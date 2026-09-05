# iTantra — Part 1: Environment Setup Guide

This guide sets up the Python environment needed to run any part of the iTantra project (STT, TTS, bitrate simulation, etc.) on your laptop. Follow every step in order. Don't skip the "Expected Output" checks — they confirm each step actually worked before moving to the next.

**v2 update:** this guide now also covers the **NVIDIA CUDA Toolkit 13.x + cuDNN 9.x** system install and the **second gated Hugging Face model** (IndicConformer) that v2 requires for GPU-accelerated Hindi/Tamil/Telugu STT. If you're on the CPU-only path, you can skip the CUDA/cuDNN step (Step 7A) entirely.

**Time required:** 30–60 minutes on the CPU path, up to 90 minutes on the GPU path (CUDA Toolkit + cuDNN add extra download/install time), depending on internet speed.

---

## Prerequisites

- Windows laptop (this guide is Windows-specific; ask in the group if you're on Mac/Linux)
- At least 8GB RAM
- ~5GB free disk space
- A working microphone (built-in or external)
- Stable internet connection (some downloads are 1-3GB)

---

## Step 1 — Check if Python is installed

Open **PowerShell** (search "PowerShell" in the Start menu) and run:

```powershell
python --version
```

**Expected output:**
```
Python 3.11.x
```
or
```
Python 3.13.x
```

**If you get an error like "python is not recognized"** → Python isn't installed. Go to Step 2.
**If a version number shows up** → skip to Step 3.

---

## Step 2 — Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.11** (recommended) or Python 3.13
3. Run the installer
4. ⚠️ **Critical:** On the first install screen, check the box **"Add Python to PATH"** before clicking Install. If you miss this, commands won't work later and you'll need to reinstall.
5. Once installed, close and reopen PowerShell, then re-run:
```powershell
python --version
```
Confirm it now shows a version number.

---

## Step 3 — Create the project folder

Choose a location on your laptop (Desktop, Documents, wherever), then in PowerShell:

```powershell
cd path\to\wherever\you\want\the\project
mkdir itantra
cd itantra
```

**Expected output:** your prompt now ends in `\itantra>`, e.g.:
```
PS F:\SIH project\itantra>
```

---

## Step 4 — Create a virtual environment

A virtual environment keeps this project's Python packages separate from everything else on your system.

```powershell
python -m venv venv
```

This creates a `venv` folder inside `itantra`. No visible output means it worked — just check that a `venv` folder now exists (you can confirm with `dir`).

**Now activate it:**
```powershell
venv\Scripts\Activate.ps1
```

**Expected output:** your prompt now starts with `(venv)`, e.g.:
```
(venv) PS F:\SIH project\itantra>
```

### ⚠️ Common error: "running scripts is disabled on this system"

If activation fails with a script execution error, run this **once**:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then try activating again:
```powershell
venv\Scripts\Activate.ps1
```
This only changes the policy for your current PowerShell window — it's safe and doesn't affect your system permanently. You may need to run this `Set-ExecutionPolicy` command again each time you open a **new** PowerShell window (it resets when you close the window).

**Important:** Every time you close and reopen PowerShell to work on this project, you must `cd` back into the `itantra` folder and re-run `venv\Scripts\Activate.ps1` before running any Python commands. If you forget, you'll get "module not found" errors even though everything is installed correctly.

---

## Step 5 — Check if you have an NVIDIA GPU

Run:
```powershell
nvidia-smi
```

**If it shows a table with GPU info** (name, memory, driver version) → you have an NVIDIA GPU. Note the **CUDA Version** shown in the top section — go to Step 6A.

**If you get "nvidia-smi is not recognized"** → you don't have an NVIDIA GPU (or it's AMD/Intel integrated graphics). Go to Step 6B.

This matters because AI models run much faster on NVIDIA GPUs, but the project must also work correctly on laptops without one — that's why we check this now.

---

## Step 6A — Install PyTorch (GPU / NVIDIA version)

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

This is a **large download (~2.5GB)**. It may take several minutes. If you see a `ConnectionResetError` or the download times out partway through, this is a temporary network hiccup — just **run the exact same command again**. Pip resumes partial downloads automatically. It's normal to need 2-3 attempts on unstable WiFi.

**Expected output (last lines):**
```
Successfully installed ... torch-2.6.0+cu124 ...
```

Skip Step 6B and go to Step 7.

---

## Step 6B — Install PyTorch (CPU-only version)

If you don't have an NVIDIA GPU:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

This is a smaller download (~200-300MB).

**Expected output (last lines):**
```
Successfully installed ... torch-2.x.x ...
```

---

## Step 7 — Install the remaining libraries

If you installed the **CPU-only** version of PyTorch in Step 6B:
```powershell
pip install transformers onnxruntime soundfile numpy sounddevice torchaudio
```

