from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from sender_pipeline import run_sender
from receiver_pipeline import speak_text
from packet_reliability import transmit_with_retry
from bitrate_sim import decompress_text, BITRATE_MODES, RAW_AUDIO_BITRATE

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000")

MESSAGE_HISTORY = []
PIPELINE_STATE = {}


@app.route("/api/step/record", methods=["POST"])
def step_record():
    data = request.get_json() or {}
    bitrate_mode = data.get("bitrateMode", "LOW")
    language = data.get("language", "en")
    PIPELINE_STATE["language"] = language
    result = run_sender(bitrate_mode=bitrate_mode, language=language)
    if result is None:
        return jsonify({"success": False, "error": "No speech detected"}), 400
    text, data_bytes, was_compressed = result
    PIPELINE_STATE["text"] = text
    PIPELINE_STATE["data_bytes"] = data_bytes
    PIPELINE_STATE["was_compressed"] = was_compressed
    PIPELINE_STATE["bitrate_mode"] = bitrate_mode
    return jsonify({
        "success": True,
        "transcription": text,
        "originalSize": len(text.encode("utf-8")),
        "transmittedSize": len(data_bytes),
    })


@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(MESSAGE_HISTORY)


@app.route("/api/role", methods=["POST"])
def set_role():
    data = request.get_json() or {}
    role = data.get("role")
    if role not in ("sender", "receiver"):
        return jsonify({"error": "Invalid role"}), 400
    PIPELINE_STATE["role"] = role
    return jsonify({"success": True, "role": role})


@app.route("/api/step/transmit", methods=["POST"])
def step_transmit():
    data = request.get_json() or {}
    priority = data.get("priority", "normal")
    data_bytes = PIPELINE_STATE.get("data_bytes")
    if data_bytes is None:
        return jsonify({"success": False, "error": "No pending message. Record first."}), 400
    reconstructed_bytes, missing = transmit_with_retry(
        data_bytes, packet_size=16, loss_probability=0.3, priority=priority
    )
    bitrate_mode = PIPELINE_STATE.get("bitrate_mode", "LOW")
    bitrate = BITRATE_MODES[bitrate_mode]
    reduction = (1 - (bitrate / RAW_AUDIO_BITRATE)) * 100
    if reconstructed_bytes is None:
        return jsonify({
            "success": False,
            "error": "Transmission failed",
            "bandwidthReduction": round(reduction, 2),
            "missingPackets": missing,
        }), 200
    PIPELINE_STATE["reconstructed_bytes"] = reconstructed_bytes
    return jsonify({
        "success": True,
        "bandwidthReduction": round(reduction, 2),
    })


@app.route("/api/step/synthesize", methods=["POST"])
def step_synthesize():
    reconstructed_bytes = PIPELINE_STATE.get("reconstructed_bytes")
    was_compressed = PIPELINE_STATE.get("was_compressed")
    language = PIPELINE_STATE.get("language", "en")
    if reconstructed_bytes is None:
        return jsonify({"success": False, "error": "Nothing to synthesize"}), 400
    decoded_text = decompress_text(reconstructed_bytes, was_compressed)
    speak_text(decoded_text, output_file="received_speech.wav", language=language)
    MESSAGE_HISTORY.append({"text": decoded_text, "language": language})
    return jsonify({"success": True, "decodedText": decoded_text})


@app.route("/api/received-audio", methods=["GET"])
def get_received_audio():
    return send_file("received_speech.wav", mimetype="audio/wav")


if __name__ == "__main__":
    print("Starting iTantra API server on http://localhost:5000")
    socketio.run(app, host="127.0.0.1", port=5000, debug=False)