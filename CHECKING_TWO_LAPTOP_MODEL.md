# iTantra v2 — Checking the Two-Laptop Network Model

This guide takes you from a completely empty laptop (nothing installed) to running iTantra's **real network transmission** — one laptop as sender (records your voice), another laptop as receiver (speaks it back) — communicating over actual WiFi, not simulated on one machine.

**This is the v2 guide.** The biggest difference from v1: speech-to-text is now split across two models instead of one. English still goes through OpenAI's Whisper. **Tamil, Hindi, and Telugu now go through AI4Bharat's IndicConformer instead of Whisper**, because testing showed Whisper reliably produces non-words or repetition loops on these languages even on clean audio, while IndicConformer produces accurate, coherent transcriptions on the same audio. This means there's an extra model to download, an extra Hugging Face gated-access approval to get, and — if you want GPU speed — an extra system-level install (NVIDIA CUDA Toolkit + cuDNN) that wasn't needed in v1. All of that is covered below, in order.

You'll do this in two stages:
1. **Single-laptop test** — sender and receiver both running on your own laptop, talking to each other over "localhost." This proves the code works before adding network complexity.
2. **Two-laptop test** — sender on one physical laptop, receiver on another, both on the same WiFi.

Follow every step in order. Don't skip the "Expected Output" checks.

**Time required:** 2–3.5 hours total (mostly downloads and the CUDA install, if you do it), split across two people if doing the two-laptop stage. This is longer than v1 mainly because of the CUDA Toolkit/cuDNN step in Part A — you can skip that step entirely and still get correct results, just slower, if you're short on time (see A6C).

---

## Prerequisites

- Two Windows laptops (for Stage 2), OR one laptop is enough to complete Stage 1
- 8GB+ RAM each, **~15GB free disk space each** (up from v1's ~10GB — IndicConformer's model is ~2.5GB, and the optional CUDA Toolkit + cuDNN install is another 5-8GB)
- A working microphone on the sender laptop, working speakers on the receiver laptop
- Both laptops on the **same WiFi network** for Stage 2
- Stable internet connection for the initial setup (downloads total several GB, more than v1 due to the second model)

---

# PART A — Base Setup (do this on every laptop involved)

## A1 — Install Python