If you installed the **GPU** version of PyTorch in Step 6A, install `onnxruntime-gpu` instead of plain `onnxruntime` — IndicConformer's ONNX-based decoder needs the GPU build to actually use your GPU:
```powershell
pip install transformers onnxruntime-gpu soundfile numpy sounddevice
pip install torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### ⚠️ Critical: never have both `onnxruntime` and `onnxruntime-gpu` installed at once

They share the same Python import name (`import onnxruntime`), so having both installed causes import conflicts — typically showing up as:
```
AttributeError: module 'onnxruntime' has no attribute 'InferenceSession'
```
Check with:
```powershell
pip list | findstr onnxruntime
```
If you see **both** `onnxruntime` and `onnxruntime-gpu` listed, remove both and reinstall only the one you actually need:
```powershell
pip uninstall onnxruntime onnxruntime-gpu -y
pip install onnxruntime-gpu   # or plain "onnxruntime" if you're on the CPU path
```

**Expected output (Step 7):** a long list of packages downloading, ending with:
```
Successfully installed ... transformers-x.x.x onnxruntime-gpu-x.x.x soundfile-x.x.x numpy-x.x.x sounddevice-x.x.x ...
```

No red "ERROR" lines. Yellow "WARNING" lines (like about pip updates or Hugging Face authentication) are safe to ignore.

---

## Step 7A — Install NVIDIA CUDA Toolkit 13.x + cuDNN 9.x (GPU path only, new in v2)

**Skip this step entirely if you're on the CPU path (Step 6B)** — IndicConformer still works correctly on CPU, just slower. This step is what lets `onnxruntime-gpu` actually use your NVIDIA GPU for IndicConformer's STT inference. It's a **system-wide install**, separate from anything `pip` handles, and is new in v2 (v1 didn't need it).

1. **Check your driver's max supported CUDA version** (you already saw this in Step 5's `nvidia-smi` output, near the top right — e.g. "CUDA Version: 12.6"). This is the *maximum* your driver supports, not necessarily what you need to install — CUDA Toolkit 13.x needs a reasonably recent driver. If `nvidia-smi` shows a CUDA version below 12.x, update your NVIDIA driver first from [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx).

2. **Download CUDA Toolkit 13.x** from [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads). Select Windows → your architecture → your Windows version → **exe (local)**.

3. **Run the installer.** Choose **Express (Recommended)** unless you specifically need a non-default install location (see the note below). This installs to `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.x` by default.

   **If your `C:` drive is low on space:** the installer doesn't offer a GUI option to change the drive, but you can redirect it with a command-line flag. Run the installer with:
   ```powershell
   .\cuda_13.x_windows.exe -s -custominstalldir="D:\CUDA"
   ```
   (Replace the filename and path with your actual installer and target drive.) After this, add `D:\CUDA\bin` to your PATH manually (System Properties → Environment Variables → Path → New).

4. **Download cuDNN 9.x** from [developer.nvidia.com/cudnn](https://developer.nvidia.com/cudnn) — requires a free NVIDIA Developer account to download. Select the version matching CUDA 13.x.

5. **Install cuDNN** by extracting the downloaded archive and copying its `bin`, `include`, and `lib` folder contents into the matching folders inside your CUDA Toolkit install directory (e.g. `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.x\`).

6. **Restart your laptop.** This step is not optional — PATH changes from the installer often don't take effect until reboot, and this is the single most common cause of "it says installed but nothing works" on this step.

7. **Verify the install:**
   ```powershell
   nvcc --version
   ```
   **Expected output:** version info showing `release 13.x`. If you get "nvcc is not recognized" after rebooting, the Toolkit's `bin` folder isn't on your PATH — check Step 3's custom-install note above, or reinstall using Express mode to the default location.

### ⚠️ Troubleshooting: `onnxruntime-gpu` still silently uses CPU after installing CUDA/cuDNN

This fails **silently** — no error, just slower performance than expected. Check:
```powershell
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```
**Expected output:** should include `'CUDAExecutionProvider'`. If it only shows `'CPUExecutionProvider'`:
- Confirm you rebooted after the CUDA/cuDNN install (Step 6 above)
- Confirm you don't have plain `onnxruntime` shadowing `onnxruntime-gpu` (see the critical warning above)
- Confirm the cuDNN version matches your CUDA Toolkit major version (9.x for CUDA 13.x)

---

## Step 8 — Verify everything works together

Run this single command (this works whether you installed `onnxruntime` or `onnxruntime-gpu` in Step 7 — the import name is the same either way):

```powershell
python -c "import torch, transformers, onnxruntime, soundfile, numpy, sounddevice, torchaudio; print('All good!'); print('torch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

