import socket
import time
import json

from sender_pipeline import record_and_transcribe
from bitrate_sim import compress_text, BITRATE_MODES, RAW_AUDIO_BITRATE
from network_common import PORT, make_packet, split_into_chunks

RECEIVER_IP = "10.11.141.198"  # <-- REPLACE with the receiver laptop's actual IP from Step 1

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5.0)


def send_message(bitrate_mode="LOW", priority="normal", language="ta"):
    text = record_and_transcribe(language=language)

    if text is None:
        print("Nothing to send.")
        return

    print(f"\nTRANSCRIBED: \"{text}\"")

    data_bytes, was_compressed = compress_text(text)
    chunks = split_into_chunks(data_bytes)
    total = len(chunks)

    bitrate = BITRATE_MODES[bitrate_mode]
    delay_per_packet = (len(data_bytes[:1]) if False else 0)  # placeholder, real calc below
    bytes_per_packet_bits = 200 * 8
    delay_per_packet = bytes_per_packet_bits / bitrate  # seconds, simulates the target bitrate

    reduction = (1 - (bitrate / RAW_AUDIO_BITRATE)) * 100
    print(f"Sending {total} packet(s) over real network to {RECEIVER_IP}, throttled to simulate {bitrate} bps ({reduction:.2f}% reduction vs raw audio)...")

    # Send metadata first (so receiver knows what's coming, including language + compression flag)
    meta = json.dumps({"total": total, "was_compressed": was_compressed, "language": language, "priority": priority}).encode("utf-8")
    sock.sendto(b"META" + meta, (RECEIVER_IP, PORT))
    time.sleep(0.1)

    retries_allowed = 5 if priority == "emergency" else 3
    remaining_seqs = list(range(total))

    for attempt in range(1, retries_allowed + 1):
        for seq in remaining_seqs:
            packet = make_packet(seq, total, chunks[seq])
            sock.sendto(packet, (RECEIVER_IP, PORT))
            time.sleep(delay_per_packet)

        # Ask receiver what's missing
        sock.sendto(b"CHECK", (RECEIVER_IP, PORT))
        try:
            response, _ = sock.recvfrom(4096)
            if response == b"ALL_RECEIVED":
                print(f"✅ All {total} packets delivered (attempt {attempt}).")
                remaining_seqs = []
                break
            else:
                missing = json.loads(response.decode("utf-8"))
                print(f"  Attempt {attempt}: missing packets {missing}")
                remaining_seqs = missing
        except socket.timeout:
            print("  No response from receiver — check it's running and reachable.")
            break

    if remaining_seqs:
        print(f"⚠️ Could not deliver all packets after {retries_allowed} attempts. Missing: {remaining_seqs}")
    else:
        print("Message fully delivered. Receiver should now be synthesizing speech.")


if __name__ == "__main__":
    print("Choose language: en / hi / ta / te")
    lang_choice = input("Language code: ").strip().lower()
    if lang_choice not in ("en", "hi", "ta", "te"):
        print("Invalid choice, defaulting to English.")
        lang_choice = "en"
    send_message(bitrate_mode="LOW", priority="normal", language=lang_choice)