Open **PowerShell** and run:
```powershell
python --version
```
**If you see a version number** → skip to A2.
**If you get an error** → go to [python.org/downloads](https://www.python.org/downloads/), download **Python 3.11** (3.13 also confirmed working), run the installer, and ⚠️ **check "Add Python to PATH"** before installing. Reopen PowerShell and confirm with `python --version`.

## A2 — Install Git

```powershell
git --version
```
**If you see a version number** → skip to A3.
**If you get an error** → download from [git-scm.com/downloads](https://git-scm.com/downloads), install with default settings, reopen PowerShell, confirm with `git --version`.

## A3 — Clone the repository

```powershell
cd Desktop
git clone https://github.com/itz-Arun-001/iTantra-version2.git
cd iTantra-version2
```

**Expected output:** a new `iTantra-version2` folder with files like `sender_pipeline.py`, `network_sender.py`, `network_receiver.py`, `test_indicconformer.py`, etc.

## A4 — Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**If you get "running scripts is disabled":**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then activate again. You'll need to repeat this `Set-ExecutionPolicy` command once per new PowerShell window.

**Expected output:** your prompt starts with `(venv)`.

## A5 — Check for an NVIDIA GPU

```powershell
nvidia-smi
```
**Shows GPU info** → go to A6A. **Shows "not recognized"** → go to A6B, then skip A6C entirely (it's GPU-only). Both paths are fully supported; a GPU just makes processing faster, and matters more in v2 than v1 since IndicConformer is a larger model than Whisper-small was.

## A6A — Install PyTorch (GPU path)

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```
Large download (~2.5GB+) — if it times out, re-run the same command, it resumes. `cu128` works with modern NVIDIA drivers even if your driver reports a newer supported CUDA version (drivers are backward-compatible). Then continue to A6C.

## A6B — Install PyTorch (CPU-only path)

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```
Smaller download (~200-300MB). Expect STT/TTS to take longer per message (15-60+ seconds, IndicConformer especially) — this is normal, not a bug. **Skip A6C** and go straight to A7.

## A6C — Install NVIDIA CUDA Toolkit + cuDNN (GPU path only — makes IndicConformer fast)

This step is **new in v2** and is **optional**. Without it, IndicConformer still produces correct transcriptions — it just runs on CPU instead of GPU, which is slower but not wrong. Skip this if you're short on time or disk space; come back to it later if speed becomes a problem.

This installs actual NVIDIA system software, separate from anything `pip` manages — it's a bigger, slower install than a normal Python package.

1. Download **CUDA Toolkit 13.x** from [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads) — select Windows → your version → exe (local). Run the installer, choose **Express Installation**, and **restart your computer** afterward (this matters — PATH changes often need a reboot to take effect).
2. Download **cuDNN 9.x** (matching CUDA 13.x) from [developer.nvidia.com/cudnn](https://developer.nvidia.com/cudnn) — requires a free NVIDIA Developer account. It comes as a zip file, not an installer: extract it, then copy its `bin`, `include`, and `lib` folders into your CUDA install location (typically `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.x\`), merging with what's already there.
3. Open a **brand new** PowerShell window (important — old windows won't see the updated PATH) and verify:
   ```powershell
   where.exe cublasLt64_13.dll
   ```
   **Expected output:** a real file path. If it says "not found," either the restart didn't happen yet, or cuDNN's files weren't copied to the right folder.

**If you'd rather install to a different drive than C:** choose **Custom (Advanced)** instead of Express in step 1, redirect the components to e.g. `F:\CUDA\v13.x`, and uncheck the driver components (safe to skip if `nvidia-smi` already works, which it does if you got this far). You'll then need to manually add `F:\CUDA\v13.x\bin` to your system PATH environment variable (search Windows for "Environment Variables" → System variables → `Path` → Edit → New) and restart.

## A7 — Install remaining Python packages

```powershell
pip install transformers onnxruntime-gpu soundfile numpy sounddevice flask flask-cors
pip install git+https://github.com/huggingface/parler-tts.git
```

**On the CPU-only path (A6B),** use `onnxruntime` instead of `onnxruntime-gpu` — there's no benefit to the GPU package without a GPU, and it avoids an unnecessary download.

⚠️ **Never install both `onnxruntime` and `onnxruntime-gpu` in the same environment.** They share the same Python import name and conflict — you'll get `AttributeError: module 'onnxruntime' has no attribute 'InferenceSession'` if both are present. If you accidentally end up with both (`pip list` will show both), fix it with:
```powershell
pip uninstall onnxruntime onnxruntime-gpu -y
pip install onnxruntime-gpu
```
(substitute plain `onnxruntime` if you're on the CPU path)

## A8 — Verify the install

```powershell
python -c "import torch, transformers, sounddevice, onnxruntime; print('All good! CUDA (torch):', torch.cuda.is_available()); print('onnxruntime providers:', onnxruntime.get_available_providers())"
```
**Expected output (GPU path, with A6C completed):**
```
All good! CUDA (torch): True
onnxruntime providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```
**Expected output (GPU path, A6C skipped, or CPU-only path):**
```
All good! CUDA (torch): True (or False on CPU-only)
onnxruntime providers: ['CPUExecutionProvider']
```
Either is fine — `CUDAExecutionProvider` missing just means IndicConformer will run on CPU (slower, still correct). No errors is what actually matters here.

## A9 — Hugging Face account and gated model access (v2 needs TWO approvals, not one)

1. Sign up free at [huggingface.co](https://huggingface.co) if you don't have an account.
2. Request access to **both** of these gated models — v2 needs both, since STT and TTS use separate AI4Bharat models:
   - [huggingface.co/ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) — text-to-speech (same as v1)
   - [huggingface.co/ai4bharat/indic-conformer-600m-multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) — speech-to-text for Tamil/Hindi/Telugu (**new in v2**)

   Both are usually approved within minutes of requesting, but this isn't guaranteed instant — request both now, before you need them.
3. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), click **New token**, name it anything, select **Read**, click **Create**, copy the token.
4. Log in from your terminal:
```powershell
hf auth login
```
(`huggingface-cli login` is deprecated and no longer works — use `hf auth login`.) Right-click to paste your token when prompted, press Enter. Type `y` if asked about git credentials.

**Expected output:** `Login successful.` You can double check with `hf auth whoami`.

## A10 — Find your microphone (needed on the SENDER laptop)

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```
Find your built-in mic in the list (look for "Microphone Array" or similar, with input channels > 0). **Note its index number.**

Then:
```powershell
notepad sender_pipeline.py
```
Find:
```python
MIC_INDEX = 7  # your mic's index
```
Change `7` to your actual mic's index number. Save and close. `network_sender.py` imports `record_and_transcribe` from `sender_pipeline.py`, so this one change is enough — you don't need to set it separately in `network_sender.py`.

⚠️ **If you're editing this file in Notepad, be careful with indentation.** This project's development hit repeated `IndentationError`/`SyntaxError` issues from Notepad mangling whitespace on paste. If you need to change more than the `MIC_INDEX` line, prefer replacing an entire function rather than editing a few lines in the middle of one — it's more reliable than trying to patch a fragment.

## A11 — Test your microphone AND check its volume is actually loud enough

```powershell
python -c "
import sounddevice as sd
import numpy as np
MIC_INDEX = 7  # replace with your actual index from A10
device_info = sd.query_devices(MIC_INDEX)
native_rate = int(device_info['default_samplerate'])
print('Recording 3 seconds — speak loudly now...')
audio = sd.rec(int(3 * native_rate), samplerate=native_rate, channels=device_info['max_input_channels'], dtype='float32', device=MIC_INDEX)
sd.wait()
print(f'Max volume: {np.max(np.abs(audio)):.4f}')
"
```

**Expected output:** a volume number **above 0.15** after speaking normally. This threshold is stricter than v1's guide — real testing during v2 development found that a peak around 0.11 was too quiet, causing Silero VAD to detect only fragmented, sub-second speech blips instead of full sentences, which in turn fed broken audio into both STT models and produced garbled transcriptions that looked like a model accuracy problem but were actually a microphone gain problem.

**If your number is below 0.15:**
- Right-click the speaker icon in the Windows taskbar → **Sound settings** → **Input** → select your mic → **Device properties** → check the **Levels** tab and push the microphone volume up
- Look for a **Microphone Boost** setting in the same properties and enable it (try +10dB or +20dB) if available
- Re-run this test until you consistently get above 0.15 before moving on — this one check will save you significant debugging time later if skipped

---

**Part A complete on this laptop.** If setting up two laptops, repeat all of Part A on the second laptop before continuing — each laptop needs its own full environment, including both Hugging Face model approvals (the receiver laptop needs the TTS model; if it will ever act as sender too, it needs IndicConformer as well).

---

# PART B — Stage 1: Single-Laptop Loopback Test

Do this on **one laptop only** first, before involving a second machine. This proves the networking code itself works, isolating bugs in your code from bugs in actual network/firewall setup.

## B1 — Set the receiver address to localhost

```powershell
notepad network_sender.py
```
Find:
```python
RECEIVER_IP = "192.168.1.42"
```
Change to:
```python
RECEIVER_IP = "127.0.0.1"
```
Save and close.

## B2 — Open two PowerShell windows

Both need to be in the project folder with venv active:
```powershell
cd Desktop\iTantra-version2
venv\Scripts\Activate.ps1
```
(Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first if needed, in each window.)

## B3 — Window 1: start the receiver

```powershell
python network_receiver.py
```

**Expected output** (after model downloads finish — several GB, first run only):
```
Listening for messages on port 5005...
```
**Leave this running.**

## B4 — Window 2: start the sender

```powershell
python network_sender.py
```

**v2 change:** you'll now be prompted for a language before recording starts:
```
Choose language: en / hi / ta / te
Language code:
```
Type one of `en`, `hi`, `ta`, or `te` and press Enter. `en` routes through Whisper; `hi`/`ta`/`te` route through IndicConformer (which will download on first use — another few GB, one-time). Speak a short sentence **in that language** when prompted — speaking English while `hi`/`ta`/`te` is selected (or vice versa) will produce nonsense, since neither model is doing language detection, only transcription in the language you told it to expect.

## B5 — Check both windows

**Sender window should show, after your speech:**
```
VAD detected N speech segment(s):
  Segment 1: 0.XXs to Y.YYs
  ...

TRANSCRIBED: "..."
Sending X packet(s) over real network to 127.0.0.1...
✅ All X packets delivered (attempt 1).
Message fully delivered.
```
The `VAD detected...` lines are new in v2 — use them as a sanity check. If you spoke a full sentence but see only one tiny fragment (well under a second) or several disconnected fragments with big gaps, your mic volume is likely too quiet — go back to A11.

**Receiver window should show:**
```
Incoming message: X packet(s) expected, language=en (or hi/ta/te)
Decoded text: "..."
✅ Speech synthesized and saved to received_speech.wav
```

## B6 — Play back the result

Find `received_speech.wav` in your project folder and play it — you should hear a synthesized voice speaking back what you said, in the language you chose.

**If Stage 1 works correctly, move to Part C. If something fails here, fix it before attempting two physical laptops** — it's much easier to debug on one machine.

---

# PART C — Stage 2: Real Two-Laptop Test

Now repeat with sender and receiver on two separate physical laptops, both connected to the **same WiFi network**.

## C1 — Get the receiver laptop's IP address

On the **receiver laptop**, run:
```powershell
ipconfig
```
Find **IPv4 Address** under your active WiFi adapter (e.g. `192.168.1.42`). Write this down.

## C2 — Set the real IP on the sender laptop

On the **sender laptop** (the one with the mic):
```powershell
notepad network_sender.py
```
Find:
```python
RECEIVER_IP = "127.0.0.1"
```
Change to the receiver laptop's actual IP from C1, e.g.:
```python
RECEIVER_IP = "192.168.1.42"
```
Save and close.

## C3 — Start the receiver first (on the receiver laptop)

```powershell
cd Desktop\iTantra-version2
venv\Scripts\Activate.ps1
python network_receiver.py
```

**A Windows Firewall popup will likely appear** the first time — click **"Allow access"** (specifically for Private networks).

Wait for:
```
Listening for messages on port 5005...
```

## C4 — Start the sender (on the sender laptop)

```powershell
cd Desktop\iTantra-version2
venv\Scripts\Activate.ps1
python network_sender.py
```

Same as B4 — choose your language at the prompt, then speak your message when prompted.

## C5 — Verify it worked

Same expected output as Stage 1 (Part B5), but now happening across two physical machines over real WiFi. The receiver laptop should play synthesized speech through its own speakers from `received_speech.wav`, generated from a message that was recorded on a completely different laptop, using whichever STT model matched the language you chose.

## C6 — Prove the bandwidth reduction is real (optional but impressive for judges)

After a successful run, check the sender laptop's project folder for `actual_raw_recording.wav` — this is your real recorded audio. Compare its file size (right-click → Properties) against the "Transmitted size" printed in the sender's terminal. This is a genuine, measured comparison — not a theoretical estimate — and holds regardless of which STT model produced the text, since compression happens after transcription either way.

## C7 — (Optional) Verify IndicConformer accuracy directly, side by side

If you want to show a judge the actual evidence behind the v1→v2 STT switch rather than just describing it: after a Tamil/Hindi/Telugu run, `actual_trimmed_audio.wav` in the project folder is the exact clean clip that was transcribed. You can run `test_indicconformer.py` against it to see IndicConformer's CTC and RNNT decoder outputs side by side, and compare against what `network_sender.py` already produced. Both decoders agreeing closely with each other (and with what was actually said) is a reasonable live confidence check, not just a canned demo.

---

## Troubleshooting

### Receiver never gets anything / sender times out waiting for a response
- Double-check the IP address in `network_sender.py` exactly matches what `ipconfig` showed on the receiver laptop
- Confirm both laptops are on the **same WiFi network** (not one on WiFi and one on mobile data, and not connected to a "Guest" network that isolates devices from each other — some routers, and many college/enterprise networks, block device-to-device communication on purpose via "client isolation" even though both devices can reach the internet fine)
- Check the Windows Firewall popup was actually allowed on the receiver laptop — if missed, go to Windows Defender Firewall settings and manually allow Python through both Private and Public profiles
- Quick isolation test: from the sender laptop, `ping <receiver's IP>` — consistent "Request timed out" on every attempt suggests network isolation rather than a code problem; occasional drops (e.g. 1 out of 4) suggest a flaky but working connection, and the retry logic should still get your message through

### "No speech detected" repeatedly, or VAD shows only tiny fragmented segments
- Confirm `MIC_INDEX` in `sender_pipeline.py` matches the sender laptop's actual microphone (Part A10) — every laptop has a different index
- Re-check your mic's peak volume with the test in A11 — anything below 0.15 is likely to cause exactly this problem. This was the single most time-consuming issue during v2 development and was ultimately fixed by enabling Microphone Boost in Windows sound settings, not by any code or model change
- Speak clearly and start talking the instant "Listening..." appears — a several-second delay before speaking can push your actual speech outside the recording window's usable portion
- If `actual_raw_recording.wav` sounds like background music, a video, or someone else talking rather than the intended speaker, the mic is picking up ambient audio competing with the intended voice — move to a quieter space or closer to the mic

### Transcription comes out as real-sounding words in the wrong language, or nonsense in a way that reads like a coherent (but wrong) sentence
- Confirm the language you typed at the `network_sender.py` prompt actually matches the language you spoke — neither model detects the language automatically, and forcing the wrong language onto real speech tends to produce fluent-sounding, entirely incorrect output rather than an obvious error

### `AttributeError: module 'onnxruntime' has no attribute 'InferenceSession'`
- You have both `onnxruntime` and `onnxruntime-gpu` installed at once — see the warning in A7. Uninstall both and reinstall only the one you actually need

### Wall of `[E:onnxruntime:...] Error loading "onnxruntime_providers_cuda.dll" which depends on "cublasLt64_13.dll" which is missing` repeated many times
- This means `onnxruntime-gpu` can't find the NVIDIA CUDA Toolkit/cuDNN files — either A6C wasn't completed, or a restart is still needed after installing them
- This is **not fatal** — `onnxruntime` automatically falls back to CPU and IndicConformer will still produce correct transcriptions, just slower. Safe to ignore if you don't need GPU speed right now; otherwise revisit A6C

### `GatedRepoError` / `403 Client Error` / "Cannot access gated repo" when loading either model
- One or both of the two Hugging Face model access requests from A9 hasn't been approved yet, or you're logged in as the wrong account — check with `hf auth whoami`, and check both model pages directly to confirm your access status

### `PortAudioError` or `DirectSound error`
- Close other apps using the microphone (Zoom, Teams, browser tabs)
- Restart Windows Audio service: open PowerShell **as Administrator**, run `Restart-Service -Name AudioSrv -Force`
- Restart the laptop as a last resort

### Everything is very slow (30-90+ seconds per message)
- Expected on CPU-only laptops, or on GPU laptops that skipped A6C — IndicConformer is a larger model than Whisper-small was in v1, so this is more noticeable in v2. Not a bug, just a hardware/setup limitation of the current prototype

### Different WiFi networks / can't reach each other at all
- This method only works when both laptops are on the **same local network**. If testing remotely from different locations, you'll need something like Tailscale (a free virtual network tool) — ask before attempting this, it's a separate setup process.

---

## Reporting Back

If stuck, share:
1. Which **Part/Step** you're on (e.g. "C4")
2. The exact command you ran
3. The full error message from **both** terminal windows if relevant
4. Whether you're on the GPU or CPU path (Part A5), and if GPU, whether A6C (CUDA Toolkit + cuDNN) was completed
5. Which language you selected at the `network_sender.py` prompt
6. Confirm both laptops show the same WiFi network name
7. If it's a transcription-accuracy question specifically, your mic's peak volume reading from A11

This lets whoever's helping fix it quickly instead of guessing.
