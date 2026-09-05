# 📡 iTantra v2 — Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for Low-Bitrate Links

> **Speak in your language. Send it over almost nothing. Hear it come out the other side.**

iTantra is a Smart India Hackathon (SIH26173) build tackling a simple but hard problem: **voice is expensive to transmit, but in an emergency, voice is the message people actually understand.** iTantra converts speech to text on-device, sends only the (tiny) text payload over a low-bitrate link, and reconstructs speech on the receiving end — so a distress call can travel over a link that could never carry raw audio.

This is **v2** of the project. The core idea, the pipeline shape, and the web UI are unchanged from v1 — what's different is the **speech-to-text engine** for Indian languages. v1 used OpenAI's Whisper for every language; v2 routes Tamil, Hindi, and Telugu through AI4Bharat's IndicConformer instead, after real testing showed it's substantially more accurate on these languages than Whisper. Full details and the actual comparison evidence are in [What Changed in v2](#-what-changed-in-v2) at the end of this document.

This repo contains a **working, end-to-end desktop prototype** with two proven transport paths: a polished web UI with simulated packet loss for demos, and a genuine two-laptop UDP network implementation — real packets, real WiFi, real packet loss and priority-aware retries, tested and confirmed working across two separate physical laptops. It runs on a laptop today; porting the validated pipeline to Android is the next phase. See [Project Status](#-project-status) for exactly what's built vs. planned.

---

## 📑 Table of Contents

- [Problem Statement](#-problem-statement)
- [Core Idea](#-core-idea)
- [Project Status](#-project-status)
- [Pipeline Architecture](#-pipeline-architecture)
- [Repository Structure](#-repository-structure)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [Tech Stack](#-tech-stack)
- [Evaluation Metrics (per PS)](#-evaluation-metrics-per-ps)
- [Roadmap](#-roadmap)
- [Known Limitations](#-known-limitations)
- [Contributing](#-contributing)
- [What Changed in v2](#-what-changed-in-v2)
- [License](#-license)

---

## 🎯 Problem Statement

**SIH Problem Statement (SIH26173):** *Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for Low Bitrate Links*

**Background:** Voice is highly data-intensive, making it hard to transmit over low-data-rate links. In alert and distress scenarios, however, transmitting *audio* — not text — is critical, because it's inclusive of people regardless of literacy.

**Ask:** Build an Android app with lightweight, accurate on-device STT and TTS for **10 Indian languages** (Hindi, Gujarati, Marathi, Kannada, Malayalam, Tamil, Telugu, Odia, Bengali, English) that:

- 🎙️ Detects speech, waits for a natural pause, and converts it to text (STT) locally
- 📶 Streams that text with minimal latency over Wi-Fi/Bluetooth to another phone or embedded device running the same app
- 🔊 Converts received text back into intelligible speech (TTS), playing it as a voice note — with emergency alerts announced at max volume and non-interruptible
- 📻 Works like a **push-to-talk walkie-talkie** between two phones (or degrades gracefully to a normal phone when the feature is off)
- 💻 Runs **fully offline**, on **low/mid-range Android hardware**, using **open-source only** frameworks — no proprietary or cloud-hosted APIs

**Judged on:** Efficiency (model/app size, CPU/RAM footprint) · Accuracy (low WER for STT, natural/legible TTS) · Latency (speech→text time, text→speech time, end-to-end phone-to-phone delay, RTF).

---

## 💡 Core Idea

> Don't send the audio. Send the *meaning*, and rebuild the audio at the other end.

```
🗣️  Speaker's voice
      │
      ▼
 [ On-device STT: Whisper (English) or IndicConformer (Tamil/Hindi/Telugu) ]
      │
      ▼
 "Medical emergency near the village. Send help immediately."
      │
      ▼
 [ Text compression ]  ──►  a few dozen bytes, not a few hundred KB of audio
      │
      ▼
 [ Low-bitrate link: real UDP transport (WiFi-based today) or simulated in the web demo ]
      │
      ▼
 [ On-device TTS at receiver: AI4Bharat Indic Parler-TTS ]  ──►  🔊 spoken voice note
```

A typical spoken sentence costs **~64 kbps as raw audio** but only a **few hundred bits as text** — a measured bandwidth reduction of **98.44%** in this prototype at the LOW bitrate setting, calculated directly from real recorded file sizes, not estimated.

---

## 🚦 Project Status

This repo is a **working, end-to-end desktop prototype** with two proven transport paths — not yet the Android deliverable described in the PS.

| Component (per PS) | Status | Notes |
|---|---|---|
| Speech capture + VAD (pause detection) | ✅ Working | `sender_pipeline.py` — Silero VAD trims silence, with onset/offset padding and a tuned `threshold=0.35` after diagnosing that quiet/short speech was being trimmed out; every run now prints detected segment timestamps |
| STT (English) | ✅ Working | `openai/whisper-large-v3-turbo` via Hugging Face `transformers` |
| STT (Tamil / Hindi / Telugu) | ✅ Working | `ai4bharat/indic-conformer-600m-multilingual`, RNNT decoder — validated as substantially more accurate than Whisper on these languages via direct side-by-side testing (see [What Changed in v2](#-what-changed-in-v2)) |
| Text compression / bitrate simulation | ✅ Working | `bitrate_sim.py` — gzip (auto-skipped when it doesn't help on short text) + simulated transmission time across HIGH/MEDIUM/LOW/EXTREME bitrate modes |
| **Real network transmission (two physical laptops)** | ✅ Working | `network_sender.py` + `network_receiver.py` — genuine UDP sockets, throttled to a target bitrate, real ACK/missing-packet retry (priority-aware: Emergency gets more attempts), language selected at runtime via a terminal prompt. Tested end-to-end across two separate physical laptops on the same WiFi — see `CHECKING_TWO_LAPTOP_MODEL.md` |
| Packet loss / reliable transmission (web demo path) | ✅ Working, but simulated | `packet_reliability.py` — packetizes the payload and simulates loss with `random.random()` **within a single process**; this is what the web UI uses, not the real socket link above |
| TTS (speech synthesis on receive) | ✅ Working — 4 languages | `receiver_pipeline.py` — AI4Bharat **Indic Parler-TTS**, with a per-language voice description. Unchanged from v1 — the receiver has no dependency on which STT model produced the incoming text |
| Full pipeline integration | ✅ Working | `full_pipeline_demo.py` (CLI, in-process simulation), the **Flask API + web UI**, and `network_sender.py`/`network_receiver.py` (real network) all run the complete mic → VAD → STT → compress → transmit → decompress → TTS loop |
| Web-based demo UI | ✅ Working | `api_server.py` (Flask backend) + `itantra-ui/` (Next.js/React frontend) — live recording, bitrate mode selector, Normal/Emergency priority toggle, language picker, real-time transmission stats, and receiver audio playback. **Already uses the dual-STT pipeline** (Whisper/IndicConformer) since `api_server.py` calls the same shared `sender_pipeline.py` code as the CLI tools — selecting Hindi/Tamil/Telugu here automatically routes through IndicConformer. **Still uses the simulated packet-loss transport, not the real UDP link** — see [Roadmap](#-roadmap) |
| Desktop Tkinter UI | ✅ Working (earlier iteration) | `demo_ui.py` — a simpler standalone Tkinter version of the loop, kept as a lighter-weight fallback demo |
| Android app | 🔜 Not started | Current pipeline runs on a Windows laptop |
| Wire the real UDP transport into the web UI | 🔜 Not started | The polished demo (`api_server.py`) still calls `packet_reliability.py`'s in-process simulation for "transmission," not the real socket link. **STT itself is not part of this gap** — `api_server.py` already shares `sender_pipeline.py` with the CLI tools, so it already gets Whisper/IndicConformer branching automatically |
| Bluetooth / Wi-Fi Direct (infrastructure-free) transport | 🔜 Not started | The real UDP link proves genuine two-device transmission and packet-loss recovery, but still runs over a WiFi router — not yet the PS's "no infrastructure" scenario |
| Push-to-talk walkie-talkie mode | 🔜 Not started | |
| On-device (TFLite / ONNX Mobile) model conversion | 🔜 Not started | Current models run via full PyTorch/`transformers`/`onnxruntime`, not yet quantized for mobile |
| All 10 PS-required languages | 🔜 Partial | 4 of 10 demonstrated (English, Hindi, Tamil, Telugu). AI4Bharat's IndicConformer multilingual checkpoint already supports the remaining 6 (Gujarati, Marathi, Kannada, Malayalam, Odia, Bengali) — adding them is now primarily an integration + validation task, not a new model search |

**In short:** the full loop — mic → VAD → STT → compress → transmit → decompress → TTS — is validated and working three different ways: a CLI script, a polished web UI, and a real UDP socket link proven across two physical laptops. STT accuracy on Indian languages is now backed by a purpose-built model (IndicConformer) instead of a general multilingual one, with real comparative evidence — and because the web UI shares the same `sender_pipeline.py` code as the CLI tools, it already benefits from this automatically. What's left near-term is wiring the *real UDP transport* (not the STT) into the polished web demo; longer-term it's the **mobile port** (Android, on-device model optimization, Bluetooth transport).

---

## 🏗️ Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              SENDER SIDE                                  │
│                                                                            │
│   🎤 Mic input                                                            │
│      │                                                                    │
│      ▼                                                                    │
│   Silero VAD  ──►  detects speech start/stop, trims silence (padded,     │
│                     threshold=0.35, prints segment timestamps)            │
│      │                                                                    │
│      ▼                                                                    │
│   ┌─────────────────────────┴──────────────────────────┐                 │
│   │  language == "en"?                                  │                 │
│   ▼                                                      ▼                 │
│  Whisper large-v3-turbo                    IndicConformer (RNNT decoder) │
│  (English STT)                             (Tamil / Hindi / Telugu STT)  │
│   │                                                      │                 │
│   └─────────────────────────┬──────────────────────────┘                 │
│                              ▼                                            │
│                     transcribed text                                     │
│                              │                                            │
│                              ▼                                            │
│   gzip compression (bitrate_sim.py)  ──►  raw bytes if gzip doesn't help │
│      │                                                                    │
│      ▼                                                                    │
│   Bitrate-mode simulation  ──►  HIGH / MEDIUM / LOW / EXTREME kbps        │
└──────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┴────────────────────────┐
        ▼                                                  ▼
  REAL UDP TRANSPORT                              SIMULATED TRANSPORT
  (network_sender.py /                            (packet_reliability.py,
  network_receiver.py, genuine                    used by the web UI —
  packets over WiFi between                       in-process, random-
  two physical laptops)                           loss simulation)
        │                                                  │
        └───────────────────────┬────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                             RECEIVER SIDE                                 │
│                                                                            │
│   Reassemble packets  ──►  decompress text                               │
│      │                                                                    │
│      ▼                                                                    │
│   receiver_pipeline.py: speak_text()  ──►  Indic Parler-TTS synthesis    │
│      │                    (unchanged — doesn't know or care which        │
│      │                     STT model produced the incoming text)         │
│      ▼                                                                    │
│   🔊 Played as voice note / non-interruptible alert                      │
└──────────────────────────────────────────────────────────────────────────┘

              ┌────────────────────────────────────────┐
              │   api_server.py (Flask, port 5000)      │
              │   shares sender_pipeline.py, so it      │
              │   already gets v2's dual-STT branching  │
              │   — only the transport is still         │
              │   simulated, not the real UDP link       │
              └───────────────┬──────────────────────────┘
                               │
              ┌────────────────▼──────────────────────────┐
              │   itantra-ui/ (Next.js, port 3000)         │
              │   record button · bitrate & priority       │
              │   controls · language picker · live stats  │
              │   · receiver audio playback                │
              └─────────────────────────────────────────────┘
```

---

## 📂 Repository Structure

```
iTantra-version2/
├── PART1_SETUP_GUIDE.md         # Windows environment setup (Python, venv, PyTorch, CUDA, mic check)
├── CHECKING_ONE_LAPTOP_MODEL.md # Zero-to-running setup guide for a teammate's fresh laptop
├── CHECKING_TWO_LAPTOP_MODEL.md # Step-by-step guide for real UDP transport across two physical laptops
├── check_mic.py                 # Mic sanity check using device-native sample rate + resample to 16kHz
├── check_mic2.py                # Variant mic check, hardcoded device index
├── test_vad.py                  # Standalone VAD + STT test: records, trims silence, transcribes
├── test_stt.py                  # Standalone STT test: records fixed duration, transcribes with Whisper
├── test_tts.py                  # Standalone TTS test: generates output_speech.wav from hardcoded text
├── test_indicconformer.py       # Standalone IndicConformer test — CTC + RNNT decoding on a saved wav file; this is the script used to produce the comparison evidence in "What Changed in v2"
├── sender_pipeline.py           # Sender flow: record → VAD trim (padded) → STT (Whisper or IndicConformer, branched by language) → compress
├── receiver_pipeline.py         # Receiver flow: decompress → Indic Parler-TTS speech synthesis (unchanged from v1)
├── bitrate_sim.py                # Text compression + simulated transmission time across bitrate modes
├── packet_reliability.py        # In-process only: packetization, simulated (random.random()) loss, priority-aware retry — used by the web demo
├── network_common.py            # Shared packet header format + chunking helpers for the real UDP transport
├── network_sender.py            # REAL UDP socket sender — prompts for language at runtime, records → STT → compress → sends over actual WiFi to another laptop
├── network_receiver.py          # REAL UDP socket receiver — listens on port 5005, reassembles, decompresses, speaks the result (language read from the sender's META packet)
├── full_pipeline_demo.py        # CLI end-to-end demo: sender → simulated lossy link → receiver TTS (v1 pipeline, Whisper-only)
├── demo_ui.py                   # Tkinter desktop UI wrapping the full pipeline (earlier iteration, v1 pipeline)
├── api_server.py                # Flask API exposing the pipeline as 3 HTTP steps for the web UI (still v1 pipeline — see Roadmap)
├── itantra-ui/                  # Next.js/React web frontend (the primary demo interface)
├── output_speech.wav            # Sample TTS output (from test_tts.py)
├── received_speech.wav          # Sample receiver-side TTS output (regenerated on each run)
└── iTantra_SIH_Analysis.md      # Problem-statement analysis / strategy notes
```

---

## 🛠️ Getting Started

**New to this repo with nothing installed?** Follow **`CHECKING_ONE_LAPTOP_MODEL.md`** — it goes from a completely empty laptop to a running demo, step by step, including Node.js/Git/Hugging Face account setup, CUDA/cuDNN installation, and troubleshooting.

**Already have Python set up?** Follow **`PART1_SETUP_GUIDE.md`** for the environment basics, then:

1. Install the backend dependencies:
   ```powershell
   pip install flask flask-cors
   pip install git+https://github.com/huggingface/parler-tts.git
   pip install transformers torch torchaudio --index-url https://download.pytorch.org/whl/cu128
   pip install onnxruntime-gpu soundfile sounddevice numpy
   ```
   **Do not** also have plain `onnxruntime` installed alongside `onnxruntime-gpu` — they conflict, since they share the same import name. If `pip list` shows both, run `pip uninstall onnxruntime -y` and keep only `onnxruntime-gpu`.

2. **Request access to both gated Hugging Face models** — v2 needs two, not one:
   - [huggingface.co/ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) (TTS, same as v1)
   - [huggingface.co/ai4bharat/indic-conformer-600m-multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) (STT for Tamil/Hindi/Telugu, **new in v2**)

   Then generate a token and log in:
   ```powershell
   hf auth login
   ```
   (`huggingface-cli login` is deprecated; use `hf auth login` instead.)

3. **Install NVIDIA CUDA Toolkit 13.x and cuDNN 9.x system-wide** — this is new in v2 and is a separate install from anything `pip` handles. Without it, IndicConformer still works correctly, just on CPU (noticeably slower). See `PART1_SETUP_GUIDE.md` for the full walkthrough, including how to install to a non-default drive if C: space is limited.

4. Find your microphone's device index and update `MIC_INDEX` in `sender_pipeline.py`:
   ```powershell
   python -c "import sounddevice as sd; print(sd.query_devices())"
   ```

5. Install the frontend:
   ```powershell
   cd itantra-ui
   npm install
   ```

---

## ▶️ Usage

### Web UI (shares v2's dual-STT pipeline; transport is still simulated, not real UDP)

Two terminals, both from the repo root:

```powershell
# Terminal 1 — backend
venv\Scripts\Activate.ps1
python api_server.py
```

```powershell
# Terminal 2 — frontend
cd itantra-ui
npm run dev
```

Then open **http://localhost:3000**, pick a language and bitrate mode, and hit record. Selecting Hindi/Tamil/Telugu automatically routes through IndicConformer, since `api_server.py` shares `sender_pipeline.py` with the CLI tools — the first time you pick one of these three languages, expect an extra multi-minute pause while IndicConformer's model downloads (a few GB, one-time). What the web UI does **not** yet do is use the real two-laptop UDP transport — it always simulates transmission and packet loss on this one machine, even though the real version exists (see below). See [Roadmap](#-roadmap).

### Real two-laptop network demo (v2's proven, real UDP transport)

On the **receiving** laptop:
```powershell
venv\Scripts\Activate.ps1
python network_receiver.py
```
Leave it running — it prints `Listening for messages on port 5005...` and waits.

On the **sending** laptop, first update `RECEIVER_IP` in `network_sender.py` to the receiving laptop's actual local IP (find it with `ipconfig`), then:
```powershell
venv\Scripts\Activate.ps1
python network_sender.py
```
You'll be prompted: `Choose language: en / hi / ta / te` — type the code and press Enter, then speak when prompted. English routes through Whisper; Hindi/Tamil/Telugu route through IndicConformer. Full setup details, including firewall configuration, are in `CHECKING_TWO_LAPTOP_MODEL.md`.

### CLI scripts

| Script | What it does | Run it with |
|---|---|---|
| `check_mic.py` / `check_mic2.py` | Verify mic input is being captured | `python check_mic.py` |
| `test_stt.py` | Record a fixed duration and transcribe with Whisper | `python test_stt.py` |
| `test_vad.py` | Record, auto-detect speech start/stop, then transcribe | `python test_vad.py` |
| `test_tts.py` | Generate speech from a hardcoded sentence | `python test_tts.py` |
| `test_indicconformer.py` | Run IndicConformer's CTC and RNNT decoders on a saved `.wav` file — the script used to validate the v1→v2 switch | `python test_indicconformer.py` |
| `bitrate_sim.py` | See compression + simulated transmission time across bitrate modes | `python bitrate_sim.py` |
| `packet_reliability.py` | See in-process packet loss + priority-based retry simulation | `python packet_reliability.py` |
| `sender_pipeline.py` | Sender-side flow only (record → VAD → STT → compress) | `python sender_pipeline.py` |
| `network_sender.py` | Real UDP sender — prompts for language, sends to another laptop | `python network_sender.py` |
| `network_receiver.py` | Real UDP receiver — listens indefinitely, speaks incoming messages | `python network_receiver.py` |
| `full_pipeline_demo.py` | Full sender + simulated lossy transmission + receiver TTS (CLI, v1 pipeline) | `python full_pipeline_demo.py` |
| `demo_ui.py` | Tkinter desktop GUI version of the v1 pipeline | `python demo_ui.py` |

---

## 🧰 Tech Stack

**Backend:**
- 🐍 Python 3.11+ (also tested on 3.13)
- 🔥 PyTorch / `torchaudio`, CUDA 12.8-enabled build (CPU fallback available)
- 🤗 Hugging Face `transformers` — `openai/whisper-large-v3-turbo` for English STT
- 🧠 **AI4Bharat IndicConformer** (`ai4bharat/indic-conformer-600m-multilingual`, ONNX-based, loaded via `transformers`' `AutoModel` with `trust_remote_code=True`) — Tamil/Hindi/Telugu STT, **new in v2**
- ⚡ `onnxruntime-gpu` — runs IndicConformer's internal ONNX components, GPU-accelerated when NVIDIA CUDA Toolkit 13.x + cuDNN 9.x are installed system-wide, falls back to CPU otherwise
- 🗣️ AI4Bharat **Indic Parler-TTS** — multilingual speech synthesis (unchanged from v1)
- 🎙️ Silero VAD — pause/speech-segment detection, tuned sensitivity (`threshold=0.35`), with segment-level debug logging
- 🔌 `socket` (UDP) — real network transport in `network_sender.py`/`network_receiver.py`, validated across two physical laptops on WiFi
- 🔊 `sounddevice`, `numpy`, `soundfile` — audio I/O
- 📦 `gzip` — text compression before transmission
- 🌶️ Flask + `flask-cors` — HTTP API bridging the (v1) Python pipeline to the web UI

**Frontend:**
- ⚛️ Next.js / React, Tailwind CSS
- Live recording controls, bitrate/priority selectors, language picker, real-time stats, receiver audio playback

**Planned (to meet the full PS requirements):**
- 📱 Android (Kotlin/Java) app shell, replacing the Python/web stack
- ⚡ TensorFlow Lite / ONNX Mobile — quantized, on-device STT/TTS
- 🈯 IndicConformer coverage extended to the remaining 6 PS-required languages (Gujarati, Marathi, Kannada, Malayalam, Odia, Bengali) — the multilingual checkpoint already supports them
- 📶 Android Wi-Fi Direct / Bluetooth transport layer, replacing the current WiFi-router-dependent UDP link
- 🔁 Wiring the real UDP transport into the polished web UI, so the demo people see reflects genuine network transmission (STT already matches — see [Known Limitations](#-known-limitations))

---

## 📊 Evaluation Metrics (per PS)

| Metric | Weight | What it measures | Where it's exercised in this repo |
|---|---|---|---|
| ⚙️ Efficiency | 20% | Model size, app RAM/flash footprint, idle-listening CPU usage | Not yet measured on mobile — current models (Whisper, IndicConformer, Indic Parler-TTS, Silero VAD) are desktop/GPU-scale, not representative of eventual mobile footprint. IndicConformer adds a real, separate CUDA/cuDNN system dependency for GPU acceleration (see `PART1_SETUP_GUIDE.md`), which will need to be replaced with a mobile-appropriate runtime before this metric can be honestly evaluated |
| 🎯 Accuracy | 40% | Low WER (STT), high legibility/flow (TTS) | English (Whisper) and Tamil/Hindi/Telugu (IndicConformer) both demonstrated qualitatively via CLI and real two-laptop tests, with a direct comparative test showing IndicConformer meaningfully outperforms Whisper on Indian languages. No formal WER benchmarking against a labeled dataset yet — comparisons so far are manual, sentence-level |
| ⏱️ Latency | 20% | Speech→text time, text→speech time, phone-to-phone delta, RTF | `bitrate_sim.py` simulates transmission time by bitrate mode (measured, e.g. 98.44% bandwidth reduction at LOW); the real UDP transport's actual wall-clock delay across two laptops has been observed but not formally logged/benchmarked; IndicConformer's CPU-fallback path is noticeably slower than its GPU path, which matters for latency claims if CUDA/cuDNN aren't available on the demo machine |

---

## 🗺️ Roadmap

- [x] Add `receiver_pipeline.py` (TTS `speak_text()`) and `packet_reliability.py` (`transmit_with_retry()`)
- [x] Build a Flask API + web UI wrapping the full pipeline
- [x] Add multi-language support for STT + TTS (English, Hindi, Tamil, Telugu)
- [x] Build a real UDP-socket transport (`network_sender.py`/`network_receiver.py`) and validate it end-to-end across two physical laptops on WiFi
- [x] **Diagnose and fix Whisper's unreliable Tamil/Hindi/Telugu transcription** by validating and integrating AI4Bharat's IndicConformer as a language-specific replacement, with real comparative evidence
- [x] Fix VAD under-sensitivity that was silently trimming quiet/short speech before it reached either STT model
- [x] Move language selection from a hardcoded, edit-and-save value to a runtime prompt in `network_sender.py`
- [ ] **Wire the real UDP transport into `api_server.py`**, replacing `packet_reliability.py`'s simulation, so the polished web demo's transmission step matches the CLI tools' proven real network path (STT already matches, since both share `sender_pipeline.py`)
- [ ] Extend IndicConformer language coverage to the remaining 6 PS-required languages (Gujarati, Marathi, Kannada, Malayalam, Odia, Bengali)
- [ ] Move the real transport off WiFi onto Bluetooth / Wi-Fi Direct (`pybluez`/`bleak`), reusing the existing packet/retry logic, to match the PS's infrastructure-free requirement
- [ ] Quantize/convert STT + TTS models to TensorFlow Lite / ONNX Mobile for on-device inference
- [ ] Port the pipeline into an Android app (Kotlin), replacing Python/Flask/web stack with native AudioRecord/AudioTrack + UI
- [ ] Implement push-to-talk mode with a toggle to fall back to normal phone functionality
- [ ] Implement non-interruptible, max-volume playback for emergency/alert-priority messages
- [ ] Benchmark model size, RAM/flash footprint, and idle CPU usage on actual low/mid-range Android hardware
- [ ] Measure and report WER (STT) and end-to-end / RTF latency across all 10 languages, on both GPU and CPU-fallback paths

---

## ⚠️ Known Limitations

- STT currently supports **4 of 10 PS-required languages** (English via Whisper; Hindi, Tamil, Telugu via IndicConformer); the remaining 6 (Gujarati, Marathi, Kannada, Malayalam, Odia, Bengali) aren't wired up yet, though IndicConformer's multilingual checkpoint already supports them
- The language spoken **must match the language selected at runtime** — there is no automatic spoken-language detection; selecting the wrong language will produce garbled or nonsensical transcriptions regardless of which STT engine handles it
- **The web UI (`api_server.py` + `itantra-ui/`) already shares v2's dual-STT pipeline** with the CLI tools (both import `sender_pipeline.py`), so Whisper/IndicConformer branching works there automatically. What it does **not** yet do is use the real UDP transport — it still simulates transmission and packet loss in-process via `packet_reliability.py`, never sending anything over an actual network
- IndicConformer's GPU acceleration depends on a **system-wide NVIDIA CUDA Toolkit 13.x + cuDNN 9.x install**, separate from anything `pip install` handles. Without it, `onnxruntime-gpu` silently falls back to CPU — correct results, just slower. This is a real, sometimes-fiddly install (multiple GB, occasionally needs a restart); see `PART1_SETUP_GUIDE.md`
- Having both plain `onnxruntime` and `onnxruntime-gpu` installed in the same environment causes import conflicts (`AttributeError: module 'onnxruntime' has no attribute 'InferenceSession'`) — only one should be installed at a time, and if both got installed accidentally, uninstall both and reinstall only `onnxruntime-gpu` fresh
- **Two separate Hugging Face gated models** now need access requests (Indic Parler-TTS for TTS, IndicConformer for STT) — a fresh machine/account needs both approved before the full pipeline will run
- Everything runs on a **Windows laptop**, not an Android device — this validates the pipeline logic but not the size/latency/CPU constraints the PS actually evaluates
- Even the real UDP transport currently runs over a **WiFi router**, not an infrastructure-free link — it proves two-device transmission and real packet loss recovery work, but not yet the PS's "no infrastructure" scenario (Bluetooth/Wi-Fi Direct/radio). College/enterprise WiFi networks sometimes enable client isolation, which blocks this kind of direct device-to-device traffic entirely — test on the actual demo network in advance
- Models used are **not yet quantized or mobile-optimized** and are far heavier than what a low/mid-range phone can comfortably run
- Microphone device indices are **hardware-specific** — `MIC_INDEX` in `sender_pipeline.py` must be updated per machine
- Comparative accuracy claims between Whisper and IndicConformer in this README are based on **manual, sentence-level review of real test recordings**, not a formal WER benchmark against a labeled dataset — the direction of the result (IndicConformer meaningfully better on Indian languages) is well-supported, but exact accuracy percentages are not yet formally measured

---

## 🤝 Contributing

This is an active SIH team project. If you're a teammate:

1. New machine? Start with `CHECKING_ONE_LAPTOP_MODEL.md` — it now includes the CUDA/cuDNN install and both Hugging Face gated-model access steps. Already set up? Use `PART1_SETUP_GUIDE.md` as reference.
2. Hardcode your own mic's `MIC_INDEX` — don't assume a teammate's index matches yours.
3. You'll need your own Hugging Face account with access approved for **both** gated models (Indic Parler-TTS and IndicConformer).
4. Keep new dependencies open-source only (per PS constraints) — no proprietary/cloud STT or TTS SDKs.
5. When adding a new language: add it to `INDIC_LANGUAGES` in `sender_pipeline.py` if it should route through IndicConformer, and add a matching entry to `receiver_pipeline.py`'s `VOICE_DESCRIPTIONS` dict, so STT and TTS stay in sync.
6. If you're touching `sender_pipeline.py` in Notepad, be careful with indentation — Notepad has repeatedly mangled indentation on paste during this project's development. Prefer VS Code or another code-aware editor if available, and when in doubt, replace the entire function rather than patching a few lines.

---

## 🆕 What Changed in v2

v1 used `openai/whisper-small` for speech-to-text across all four supported languages. In testing, Whisper's Tamil/Hindi/Telugu output was unreliable in two distinct ways, even after upgrading to `whisper-large-v3-turbo`:

- **Hallucinated loops** — the model would get stuck repeating a short phrase over and over instead of transcribing what was actually said (a known Whisper failure mode, not specific to this project)
- **Non-words** — on clean, correctly-captured audio, Whisper would output syllables that aren't real Tamil/Hindi/Telugu words at all

A controlled test was run to isolate the cause: the same clean audio file (background noise eliminated, microphone gain corrected, VAD-trimmed) was fed to both Whisper and AI4Bharat's **IndicConformer** (`ai4bharat/indic-conformer-600m-multilingual`) back to back.

**Result:**

| Model | Output on a real Tamil test sentence |
|---|---|
| Whisper (`large-v3-turbo`) | `"நான்தக்கைத்துளிப்பருகிறால் வைக்கபாகிறால் காதில்கிறால்"` — not real words |
| IndicConformer (RNNT decoder) | `"வாய்ப்புகள் இருக்கிற கஷ்டத்தை பாக்குறவங்க தோத்துறாங்க அந்த கஷ்டத்திலயும் இருக்கிற வாய்ப்பை பாக்குறவங்க சிரிக்கிறாங்க"` — a coherent, ~95% word-accurate match to what was actually said |

This was repeated across multiple fresh Tamil, Hindi, and Telugu recordings with consistent results: IndicConformer produced real, grammatical, largely-correct transcriptions every time; Whisper did not, regardless of audio quality.

**v2's fix:** `sender_pipeline.py` now branches on the selected language. English still goes through Whisper (`large-v3-turbo`), unchanged. Tamil, Hindi, and Telugu are routed through IndicConformer's RNNT decoder instead. Nothing on the receiver side changed — the transport layer only ever carries plain text, so it has no idea (and doesn't need to know) which model produced it.

Two smaller fixes landed alongside this:
- **VAD sensitivity was tuned** (`threshold=0.35`, `min_speech_duration_ms=100`, down from Silero's defaults) after diagnosing that quiet speech and short clauses were sometimes being trimmed out entirely before reaching either STT model. `sender_pipeline.py` now prints every detected speech segment with timestamps, so this class of problem is visible immediately instead of only showing up as a bad transcription.
- **Language selection is now a runtime prompt** in `network_sender.py` instead of a hardcoded value you had to edit and save before every run.
- **Real two-laptop WiFi transport was tested and confirmed working** (see [Project Status](#-project-status)) — genuine UDP packets, sent and received across two separate physical machines, with real packet-loss recovery. This was already built in v1 but hadn't been documented as tested; v2's `CHECKING_TWO_LAPTOP_MODEL.md` walks through it step by step.

---

## 📄 License

License not yet specified for this repository — add a `LICENSE` file before public release.
