# iTantra — Receiver Laptop Setup Guide

This guide covers everything needed to set up **one laptop as the RECEIVER** in the iTantra two-laptop network model. The receiver laptop listens over WiFi (UDP), reassembles the incoming text packets, decompresses them, and speaks the message out loud using AI4Bharat's Indic Parler-TTS model.

> This laptop does **not** need a microphone. It **does** need working speakers/headphones and a stable connection to the same WiFi network as the sender laptop.

Relevant files in the repo for this role: `network_receiver.py`, `receiver_pipeline.py`, `bitrate_sim.py`, `network_common.py`.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Step-by-step Setup](#2-step-by-step-setup)
3. [Hugging Face Account & Gated Model Access](#3-hugging-face-account--gated-model-access)
4. [Finding the Receiver's IP Address](#4-finding-the-receivers-ip-address)
5. [Windows Firewall](#5-windows-firewall)
6. [Running the Receiver](#6-running-the-receiver)
7. [How the Receiver Works Internally](#7-how-the-receiver-works-internally)
8. [Verifying a Successful Run](#8-verifying-a-successful-run)
9. [Full Troubleshooting Reference](#9-full-troubleshooting-reference)
10. [Reporting a Problem to the Team](#10-reporting-a-problem-to-the-team)
11. [Reference Links](#11-reference-links)

---

## 1. Prerequisites

| Requirement | Details |
|---|---|
| OS | Windows laptop (this guide is Windows-specific; the repo's guides assume PowerShell) |
| RAM | 8 GB minimum |
| Disk space | ~10 GB free (models + dependencies) |
| Audio | Working **speakers or headphones** (no mic needed on this laptop) |
| Network | Connected to the **same WiFi network** as the sender laptop, and **not** a "Guest" network (guest networks often block device-to-device traffic) |
| Internet | Stable connection for the initial setup — downloads total several GB |
| Account | A free Hugging Face account (needed to access the gated TTS model) |

**Time required:** ~45–90 minutes for a completely fresh laptop, mostly downloads.

---

## 2. Step-by-step Setup

### Step 1 — Check/install Python

```powershell
python --version
```
Expected: `Python 3.11.x` or `Python 3.13.x`.

If you get **"python is not recognized"**:
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11 (recommended)
3. Run the installer
4. ⚠️ **Check the box "Add Python to PATH"** before clicking Install — if you miss this, you'll need to reinstall
5. Close and reopen PowerShell, re-run `python --version` to confirm

### Step 2 — Check/install Git

```powershell
git --version
```
If not recognized, install from [git-scm.com/downloads](https://git-scm.com/downloads) with default settings, then reopen PowerShell and confirm.

### Step 3 — Clone the repository

```powershell
cd Desktop
git clone https://github.com/itz-Arun-001/iTantra.git
cd iTantra
```
Expected: a new `iTantra` folder containing `network_receiver.py`, `receiver_pipeline.py`, `network_common.py`, `bitrate_sim.py`, etc.

### Step 4 — Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**⚠️ Error: "running scripts is disabled on this system"**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then re-run the activate command. This only applies to the current PowerShell window — you'll need to repeat it every time you open a **new** window before activating.

Expected: your prompt now starts with `(venv)`.

**Reminder:** Every time you close and reopen PowerShell, `cd` back into `iTantra` and re-run `venv\Scripts\Activate.ps1` before running any Python command — otherwise you'll get "module not found" errors even though everything is installed.

### Step 5 — Check for an NVIDIA GPU

```powershell
nvidia-smi
```
- **Shows a GPU info table** → go to Step 6A (this laptop will run TTS faster)
- **"nvidia-smi is not recognized"** → go to Step 6B (CPU-only, still fully supported — just slower)

### Step 6A — Install PyTorch (GPU / NVIDIA path)

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```
This is a **large download (~2.5 GB)**.

**⚠️ `ConnectionResetError` or download times out** → this is a normal, temporary network hiccup on unstable WiFi. Just **re-run the exact same command**; pip resumes the partial download. 2–3 attempts is common.

Skip Step 6B.

### Step 6B — Install PyTorch (CPU-only path)

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
Smaller download (~200–300 MB). Expect TTS synthesis to take **15–40+ seconds per message** on CPU — this is expected, not a bug.

### Step 7 — Install the remaining dependencies

```powershell
pip install transformers onnxruntime soundfile numpy sounddevice torchaudio flask flask-cors
pip install git+https://github.com/huggingface/parler-tts.git
```

If you're on the **GPU path**, also run:
```powershell
pip install torchaudio --index-url https://download.pytorch.org/whl/cu124
```

Expected: a long list of downloads ending in `Successfully installed ...` with no red `ERROR` lines. Yellow `WARNING` lines are safe to ignore.

**⚠️ `git+https://github.com/huggingface/parler-tts.git` install fails** — usually means Git isn't installed/on PATH (recheck Step 2), or the network blocked github.com momentarily — retry the command.

### Step 8 — Verify the install

```powershell
python -c "import torch, transformers, sounddevice; print('All good! CUDA:', torch.cuda.is_available())"
```
Expected: `All good! CUDA: True` (GPU path) or `All good! CUDA: False` (CPU path) — both are fine, the important part is **no errors**.

---

## 3. Hugging Face Account & Gated Model Access

The receiver loads **AI4Bharat Indic Parler-TTS**, which is a *gated* model — you must request access and authenticate, or the receiver script will fail on startup.

1. Sign up free at [huggingface.co](https://huggingface.co) if you don't already have an account.
2. Go to [huggingface.co/ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) and click to request access (short form, usually approved within minutes, sometimes needs manual approval — don't proceed to run the receiver until you see "access granted"/you can view the model files).
3. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), click **New token**, name it anything, select the **Read** role, click **Create**, and copy the token.
4. Log in from your terminal:
   ```powershell
   huggingface-cli login
   ```
   Right-click to paste your token when prompted, press Enter. Type `y` if asked about git credentials.

Expected output: `Login successful.`

**⚠️ `GatedRepoError` when starting `network_receiver.py`** → this means Step 3 above wasn't completed on **this specific laptop**. Each teammate's laptop needs its own Hugging Face account + access request + login — one person being approved doesn't grant access to everyone.

---

## 4. Finding the Receiver's IP Address

The sender laptop needs to know this laptop's IP address to send packets to it.

On the **receiver laptop**, run:
```powershell
ipconfig
```
Look under your active WiFi adapter for **IPv4 Address**, e.g. `192.168.1.42`. Write this down and give it to whoever is running the sender — they will paste it into `RECEIVER_IP` in `network_sender.py` on the sender laptop.

**Notes:**
- This IP can change if you reconnect to WiFi or restart the laptop — re-check it if the sender suddenly can't reach you.
- This only works when both laptops are on the **same local network**. For testing across different locations/networks, a tool like [Tailscale](https://tailscale.com/) is needed (separate setup, ask the team before attempting this).

---

## 5. Windows Firewall

The first time you run `network_receiver.py`, **Windows Defender Firewall will likely pop up** asking to allow Python to communicate on networks.

- Click **"Allow access"**.
- If the popup only mentions "Private networks", but you're on a network Windows classifies as "Public" (uncommon on home/office WiFi, but happens on some routers), also check the **Public** box, or fix this manually:
  - Open **Windows Defender Firewall with Advanced Security**
  - Go to **Inbound Rules** → find the Python rule (or add a new one) → allow UDP for both Private and Public profiles

**⚠️ If you missed the popup** and don't see it again: go to **Windows Security → Firewall & network protection → Allow an app through firewall**, find Python, and check both Private and Public boxes.

---

## 6. Running the Receiver

Always do this **before** the sender starts sending (start the receiver first, so it's listening).

```powershell
cd Desktop\iTantra
venv\Scripts\Activate.ps1
python network_receiver.py
```

**First run only:** this will download the Indic Parler-TTS model weights (several GB) — this can take a while depending on your connection. Subsequent runs load from a local cache and start much faster.

**Expected output once ready:**
```
Using device: cpu   (or "cuda" if you have a GPU)
Loading Indic Parler-TTS model...
Listening for messages on port 5005...
```

Leave this window open and running — it will print incoming messages as they arrive.

---

## 7. How the Receiver Works Internally

Useful to know when debugging:

- **Transport:** raw UDP socket bound to `0.0.0.0:5005` (`network_common.py` defines `PORT = 5005`).
- **Packet format:** each UDP packet has a 12-byte header (`sequence number`, `total packets`, `payload length`, all as unsigned ints) followed by up to 200 bytes of payload (`PACKET_SIZE = 200`).
- **Message flow:**
  1. Sender sends a `META` packet first — a JSON blob with `total` (packet count), `was_compressed` (bool), and `language` (e.g. `"en"`, `"hi"`, `"ta"`, `"te"`).
  2. Sender then sends the numbered data packets.
  3. Sender sends a `CHECK` request; the receiver replies with either a JSON list of **missing** sequence numbers (triggering a retry) or `ALL_RECEIVED`.
  4. Once complete, the receiver reassembles the chunks in order, decompresses (gzip, if `was_compressed` is true) via `bitrate_sim.decompress_text`, and calls `speak_text()`.
- **TTS step:** `receiver_pipeline.speak_text()` picks a per-language voice description (English/Hindi/Tamil/Telugu supported), tokenizes text + description, runs `model.generate(...)`, and writes the result to `received_speech.wav` in the project folder at the model's native sample rate.
- **Only 4 languages currently supported end-to-end:** English (`en`), Hindi (`hi`), Tamil (`ta`), Telugu (`te`). Any other language code falls back to the English voice description, which will sound wrong for non-English text.

---

## 8. Verifying a Successful Run

After the sender sends a message, the receiver terminal should show:

```
Incoming message: X packet(s) expected, language=en

RECEIVED ... bytes over the link.
Decoded text: "Medical emergency near the village. Send help immediately."

Generating speech for: "Medical emergency near the village. Send help immediately."
✅ Speech saved to received_speech.wav
✅ Speech synthesized and saved to received_speech.wav
```

Then:
1. Locate `received_speech.wav` in the `iTantra` project folder (it's overwritten on every new message).
2. Double-click to play it, or open it in any media player.
3. You should hear a synthesized voice speaking back the transcribed message.

If you don't hear anything even though the file was created, the problem is Windows audio output, not the pipeline — see the troubleshooting section below.

---

## 9. Full Troubleshooting Reference

### `GatedRepoError` on startup
The Hugging Face access request / login (Section 3) wasn't completed on **this** laptop. Go back and finish it — this is per-machine/per-account, not shared across the team.

### Receiver never receives anything / sender times out
- Confirm the IP the sender typed into `RECEIVER_IP` in `network_sender.py` **exactly** matches this laptop's current `ipconfig` output (Section 4) — a stale IP from an earlier session is the most common cause.
- Confirm both laptops are on the **same WiFi network** — not one on WiFi and one on mobile data.
- Avoid "Guest" WiFi networks — many routers isolate guest devices from each other so they can't reach each other even on the "same" network.
- Confirm the Windows Firewall popup was allowed (Section 5). If missed, add the manual rule described there.
- Confirm `network_receiver.py` was started **before** the sender tried to send, and is still running (not crashed/closed).

### `OSError: [WinError 10048] ... Only one usage of each socket address...` / "port already in use"
Another instance of `network_receiver.py` is already running and holding port 5005.
- Check for and close any other PowerShell window running the receiver.
- Or find and kill the stray process:
  ```powershell
  netstat -ano | findstr 5005
  taskkill /PID <pid_from_above> /F
  ```

### Model download seems stuck / very slow on first run
- This is normal for the first run — Indic Parler-TTS weights are multiple GB. Let it run on a stable connection.
- If it errors out partway (`ConnectionResetError`, `ReadTimeoutError`), just re-run `python network_receiver.py` — Hugging Face's cache resumes partial downloads.

### No sound plays from `received_speech.wav`, but the file exists and has content
This is a Windows audio output issue, not a pipeline issue:
1. Check the correct playback device is selected: right-click speaker icon → **Sound settings** → Output → confirm the right device, volume isn't at 0.
2. Check the file actually has audio: right-click the `.wav` → Properties → check its size is non-trivial (a few hundred KB, not a few bytes).
3. Try playing it in a different app (e.g. VLC) in case the default player has a codec issue.
4. Confirm speakers/headphones aren't muted via a physical key or software toggle.

### Decoded text is garbled or wrong
- The **language code** sent by the sender must match the actual language spoken — there's no automatic language detection. If the sender selected the wrong language, the transcription (and therefore the TTS voice/pronunciation) will be wrong. This is a sender-side fix, not a receiver bug.
- If `language` isn't one of `en`/`hi`/`ta`/`te`, the receiver silently falls back to the English voice description — check the `language=` value printed in "Incoming message: ... language=..." to confirm what was actually sent.

### `CUDA out of memory` (GPU path only)
- Close other GPU-heavy applications (games, other model-serving processes, browser tabs with heavy WebGL/video).
- If it persists, temporarily force CPU by uninstalling the CUDA build of torch and reinstalling the CPU build (Step 6B) — slower, but avoids the crash.

### `PortAudioError` / `DirectSound error` (rare on the receiver, since it doesn't use the mic, but `sounddevice` is still imported)
- Close other apps that might be holding an audio device (Zoom, Teams, browser tabs with active calls).
- Restart the Windows Audio service (PowerShell **as Administrator**):
  ```powershell
  Restart-Service -Name AudioSrv -Force
  ```
- Restart the laptop as a last resort.

### Everything is very slow (30–60+ seconds per message)
Expected on CPU-only laptops without an NVIDIA GPU — this is a hardware limitation of the current prototype, not a bug. It will not get meaningfully faster without a GPU or a smaller/quantized model.

### `ModuleNotFoundError` for a package you already installed
You forgot to activate the virtual environment in this PowerShell window:
```powershell
cd Desktop\iTantra
venv\Scripts\Activate.ps1
```
Confirm `(venv)` shows in the prompt, then re-run the script.

### Different WiFi networks entirely / can't reach each other at all
Real UDP transmission over `network_receiver.py`/`network_sender.py` only works on the **same local network**. For remote testing across different locations, you need a virtual network layer such as [Tailscale](https://tailscale.com/) — this is a separate setup process; coordinate with the team before attempting it.

---

## 10. Reporting a Problem to the Team

If you get stuck, share all of the following so someone can help without guessing:

1. Which step/section you were on (e.g. "Section 6, first run")
2. The **exact command** you ran
3. The **complete** error message/output (not a paraphrase or screenshot description)
4. Whether you're on the GPU or CPU path (Section 5's `nvidia-smi` result)
5. This laptop's IP from `ipconfig`, and confirmation both laptops show the same WiFi network name
6. Whether the Hugging Face login (Section 3) completed successfully

---

## 11. Reference Links

- Python downloads: https://www.python.org/downloads/
- Git downloads: https://git-scm.com/downloads
- PyTorch install matrix (for other CUDA versions): https://pytorch.org/get-started/locally/
- Hugging Face sign-up: https://huggingface.co
- Hugging Face access tokens: https://huggingface.co/settings/tokens
- Indic Parler-TTS model page (request access here): https://huggingface.co/ai4bharat/indic-parler-tts
- Parler-TTS source (installed via `pip install git+...`): https://github.com/huggingface/parler-tts
- Tailscale (for cross-network testing): https://tailscale.com/
- Project repository: https://github.com/itz-Arun-001/iTantra
