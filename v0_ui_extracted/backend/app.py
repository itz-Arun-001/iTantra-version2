from __future__ import annotations

import gzip
import importlib
import os
import secrets
import socket
import struct
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

PORT = int(os.getenv("ITANTRA_UDP_PORT", "5005"))
BIND = os.getenv("ITANTRA_BIND", "0.0.0.0")
BASE = Path(__file__).resolve().parent
AUDIO_DIR = BASE / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("ITANTRA_SECRET", secrets.token_hex(16))
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
state = {"role": "sender", "receiver_running": False}
history: deque[dict[str, Any]] = deque(maxlen=20)
audio_files: dict[str, Path] = {}
listener_stop = threading.Event()
listener_thread: threading.Thread | None = None


def supplied(name: str):
    module_path = os.getenv("ITANTRA_MODULE_PATH", "")
    if module_path and module_path not in os.sys.path:
        os.sys.path.insert(0, module_path)
    return importlib.import_module(name)


def emit_progress(stage: str, detail: str):
    socketio.emit("sender_progress", {"stage": stage, "detail": detail})


def load(name: str, fallback: Any = None):
    try:
        return supplied(name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"Missing supplied module '{name}'. Set ITANTRA_MODULE_PATH to its folder.") from exc


def send_udp(payload: bytes, was_compressed: bool, receiver_ip: str, language: str, priority: str, mode: str):
    common = load("network_common")
    sender = load("network_sender")
    bitrate = load("bitrate_sim")
    chunks = common.split_into_chunks(payload)
    seq = secrets.randbelow(2**31)
    meta = f"META|{len(chunks)}|{int(was_compressed)}|{language}|{priority}".encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.7)
    sent = retried = 0
    try:
        sock.sendto(meta, (receiver_ip, PORT))
        rate = bitrate.BITRATE_MODES[mode]
        delay = max(0.001, len(payload) * 8 / rate / max(1, len(chunks)))
        for index, chunk in enumerate(chunks):
            packet = common.make_packet(seq + index, len(chunks), chunk)
            sock.sendto(packet, (receiver_ip, PORT)); sent += 1
            time.sleep(delay)
        attempts = 5 if priority == "emergency" else 3
        delivered = False
        for attempt in range(attempts):
            sock.sendto(f"CHECK|{seq}|{len(chunks)}".encode(), (receiver_ip, PORT))
            try:
                response, _ = sock.recvfrom(4096)
                if b"ALL_RECEIVED" in response:
                    delivered = True; break
                missing = [int(x) for x in response.decode().split("|")[-1].split(",") if x]
                for missing_seq in missing:
                    idx = missing_seq - seq
                    if 0 <= idx < len(chunks):
                        sock.sendto(common.make_packet(missing_seq, len(chunks), chunks[idx]), (receiver_ip, PORT)); sent += 1; retried += 1
            except socket.timeout:
                retried += 1
        return sent, retried, delivered
    finally:
        sock.close()


def run_send(data: dict[str, Any]):
    started = time.perf_counter()
    try:
        emit_progress("recording", "Listening for speech through the supplied microphone pipeline")
        sender_pipeline = load("sender_pipeline")
        text = sender_pipeline.record_and_transcribe(data["language"])
        if not text or not str(text).strip():
            raise RuntimeError("No speech detected. Speak clearly and try again.")
        emit_progress("transcribing", f"Captured {len(text)} characters")
        bitrate = load("bitrate_sim")
        payload, was_compressed = bitrate.compress_text(text)
        emit_progress("sending", f"Transmitting over UDP to {data['receiverIp']}:{PORT}")
        sent, retried, delivered = send_udp(payload, was_compressed, data["receiverIp"], data["language"], data["priority"], data["bitrateMode"])
        emit_progress("awaiting_ack", "Receiver acknowledgement received" if delivered else "No acknowledgement after retry budget")
        result = {"text": text, "originalBytes": len(text.encode()), "transmittedBytes": len(payload), "reductionPct": round((1 - len(payload) / max(1, 64000)) * 100, 1), "packetsTotal": sent, "packetsRetried": retried, "elapsedSeconds": round(time.perf_counter() - started, 2), "delivered": delivered}
        if not delivered: raise RuntimeError("UDP payload was not acknowledged after the configured retry attempts.")
        socketio.emit("sender_done", result); emit_progress("done", "Message delivered")
    except Exception as exc:
        socketio.emit("sender_error", {"message": str(exc)}); emit_progress("failed", str(exc))


