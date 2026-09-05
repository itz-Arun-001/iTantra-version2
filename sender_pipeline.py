from transformers import AutoModel
import sounddevice as sd
import numpy as np
import torch
import torchaudio
import time
import os
import soundfile as sf
from transformers import pipeline

from bitrate_sim import compress_text, simulate_transmission, BITRATE_MODES, RAW_AUDIO_BITRATE

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

MIC_INDEX = None  # your mic's index
MAX_DURATION = 20  # absolute safety cap in seconds

if MIC_INDEX is None:
    device_info = sd.query_devices(kind='input')
else:
    device_info = sd.query_devices(MIC_INDEX)
native_rate = int(device_info["default_samplerate"])
channels = device_info["max_input_channels"]

print("Loading Silero VAD...")
vad_model, utils = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad")
(get_speech_timestamps, _, _, _, _) = utils

print("Loading Whisper model...")
asr = pipeline(
    "automatic-speech-recognition",
   model="openai/whisper-large-v3-turbo",
    device=0 if DEVICE == "cuda" else -1,
)
asr.model.generation_config.suppress_tokens = None
asr.model.generation_config.begin_suppress_tokens = None
print("Loading IndicConformer (Tamil/Hindi/Telugu)...")
indic_model = AutoModel.from_pretrained(
    "ai4bharat/indic-conformer-600m-multilingual", trust_remote_code=True
)

INDIC_LANGUAGES = {"ta", "hi", "te"}

resampler = torchaudio.transforms.Resample(orig_freq=native_rate, new_freq=16000)

def record_and_transcribe(language="en"):
    """Record from mic (fixed duration), trim silence with VAD, transcribe with Whisper or IndicConformer."""
    RECORD_DURATION = 20  # seconds

    print("\nGet ready...")
    time.sleep(1.5)
    print(f"Listening... speak, then just stop (max {RECORD_DURATION} sec).")

    audio = sd.rec(int(RECORD_DURATION * native_rate), samplerate=native_rate, channels=channels, dtype="float32", device=MIC_INDEX)
    sd.wait()
    print("Recording done. Detecting speech segments...")

    sf.write("actual_raw_recording.wav", audio, native_rate)
    raw_file_size = os.path.getsize("actual_raw_recording.wav")
    print(f"Actual raw audio file size: {raw_file_size} bytes")

    audio_tensor = torch.from_numpy(audio.T)
    if audio_tensor.shape[0] > 1:
        audio_tensor = audio_tensor.mean(dim=0, keepdim=True)
    resampled = resampler(audio_tensor).squeeze(0)

    speech_timestamps = get_speech_timestamps(
        resampled, vad_model, sampling_rate=16000,
        threshold=0.35,
        min_speech_duration_ms=100,
    )

    print(f"VAD detected {len(speech_timestamps)} speech segment(s):")
    for i, seg in enumerate(speech_timestamps):
        print(f"  Segment {i+1}: {seg['start']/16000:.2f}s to {seg['end']/16000:.2f}s")

    if not speech_timestamps:
        print("No speech detected.")
        return None

    PAD_SAMPLES = 4000

    start = max(0, speech_timestamps[0]["start"] - PAD_SAMPLES)
    end = min(len(resampled), speech_timestamps[-1]["end"] + PAD_SAMPLES)
    trimmed = resampled[start:end].numpy()
    sf.write("actual_trimmed_audio.wav", trimmed, 16000)

    if language in INDIC_LANGUAGES:
        wav_tensor = torch.from_numpy(trimmed).float().unsqueeze(0)
        text = indic_model(wav_tensor, language, "rnnt")
        return text.strip()
    else:
        result = asr(
            {"array": trimmed, "sampling_rate": 16000},
            generate_kwargs={
                "language": language,
                "task": "transcribe",
                "no_repeat_ngram_size": 3,
                "repetition_penalty": 1.3,
                "condition_on_prev_tokens": False,
            },
        )
        return result["text"].strip()

def run_sender(bitrate_mode="LOW", language="en"):
    text = record_and_transcribe(language=language)

    if text is None:
        print("Nothing to send.")
        return

    print(f"\n{'='*60}")
    print(f"TRANSCRIBED TEXT (this is what gets sent, not audio): \"{text}\"")

    data_bytes, was_compressed = compress_text(text)
    method = "gzip" if was_compressed else "raw"
    print(f"Transmitted size: {len(data_bytes)} bytes ({method})")

    # REAL, measured comparison — not theoretical
    if os.path.exists("actual_raw_recording.wav"):
        raw_size = os.path.getsize("actual_raw_recording.wav")
        real_reduction = (1 - (len(data_bytes) / raw_size)) * 100
        print(f"\n📊 REAL MEASURED COMPARISON:")
        print(f"   Actual raw audio file: {raw_size:,} bytes")
        print(f"   Actual transmitted text: {len(data_bytes):,} bytes")
        print(f"   REAL reduction: {real_reduction:.2f}% smaller (measured, not estimated)")

    bitrate = BITRATE_MODES[bitrate_mode]
    transmit_time = simulate_transmission(data_bytes, bitrate)
    print(f"\nBitrate mode: {bitrate_mode} ({bitrate} bps) → simulated transmission time: {transmit_time:.3f}s")

    estimated_audio_seconds = max(1, len(text.split()) / 2.5)
    reduction = (1 - (bitrate / RAW_AUDIO_BITRATE)) * 100
    print(f"Theoretical bandwidth reduction vs standard 64kbps voice: {reduction:.2f}%")

    print(f"\n✅ Ready to transmit. In the next step, this data would be sent to the receiver laptop, which converts it back to speech via TTS.")

    return text, data_bytes, was_compressed


if __name__ == "__main__":
    run_sender(bitrate_mode="LOW", language="en")