**Expected output:**
```
All good!
torch: 2.6.0+cu124
CUDA available: True
```
(If you installed the CPU version, `CUDA available` will correctly show `False` — that's expected and fine, not an error.)

**If this runs with no errors** → ✅ **Part 1 is complete.** You're ready to move to Part 2 (Speech-to-Text).

---

## Step 8A — Hugging Face account: request access to BOTH gated models (new in v2)

v2 needs access to **two** gated Hugging Face models, not just one — one for TTS, one for STT:

1. Sign up free at [huggingface.co](https://huggingface.co) if you don't already have an account.
2. Request access to the **TTS** model (used on the receiver side, same as v1):
   [huggingface.co/ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts)
3. Request access to the **STT** model (new in v2, used for Hindi/Tamil/Telugu on the sender side):
   [huggingface.co/ai4bharat/indic-conformer-600m-multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual)
   Fill in the short form on each page and submit — approval is usually within minutes, but check both show "access granted" before moving on.
4. Generate a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (New token → Read role → Create), then log in:
   ```powershell
   hf auth login
   ```
   ⚠️ **Note:** `huggingface-cli login` is deprecated as of recent `huggingface_hub` versions — use `hf auth login` instead. If `hf` isn't recognized, update the package first: `pip install -U huggingface_hub`.

**Expected output:** `Login successful.` This single login covers both gated models once both access requests are approved — you don't log in twice.

**⚠️ `GatedRepoError` later when running sender/receiver scripts** → means one of the two access requests above wasn't completed or approved yet on this specific machine/account. Each teammate needs their own account with both approved.

---

## Step 9 — Check your microphone works (do this before Part 2)

**First, list your audio devices** so you can find your mic's index number. Create `list_devices.py`:

```powershell
notepad list_devices.py
```

```python
import sounddevice as sd
print(sd.query_devices())
print(f"\nDefault input device index: {sd.default.device[0]}")
```

Run it:
```powershell
python list_devices.py
```

Look through the list for your laptop's built-in mic (usually named something like "Microphone Array (Realtek...)"). **Note its index number** (the number on the left of that line) — you'll need it below. It will very likely be a **different number on your laptop** than on someone else's — don't assume it's the same index as a teammate's.

**Now create `check_mic.py`** — this is the tested, working version (handles the sample-rate mismatch that commonly occurs with WASAPI audio devices on Windows):

```powershell
notepad check_mic.py
```

Paste this in, save, and close Notepad:

```python
import sounddevice as sd
import numpy as np
import torch
import torchaudio

MIC_INDEX = 15  # <-- REPLACE with YOUR mic's index number from list_devices.py

device_info = sd.query_devices(MIC_INDEX)
native_rate = int(device_info["default_samplerate"])
print(f"Device native sample rate: {native_rate}")

print(f"\nRecording 3 seconds — speak loudly now...")
audio = sd.rec(int(3 * native_rate), samplerate=native_rate, channels=1, dtype="float32", device=MIC_INDEX)
sd.wait()

max_vol = np.max(np.abs(audio))
print(f"\nMax volume captured (native rate): {max_vol:.4f}")
if max_vol < 0.01:
    print("⚠️  Almost silent — mic likely not capturing audio. See troubleshooting section below.")
else:
    print("✅ Mic is capturing audio correctly.")

# Resample to 16000 Hz — this is the rate our STT/TTS models expect
audio_tensor = torch.from_numpy(audio.T)
resampler = torchaudio.transforms.Resample(orig_freq=native_rate, new_freq=16000)
resampled = resampler(audio_tensor)
print(f"Resampled shape: {resampled.shape}")
```

Run it:
```powershell
python check_mic.py
```

**Expected output:** the device's native sample rate (commonly `48000`), followed by a volume number **above 0.05** (ideally 0.2–0.9 if you spoke clearly), the "✅ Mic is capturing audio correctly" message, and a resampled shape line.

⚠️ **Important:** if you get a `PortAudioError: Invalid sample rate` error, it means you skipped the native-rate handling above and tried to record directly at 16000Hz on a device that doesn't support it natively — make sure you copied the script exactly as written, including the `native_rate` detection lines.

### ⚠️ Troubleshooting: "Max volume captured: 0.0000"

Try these in order:

1. **Check Windows mic permissions:** Settings → Privacy & Security → Microphone → make sure microphone access is ON, and "Let desktop apps access your microphone" is ON.
2. **Check Windows sound settings:** Right-click the speaker icon in taskbar → Sound settings → Input → confirm the correct microphone is selected, volume isn't at 0 (aim for 60-80), and the input level bar visibly moves when you talk.
3. **Check it isn't muted** — some laptops have a physical mute key or software mute toggle.
4. **Try a different device index** — if you have multiple audio devices (e.g. a Bluetooth headset connected), the wrong one might be selected as default. Look at the full device list printed above, find your laptop's built-in mic (usually named "Microphone Array" or similar), note its index number, then edit the script to hardcode it:
   ```python
   DEVICE_INDEX = 15  # replace with your mic's actual index number
   ```

### ⚠️ Troubleshooting: `PortAudioError: Invalid sample rate`

This means the mic device doesn't support the sample rate you're requesting directly. The script above already handles this by using the device's own `default_samplerate` instead of forcing 16000Hz — if you still see this error, double check you copied the script exactly as written (specifically the `native_rate` lines).

---

## Common Warnings You Can Safely Ignore

You may see these — they are **not errors** and don't affect anything:

- `Warning: You are sending unauthenticated requests to the HF Hub...` — just means downloads might be slightly slower without a Hugging Face account login. Not required for this project.
- `UserWarning: huggingface_hub cache-system uses symlinks by default...` — a Windows-specific caching quirk, purely cosmetic.
- `[notice] A new release of pip is available...` — just a suggestion to update pip, not required.

---

## Final Checklist Before Moving to Part 2

- [ ] `python --version` shows a version number
- [ ] `(venv)` appears in your PowerShell prompt after activating
- [ ] Step 8's verification command runs with no errors
- [ ] **(GPU path only)** `nvcc --version` shows CUDA 13.x, and `onnxruntime`'s provider list includes `CUDAExecutionProvider` (Step 7A)
- [ ] **(New in v2)** Both gated Hugging Face models show "access granted," and `hf auth login` succeeded (Step 8A)
- [ ] `check_mic.py` shows a volume reading above 0.05 and "✅ Mic is capturing audio correctly"

Once all four are checked, you're fully set up and ready for **Part 2: Speech-to-Text (STT)**.

---

## Bonus: Tested Part 2 Preview (Speech-to-Text)

Once your mic check passes, here's the **tested, working STT script** (using OpenAI Whisper). This confirms your full pipeline — mic → resample → transcribe — works end to end. **Note (v2):** in the full project, Whisper is now only used for **English**; Hindi/Tamil/Telugu are routed through AI4Bharat IndicConformer instead (see `sender_pipeline.py` and the main `README.md`'s "What Changed in v2" section) — but this standalone Whisper-only script below is still a valid quick sanity check that your mic → STT loop works at all, in any language.

Create `test_stt.py`:

```powershell
notepad test_stt.py
```

```python
import sounddevice as sd
import numpy as np
import torch
import torchaudio
import time
from transformers import pipeline

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

MIC_INDEX = 15  # <-- REPLACE with YOUR mic's index number from list_devices.py
DURATION = 10  # seconds

print("Loading Whisper model...")
asr = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-small",
    device=0 if DEVICE == "cuda" else -1,
)
asr.model.generation_config.suppress_tokens = None
asr.model.generation_config.begin_suppress_tokens = None

device_info = sd.query_devices(MIC_INDEX)
native_rate = int(device_info["default_samplerate"])

print("\nGet ready...")
time.sleep(1.5)  # buffer so your first word isn't cut off
print(f"Recording for {DURATION} seconds... SPEAK NOW!")

audio = sd.rec(int(DURATION * native_rate), samplerate=native_rate, channels=1, dtype="float32", device=MIC_INDEX)
sd.wait()
print("Recording done. Resampling and transcribing...")

audio_tensor = torch.from_numpy(audio.T)
resampler = torchaudio.transforms.Resample(orig_freq=native_rate, new_freq=16000)
resampled = resampler(audio_tensor).numpy().flatten()

result = asr(
    {"array": resampled, "sampling_rate": 16000},
    generate_kwargs={"language": "en", "task": "transcribe"},
)

print("\n--- TRANSCRIPTION ---")
print(result["text"])
```

Run it:
```powershell
python test_stt.py
```

**Expected output:** after "SPEAK NOW!", speak a clear sentence at a normal pace (not rushed). It should print a reasonably accurate transcription of what you said.

**Known limitation:** Whisper occasionally drops small connector words (like "all of", "a", "the") in fast or quiet speech — this is normal, minor, and not worth over-optimizing for a hackathon demo. Don't burn time chasing perfect accuracy here.

**Harmless warnings you'll likely still see** (safe to ignore, don't affect the output):
```
[transformers] Passing `generation_config` together with generation-related arguments...
[transformers] Ignoring clean_up_tokenization_spaces=True...
```

---

## If You Get Stuck

Post the **full error message** (not just a screenshot description) in the team chat, including:
1. The exact command you ran
2. The complete output/error text
3. Whether you have an NVIDIA GPU or not (from Step 5)

This lets whoever's helping diagnose the issue quickly instead of guessing.