def receiver_loop():
    common = None
    try: common = load("network_common")
    except Exception as exc:
        socketio.emit("receiver_error", {"message": str(exc)}); return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); sock.bind((BIND, PORT)); sock.settimeout(0.5)
    packets: dict[int, bytes] = {}; expected = 0; meta: dict[str, Any] = {}; start = time.time()
    while not listener_stop.is_set():
        try: raw, address = sock.recvfrom(65535)
        except socket.timeout: continue
        if raw.startswith(b"META|"):
            _, total, compressed, language, priority = raw.decode().split("|", 4); packets = {}; expected = int(total); meta = {"compressed": compressed == "1", "language": language, "priority": priority, "address": address[0]}; start = time.time(); continue
        if raw.startswith(b"CHECK|"):
            missing = [str(i) for i in range(min(packets.keys(), default=0), min(packets.keys(), default=0) + expected) if i not in packets]
            sock.sendto(b"ALL_RECEIVED" if not missing and len(packets) == expected else (b"MISSING|" + ",".join(missing).encode()), address); continue
        try: seq, total, chunk = common.parse_packet(raw)
        except Exception: continue
        packets[seq] = chunk
        if expected and len(packets) >= expected:
            try:
                payload = b"".join(packets[k] for k in sorted(packets))
                text = gzip.decompress(payload).decode() if meta.get("compressed") else payload.decode()
                item = {"id": uuid.uuid4().hex, "text": text, "language": meta.get("language", "en"), "priority": meta.get("priority", "normal"), "packetsTotal": expected, "packetsLost": 0, "packetsRetried": 0, "bytesReceived": len(payload), "timestamp": time.strftime("%H:%M:%S")}
                history.appendleft(item); socketio.emit("message_received", item)

                def synthesize(text=text, item_id=item["id"], language=item["language"]):
                    try:
                        receiver_pipeline = load("receiver_pipeline")
                        output = AUDIO_DIR / f"{item_id}.wav"
                        receiver_pipeline.speak_text(text, str(output), language)
                        audio_files[item_id] = output
                        socketio.emit("audio_ready", {"id": item_id})
                    except Exception as exc:
                        socketio.emit("receiver_error", {"message": f"Message decoded, but TTS failed: {exc}"})

                threading.Thread(target=synthesize, daemon=True).start()
                packets = {}; expected = 0
            except Exception as exc: socketio.emit("receiver_error", {"message": f"Packet reassembly failed: {exc}"})
    sock.close()


def set_role(role: str):
    global listener_thread
    if role == "receiver" and not state["receiver_running"]:
        listener_stop.clear(); listener_thread = threading.Thread(target=receiver_loop, daemon=True); listener_thread.start(); state["receiver_running"] = True
    elif role != "receiver" and state["receiver_running"]:
        listener_stop.set(); state["receiver_running"] = False
    state["role"] = role

@app.get("/api/health")
def health(): return jsonify({"ok": True, "role": state["role"], "receiverRunning": state["receiver_running"], "udpPort": PORT})
@app.get("/api/history")
def get_history(): return jsonify(list(history))
@app.post("/api/role")
def role():
    value = request.json.get("role") if request.is_json else None
    if value not in ("sender", "receiver"): return jsonify({"error": "Role must be sender or receiver."}), 400
    set_role(value); return jsonify({"role": value, "receiverRunning": state["receiver_running"]})
@app.post("/api/send")
def send():
    data = request.get_json(silent=True) or {}; required = {"language": ("en", "hi", "ta", "te"), "bitrateMode": ("LOW", "MEDIUM", "HIGH", "EXTREME"), "priority": ("normal", "emergency")}
    for key, allowed in required.items():
        if data.get(key) not in allowed: return jsonify({"error": f"Invalid {key}."}), 400
    try: socket.inet_aton(data.get("receiverIp", ""))
    except OSError: return jsonify({"error": "Enter a valid IPv4 receiver address."}), 400
    socketio.start_background_task(run_send, data); return jsonify({"started": True})
@app.get("/api/received-audio/<message_id>")
def audio(message_id: str):
    path = audio_files.get(message_id)
    if not path or not path.is_file(): return jsonify({"error": "Audio is not ready."}), 404
    return send_file(path, mimetype="audio/wav", conditional=True)

if __name__ == "__main__":
    socketio.run(app, host=BIND, port=int(os.getenv("ITANTRA_HTTP_PORT", "5000")), allow_unsafe_werkzeug=True)