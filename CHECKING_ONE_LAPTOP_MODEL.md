# iTantra v2 — Checking the Full Project on One Laptop

This guide takes you from a completely empty laptop (nothing installed) to running the full iTantra system — mic recording, speech-to-text, low-bitrate simulation, text-to-speech, and the web UI — all on a single machine.

**This is the v2 guide.** The web UI and single-laptop flow look the same as v1 on the surface, but the speech-to-text step underneath is different: English still uses OpenAI's Whisper, while Tamil, Hindi, and Telugu now use AI4Bharat's **IndicConformer** instead, because testing showed Whisper is unreliable on these languages even on clean audio (see the main `README.md`'s "What Changed in v2" section for the actual evidence). Since the web UI calls the same underlying `sender_pipeline.py` code as the command-line tools, this switch applies automatically here too — you don't need to do anything special to get it, but you do need one extra Hugging Face model approval and, optionally, one extra system install (covered below) to get the most out of it.

Follow every step in order. Don't skip the "Expected Output" checks.

**Time required:** 1.5–3 hours, mostly waiting on downloads — longer than v1 mainly because of the second STT model and the optional CUDA/cuDNN step. If you're short on time, skip Step 8C entirely; everything still works correctly, just slower.

---

## Prerequisites

- Windows laptop, 8GB+ RAM, **~15GB free disk space** (up from v1's ~10GB — IndicConformer's model is ~2.5GB on its own, and the optional CUDA Toolkit + cuDNN install adds another 5-8GB if you choose to do it)
- A working microphone (built-in or external)
- Stable internet connection (downloads total several GB, more than v1)

---

## PART A — Install Python

### Step 1 — Check if Python is already installed

Open **PowerShell** (search "PowerShell" in the Start menu) and run:

```powershell
python --version
```

**If you see a version number** (e.g. `Python 3.11.x` or `Python 3.13.x`) → skip to Step 3.
**If you get an error** → continue to Step 2.

### Step 2 — Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.11** (3.13 also confirmed working)
3. Run the installer
4. ⚠️ **Critical:** check the box **"Add Python to PATH"** before clicking Install
5. Close and reopen PowerShell, then re-run `python --version` to confirm

---

## PART B — Install Git

### Step 3 — Check if Git is installed

```powershell
git --version
```

**If you see a version number** → skip to Step 5.
**If you get an error** → continue to Step 4.

### Step 4 — Install Git

1. Go to [git-scm.com/downloads](https://git-scm.com/downloads)
2. Download and run the Windows installer
3. Click through with default settings (safe to leave everything as-is)
4. Close and reopen PowerShell, confirm with `git --version`

---

## PART C — Get the Project Code

### Step 5 — Choose a folder and clone the repository

```powershell
cd Desktop
git clone https://github.com/itz-Arun-001/iTantra-version2.git
cd iTantra-version2
```

**Expected output:** a new `iTantra-version2` folder appears containing files like `sender_pipeline.py`, `api_server.py`, `network_sender.py`, `test_indicconformer.py`, `PART1_SETUP_GUIDE.md`, etc.

---

## PART D — Python Environment Setup

### Step 6 — Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Expected output:** your prompt now starts with `(venv)`.

### ⚠️ If you get "running scripts is disabled on this system"

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then try activating again. You'll need to run this once per new PowerShell window.

**Important:** every time you close and reopen PowerShell, you must `cd` back into the `iTantra-version2` folder and re-run `venv\Scripts\Activate.ps1` before running any Python commands.

### Step 7 — Check if you have an NVIDIA GPU

```powershell
nvidia-smi
```

**If it shows GPU info** → note the CUDA version shown, go to Step 8A.
**If you get "not recognized"** → you don't have an NVIDIA GPU, go to Step 8B and skip Step 8C entirely. This is completely fine — the project runs correctly on CPU too, just slower, and this matters slightly more in v2 than v1 since IndicConformer is a larger model than Whisper-small was.

### Step 8A — Install PyTorch (GPU version)

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

This is a large download (~2.5GB+). If it times out partway, just run the exact same command again — it resumes automatically. `cu128` works with modern NVIDIA drivers even if `nvidia-smi` reports a newer supported CUDA version — drivers are backward-compatible with older CUDA builds.

Then continue to Step 8C.

### Step 8B — Install PyTorch (CPU version)

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

Smaller download (~200-300MB). Expect STT/TTS to take longer per message (15-60+ seconds, IndicConformer especially) — this is expected, not a bug. **Skip Step 8C** and go straight to Step 9.

### Step 8C — Install NVIDIA CUDA Toolkit + cuDNN (GPU path only, optional, new in v2)

This step is **new in v2** and is **optional**. Without it, IndicConformer still produces correct transcriptions — it just runs on CPU instead of GPU. Skip this if you're short on time or disk space; you can always come back to it later.

This installs actual NVIDIA system software — separate from anything `pip` manages, and a bigger, slower install than a normal Python package.

1. Download **CUDA Toolkit 13.x** from [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads) — select Windows → your version → exe (local). Run the installer, choose **Express Installation**, and **restart your computer** afterward (PATH changes often need a reboot to take effect).
2. Download **cuDNN 9.x** (matching CUDA 13.x) from [developer.nvidia.com/cudnn](https://developer.nvidia.com/cudnn) — requires a free NVIDIA Developer account. It's a zip file, not an installer: extract it, then copy its `bin`, `include`, and `lib` folders into your CUDA install location (typically `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.x\`), merging with what's already there.
3. Open a **brand new** PowerShell window (important — old windows won't see the updated PATH) and verify:
   ```powershell
   where.exe cublasLt64_13.dll
   ```
   **Expected output:** a real file path. If it says "not found," either the restart hasn't happened yet, or cuDNN's files weren't copied to the right folder.

**Installing to a different drive than C:** choose **Custom (Advanced)** instead of Express in step 1, redirect components to e.g. `F:\CUDA\v13.x`, and uncheck the driver components (safe to skip since `nvidia-smi` already works). You'll then need to manually add `F:\CUDA\v13.x\bin` to your system PATH (search Windows for "Environment Variables" → System variables → `Path` → Edit → New) and restart.

### Step 9 — Install all remaining Python packages

```powershell
pip install transformers soundfile numpy sounddevice flask flask-cors
```

**If you're on the GPU path (Step 8A):**
```powershell
pip install onnxruntime-gpu
```
**If you're on the CPU path (Step 8B):**
```powershell
pip install onnxruntime
```

⚠️ **Never install both `onnxruntime` and `onnxruntime-gpu` in the same environment.** They share the same Python import name and conflict — you'll get `AttributeError: module 'onnxruntime' has no attribute 'InferenceSession'` if both are present. Check with `pip list` if unsure; if you see both, fix it with:
```powershell
pip uninstall onnxruntime onnxruntime-gpu -y
pip install onnxruntime-gpu
```
(substitute plain `onnxruntime` if you're on the CPU path)

### Step 10 — Install the TTS library (from GitHub, not a standard package)

```powershell
pip install git+https://github.com/huggingface/parler-tts.git
```

### Step 11 — Verify the install

```powershell
python -c "import torch, transformers, flask, sounddevice, onnxruntime; print('All good! CUDA (torch):', torch.cuda.is_available()); print('onnxruntime providers:', onnxruntime.get_available_providers())"
```

**Expected output (GPU path, with Step 8C completed):**
```
All good! CUDA (torch): True
onnxruntime providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```
**Expected output (GPU path, Step 8C skipped, or CPU-only path):**
```
All good! CUDA (torch): True (or False on CPU-only)
onnxruntime providers: ['CPUExecutionProvider']
```
Either is fine — `CUDAExecutionProvider` missing just means IndicConformer will run on CPU (slower, still correct). No errors is what actually matters.

---

## PART E — Hugging Face Account & Gated Model Access (v2 needs TWO approvals, not one)

### Step 12 — Create a Hugging Face account

Go to [huggingface.co](https://huggingface.co) and sign up (free) if you don't have an account.

### Step 13 — Request access to BOTH gated models

v2 needs two separate AI4Bharat models approved, not one — STT and TTS are handled by different models:

1. **TTS (same as v1):** [huggingface.co/ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) — fill in the short form and submit
2. **STT for Tamil/Hindi/Telugu (new in v2):** [huggingface.co/ai4bharat/indic-conformer-600m-multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) — same process

Both are usually granted within minutes, but not guaranteed instant — request both now, before you need them, and don't proceed until you can view both models' files.

### Step 14 — Generate an access token

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **New token**, name it anything (e.g. "itantra"), select **Read** access, click **Create**
3. Copy the token (starts with `hf_`)

### Step 15 — Log in from your terminal

```powershell
hf auth login
```

`huggingface-cli login` is deprecated and no longer works — use `hf auth login` instead. If `hf` isn't recognized, run `pip install -U huggingface_hub` first.

When prompted, right-click to paste your token, press Enter. When asked "Add token as git credential?", typing `y` is fine.

**Expected output:** `Login successful.` Double-check anytime with `hf auth whoami`.

---

## PART F — Find Your Microphone

### Step 16 — List your audio devices

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Find your laptop's microphone — look for something with **"in"** channels greater than 0, commonly named "Microphone Array" or "Microphone (Realtek...)". **Note its index number** (the number at the start of that line).

### Step 17 — Update the mic index in the code

```powershell
notepad sender_pipeline.py
```

Find this line near the top:
```python
MIC_INDEX = 7  # your mic's index
```

Change `7` to **your** mic's index number from Step 16. Save and close.

⚠️ **If you're editing this file in Notepad, be careful with indentation.** This project's development repeatedly hit `IndentationError`/`SyntaxError` from Notepad mangling whitespace on paste. Changing just this one line is safe, but if you ever need to edit more, prefer replacing an entire function rather than patching a fragment in the middle of one.

### Step 18 — Test your microphone AND check its volume is actually loud enough

```powershell
python -c "
import sounddevice as sd
import numpy as np
MIC_INDEX = 7  # replace with your actual index from Step 16
device_info = sd.query_devices(MIC_INDEX)
native_rate = int(device_info['default_samplerate'])
print('Recording 3 seconds — speak loudly now...')
audio = sd.rec(int(3 * native_rate), samplerate=native_rate, channels=device_info['max_input_channels'], dtype='float32', device=MIC_INDEX)
sd.wait()
print(f'Max volume: {np.max(np.abs(audio)):.4f}')
"
```

**Expected output:** a volume number **above 0.15** after speaking normally. This threshold is stricter than earlier drafts of this guide — real testing during v2 development found that a peak around 0.11 was too quiet, causing the voice-activity detector to catch only fragmented, sub-second speech blips instead of full sentences, which then fed broken audio into both STT models and produced garbled transcriptions that looked like a model accuracy problem but were actually a microphone gain problem.

**If your number is below 0.15:**
- Right-click the speaker icon in the Windows taskbar → **Sound settings** → **Input** → select your mic → **Device properties** → **Levels** tab → push the microphone volume up
- Look for a **Microphone Boost** setting in the same properties and enable it (try +10dB or +20dB) if available
- If it's still near 0.0000 even after boosting, check Windows microphone privacy settings (Settings → Privacy & Security → Microphone → ensure desktop apps are allowed)
- Re-run this test until you consistently get above 0.15 before moving on — skipping this check is the single most common cause of confusing, hard-to-diagnose transcription problems later

---

## PART G — Set Up the Web Interface

### Step 19 — Check if Node.js is installed

```powershell
node --version
```

**If you see a version number** → skip to Step 21.
**If you get an error** → continue to Step 20.

### Step 20 — Install Node.js

1. Go to [nodejs.org](https://nodejs.org)
2. Download the **LTS** version, run the installer with default settings
3. On the "Tools for Native Modules" screen, leave the checkbox **unchecked**, click Next
4. Close and reopen PowerShell, confirm with `node --version`

### Step 21 — Install the frontend's dependencies

```powershell
cd itantra-ui
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
npm install
```

This downloads ~300MB of packages, takes a few minutes.

**Expected output:** ends with `added XXX packages`.

---

## PART H — Run Everything

You need **two PowerShell windows** open at the same time.

### Step 22 — Window 1: Start the Python backend

```powershell
cd Desktop\iTantra-version2
venv\Scripts\Activate.ps1
python api_server.py
```

**Expected output (after model downloads finish — first run only, several GB, several minutes):**
```
Starting iTantra API server on http://localhost:5000
Running on http://127.0.0.1:5000
```

**Leave this window open.**

### Step 23 — Window 2: Start the web interface

Open a **new** PowerShell window:

```powershell
cd Desktop\iTantra-version2\itantra-ui
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
npm run dev
```

**Expected output:**
```
Local: http://localhost:3000
```

### Step 24 — Test it

Open your browser and go to:
```
http://localhost:3000
```

You should see the iTantra interface. Select a language and bitrate mode, click the record button, and speak a short sentence **in that language**. After a short wait (model processing takes time, especially on CPU-only laptops), you should see:
- Your transcribed text
- Bandwidth reduction stats
- A playable audio clip of the synthesized speech response

**v2 note:** the web UI calls the same `sender_pipeline.py` code as the command-line tools, so selecting Hindi, Tamil, or Telugu here automatically routes through IndicConformer, not Whisper — you don't need to configure anything extra for this to happen. The **first time** you select one of these three languages, expect an extra multi-minute pause while IndicConformer's model downloads (a few GB, one-time only). What the web UI does *not* yet do is use the real two-laptop UDP network transport — it always simulates transmission and packet loss on this one machine, even though a genuine network version exists (`network_sender.py`/`network_receiver.py`, covered in `CHECKING_TWO_LAPTOP_MODEL.md`).

---

## Common Issues

### "No speech detected" every time, or transcription is garbled even on a clear sentence
- Check your mic index is correct (Step 16-17)
- Re-check your mic's peak volume against the 0.15 threshold in Step 18 — this was the single most time-consuming issue during v2 development, and was fixed by enabling Microphone Boost in Windows sound settings, not by any code or model change
- Speak clearly and start talking the instant the interface shows it's listening — a delay before speaking can push your actual speech outside the usable recording window
- Confirm the language you selected in the UI actually matches the language you spoke — neither STT model does automatic language detection, and forcing the wrong language onto real speech tends to produce fluent-sounding but entirely wrong output rather than an obvious error

### `PortAudioError` or `DirectSound error`
- Close other apps that might be using the microphone (Zoom, Teams, browser tabs with mic access)
- Restart the Windows Audio service: open PowerShell **as Administrator**, run `Restart-Service -Name AudioSrv -Force`
- As a last resort, restart your laptop

### CORS error in the browser console
- Make sure **both** Window 1 (Flask) and Window 2 (npm) are running at the same time
- Refresh the browser page after both are confirmed running

### `AttributeError: module 'onnxruntime' has no attribute 'InferenceSession'`
- You have both `onnxruntime` and `onnxruntime-gpu` installed at once — see the warning in Step 9. Uninstall both and reinstall only the one you actually need

### Wall of `[E:onnxruntime:...] Error loading "onnxruntime_providers_cuda.dll" which depends on "cublasLt64_13.dll" which is missing` repeated many times
- Means `onnxruntime-gpu` can't find the NVIDIA CUDA Toolkit/cuDNN files — either Step 8C wasn't completed, or a restart is still needed
- **Not fatal** — `onnxruntime` automatically falls back to CPU and still produces correct transcriptions, just slower. Safe to ignore if you don't need GPU speed right now

### `GatedRepoError` / `403 Client Error` / "Cannot access gated repo" when a model loads
- One or both of the two Hugging Face model access requests from Step 13 hasn't been approved yet, or you're logged into the wrong account — check with `hf auth whoami`, and check both model pages directly to confirm access status

### Everything is slow (30-60+ seconds per response)
- Expected on CPU-only laptops, or GPU laptops that skipped Step 8C — IndicConformer is a larger model than Whisper-small was in v1, so this is more noticeable in v2 than it was before. This is not a bug.

---

## Reporting Back

If you get stuck, share:
1. Which **Step number** you're on
2. The **exact command** you ran
3. The **full error message** (not a summary or screenshot description)
4. Whether you have an NVIDIA GPU or not, and if so, whether you completed Step 8C (CUDA Toolkit + cuDNN)
5. Which language you selected in the UI when the problem occurred
6. Your mic's peak volume reading from Step 18, if it's a transcription-quality question

This lets whoever's helping fix it quickly instead of guessing.
