import torch
import soundfile as sf
import numpy as np
from transformers import AutoModel
import torchaudio

print("Loading IndicConformer multilingual model...")
model = AutoModel.from_pretrained(
    "ai4bharat/indic-conformer-600m-multilingual", trust_remote_code=True
)

print("Loading audio...")
data, sr = sf.read("actual_trimmed_audio.wav")
wav = torch.from_numpy(data).float()
if wav.ndim == 1:
    wav = wav.unsqueeze(0)
else:
    wav = wav.T
wav = torch.mean(wav, dim=0, keepdim=True)

target_sample_rate = 16000
if sr != target_sample_rate:
    resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sample_rate)
    wav = resampler(wav)

print("Transcribing (CTC)...")
transcription_ctc = model(wav, "ta", "ctc")
print("CTC Transcription:", transcription_ctc)

print("Transcribing (RNNT)...")
transcription_rnnt = model(wav, "ta", "rnnt")
print("RNNT Transcription:", transcription_rnnt)