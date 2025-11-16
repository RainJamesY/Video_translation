# Video Translation: English → German

This repository implements an end-to-end **video translation pipeline**:

> **English video + subtitles → German audio + translated video (+ optional lip-sync)**

The focus is on:

* Keeping the pipeline **modular & inspectable** (each step can be run & debugged separately).
* Documenting **design decisions, assumptions, and limitations** clearly.
* Providing both a **practical API-based MVP** and thoughts on a **fully open-source alternative**.



**Overview of Results:**

Original Video (**En**):

<video width="640" height="360" controls>
  <source src="data/examples/Tanzania_subtitled.mp4" type="video/mp4">
</video>

After translation (**DE**):

<video width="640" height="360" controls>
  <source src="data/examples/Tanzania_de_lipsynced_trim_subtitled.mp4" type="video/mp4">
</video>



---

## 1. Repository Structure

```bash
.
├── code
│   ├── audio_align/          # Audio alignment + concat + audio↔video utilities
│   ├── lip_sync/             # Optional lip-sync integration (Sync / Wav2Lip API)
│   ├── translation/          # Subtitle translation using Gemini API
│   ├── tts/                  # TTS segment generation using ElevenLabs API
│   ├── utils/                # Small utilities (e.g., trimming audio/video)
│   ├── voice_clone/          # (Optional) voice cloning utilities for ElevenLabs
│   ├── list_voices.py        # Helper script to list available ElevenLabs voices
│   ├── main.py               # (Optional) high-level entry point (not required)
│   └── subtitle_parser.py    # SRT parsing helpers
├── data
│   ├── input/                # Input video + original English subtitles
│   ├── output/               # All intermediate & final outputs
│   └── elevenLabs/           # (Optional) local artifacts related to ElevenLabs
├── Tanzania-caption.txt      # Original caption file (provided by HeyGen)
├── Test task - Translate to German.docx  # Original assignment spec
├── .env                      # API keys (NOT committed)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 2. Requirements & Setup

### 2.1 Environment

* Python 3.10+
* `ffmpeg` / `ffprobe` installed and on `PATH`

  * macOS example: `brew install ffmpeg`
* A virtual env is recommended:

```bash
conda create -n heygen python=3.10
conda activate heygen
pip install -r requirements.txt
```

Key Python deps (see `requirements.txt`):

* `google-genai` (Gemini API)
* `python-dotenv`
* `srt`
* `pydub`, `librosa`, `soundfile`, `numpy`
* `elevenlabs`
* `syncsdk` (for Wav2Lip commercial API via sync.so)
* `ffmpeg-python` (optional helper, core ops still use CLI `ffmpeg`)

### 2.2 API Keys (`.env`)

Create a `.env` file in the repo root (never commit your real keys):

```bash
# Google Gemini
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY

# ElevenLabs
ELEVENLABS_API_KEY=YOUR_ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID=YOUR_VOICE_ID   # e.g., Rachel or a cloned voice

# Optional: Sync (Wav2Lip commercial API)
SYNC_API_KEY=YOUR_SYNC_API_KEY
```

All scripts use `python-dotenv` to load these values automatically.

---

## 3. End-to-End Pipeline Overview

### High-level steps

1. **Translate subtitles** (English → German) using Gemini.
2. **(Optional) Voice cloning**: extract speaker reference audio and create a cloned voice on ElevenLabs.
3. **Generate German TTS** for each subtitle segment via ElevenLabs (using a chosen or cloned voice).
4. **Align & concatenate** all TTS segments into one continuous German audio track, aligned to original subtitle timings.
5. **Replace audio in the original video** with the aligned German track (optional bilingual version with both tracks).
6. **(Optional) Lip sync**: call Wav2Lip-like API (sync.so `lipsync-2`) to refine mouth movements to match the new German audio.

All steps are **offline and modular**: you can run them one by one and inspect intermediate outputs (JSONL, per-segment MP3s, aligned WAV, etc.).

---

## 4. Step-by-Step Usage

Example paths below are based on the current repo layout.
Assume:

* Input video: `data/input/Tanzania-2.mp4`
* Original subtitles (SRT): `data/input/Tanzania-caption.srt`

### 4.1 Subtitle Translation (Gemini API)

Translate the English SRT into German and save a JSONL file with aligned segments:

```bash
python -m code.translation.run_translation \
  --subs data/input/Tanzania-caption.srt \
  --out_dir data/output/caption_de
```

This produces:

```bash
data/output/caption_de/Tanzania-caption_translations_de.jsonl
```

Each line represents one subtitle segment:

```json
{
  "index": 1,
  "start_sec": 0.0,
  "end_sec": 4.436,
  "text_en": "Tanzania—home to some of the most breathtaking wildlife on Earth.",
  "text_de": "Tansania – die Heimat einiger der atemberaubendsten Wildtiere der Erde."
}
```

> The JSONL format makes it easy to **manually audit translations** and optionally post-edit them.

---

### 4.2 (Optional) Voice Cloning with ElevenLabs

**Goal:** approximate the original speaker’s identity by cloning their voice, then use that voice for German TTS.

#### 4.2.1 Extract speaker reference audio

Select a few clean segments from the original video using subtitle timestamps and save a single reference WAV:

```bash
python -m code.voice_clone.run_extract_speaker_ref \
  --video data/input/Tanzania-2.mp4 \
  --subs data/input/Tanzania-caption.srt \
  --out_dir data/output/audio/speaker_ref \
  --num_segments 3 \
  --min_duration 1.0
```

Outputs (example):

```bash
data/output/audio/speaker_ref/speaker_ref.wav
data/output/audio/speaker_ref/Tanzania-2_en.wav   # extracted full original audio (for later alignment)
```

#### 4.2.2 Call ElevenLabs to clone voice

> Requires an ElevenLabs plan that supports voice cloning. https://elevenlabs.io/docs/cookbooks/voices/instant-voice-cloning

```bash
python -m code.voice_clone.run_clone_voice \
  --ref data/output/audio/speaker_ref/speaker_ref.wav \
  --name "heygen_takehome_speaker"
```

This returns a `voice_id`. Put it into `.env`:

```bash
ELEVENLABS_VOICE_ID=YOUR_CLONED_VOICE_ID
```

If you **don’t have access to paid cloning**, you can skip this step and just use a built-in voice (e.g., Rachel); the rest of the pipeline is unchanged.

---

### 4.3 TTS for Each German Sentence (ElevenLabs)

Generate an audio file for each translated sentence:

```bash
python -m code.tts.run_tts_segments \
  --jsonl data/output/caption_de/Tanzania-caption_translations_de.jsonl \
  --out_dir data/output/audio/de_segments
```

This produces:

```bash
data/output/audio/de_segments/seg_0001.mp3
data/output/audio/de_segments/seg_0002.mp3
...
```

* Filenames are aligned with `index` in the JSONL (`seg_{index:04d}.mp3`).
* The script uses the `ELEVENLABS_VOICE_ID` from `.env` (cloned or preset).
  * See full list of ElevenLabs supports voices at https://elevenlabs.io/docs/api-reference/voices/search

---

### 4.4 Align & Concatenate Audio Segments

Now we align all German segments to the original subtitle timings and create a single continuous German track.

```bash
python -m code.audio_align.run_align_concat_audio \
  --jsonl data/output/caption_de/Tanzania-caption_translations_de.jsonl \
  --segments_dir data/output/audio/de_segments \
  --orig_audio data/output/audio/speaker_ref/Tanzania-2_en.wav \
  --out_wav data/output/audio/de_aligned/Tanzania_de_aligned.wav \
  --sample_rate 16000
```

What this script does:

* Uses `start_sec` / `end_sec` from JSONL to compute a slot for each sentence.
* Loads each `seg_xxxx.mp3` at `sample_rate` Hz.
* **Prefers minimal distortion**:
  * If the segment duration is close to the slot, it only trims/pads with silence.
  * Only when the mismatch is large does it use `librosa.effects.time_stretch` with a limited stretch factor (e.g., 0.7–1.3).
* Fills gaps between slots with silence.
* Ensures final track length ≈ original audio length.

Output:

```bash
data/output/audio/de_aligned/Tanzania_de_aligned.wav
```

---

### 4.5 Replace Audio in the Original Video

Replace the English audio with the aligned German track:

```bash
python -m code.audio_align.replace_audio_with_ffmpeg \
  --video data/input/Tanzania-2.mp4 \
  --audio data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav \
  --out data/output/video/Tanzania_de_final.mp4
```

* Video stream is copied (`-c:v copy`), so image quality is unchanged.
* Audio is encoded to AAC.

**Optional: keep original audio as a second track** (bilingual video):

```bash
python -m code.audio_align.replace_audio_with_ffmpeg \
  --video data/input/Tanzania-2.mp4 \
  --audio data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav \
  --out data/output/video/Tanzania_de_bilingual.mp4 \
  --keep-original-audio
```

In the bilingual video:

* Track 0: German aligned audio
* Track 1: Original English audio

Many players let you switch between tracks—useful for demos.

---

### 4.6 (Optional) Lip Sync with Wav2Lip-style API (Sync `lipsync-2`)

To further refine mouth movements, an optional step calls Sync’s `lipsync-2` model (a [Wav2Lip](https://github.com/Rudrabha/Wav2Lip)-style commercial API).

**Important constraints (free tier):**

* Input video & audio must be available via **public URLs** (e.g., GitHub raw links).
* Duration must be **< 60 seconds**.
* Free generations are watermarked.

#### 4.6.1 Ensure < 60 s (optional trimming)

For the free plan, I trim ~1 second from the end of both audio & video:

```bash
python -m code.utils.trim_last_seconds \
  --input  data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav \
  --output data/output/audio/de_aligned/Tanzania_de_aligned_trim.wav \
  --trim_sec 1.0

python -m code.utils.trim_last_seconds \
  --input  data/output/video/Tanzania_de_final.mp4 \
  --output data/output/video/Tanzania_de_final_trim.mp4 \
  --trim_sec 1.0
```

Upload these trimmed files to the GitHub repo and use their **raw URLs**, e.g.:

```text
https://raw.githubusercontent.com/RainJamesY/Video_translation/main/data/output/video/Tanzania_de_final_trim.mp4
https://raw.githubusercontent.com/RainJamesY/Video_translation/main/data/output/audio/de_aligned/Tanzania_de_aligned_trim.wav
```

#### 4.6.2 Call lipsync API

```bash
python -m code.lip_sync.run_lipsync_sync_api \
  --video_url "https://raw.githubusercontent.com/RainJamesY/Video_translation/main/data/output/video/Tanzania_de_final_trim.mp4" \
  --audio_url "https://raw.githubusercontent.com/RainJamesY/Video_translation/main/data/output/audio/de_aligned/Tanzania_de_aligned_trim.wav" \
  --output_name "Tanzania_de_lipsynced_trim" \
  --model "lipsync-2"
```

The script:

* Submits a generation job to Sync.
* Polls status until `COMPLETED` / `FAILED` / `REJECTED`.
* Prints the final `output_url` where the lipsynced video can be downloaded.

> For the assignment, I treat this as an **optional extension** to demonstrate how lip sync could integrate into the existing pipeline, rather than as a hard requirement.

---

## 5. Example Inputs & Outputs

### Example Input Files

* `data/input/Tanzania-2.mp4`
  Original video with English audio.
* `data/input/Tanzania-caption.srt`
  Original English subtitles (converted from the provided `.txt` caption).

### Example Intermediate Outputs

* `data/output/caption_de/Tanzania-caption_translations_de.jsonl`
  Sentence-level English & German pairs with timestamps.
* `data/output/audio/de_segments/seg_0001.mp3`
  Per-sentence German TTS segments.
* `data/output/audio/speaker_ref/speaker_ref.wav`
  Extracted speaker reference audio for cloning (optional).

### Final Output Files

* `data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav`
  Continuous German audio track aligned to subtitle timings.
* `data/output/video/Tanzania_de_final.mp4`
  Video with German audio replacing the original audio.
* `data/output/video/Tanzania_de_bilingual.mp4` (optional)
  Video with both German & English audio tracks.
* `Tanzania_de_lipsynced_trim` (downloaded from Sync output URL)
  Lipsynced video produced by `lipsync-2` (watermarked, <60s).

---

## 6. Assumptions & Limitations

### Assumptions

* **Single main speaker** whose voice we want to approximate.
* Original audio has relatively **clean speech** (the given test video has minimal background noise).
* The video is **short-form** (~60 seconds) and primarily **narration + visuals**, not multi-speaker dialogue.
* Subtitle timings are reasonably accurate; translation doesn’t change timing semantics drastically.

### Limitations

1. **Voice cloning**

   * High-quality cloning in ElevenLabs requires a paid plan; the repo includes code paths for cloning, but the default flow can use a non-custom voice.
   * If cloning is unavailable, the German voice will not match the original speaker’s identity.
2. **TTS & prosody**

   * Prosody is controlled by the TTS provider (ElevenLabs) and basic parameters only; the pipeline does not yet perform prosody transfer or fine-grained style control.
3. **Audio alignment**

   * Alignment is based on **subtitle time slots** rather than phoneme-level alignment.
   * Light time-stretching is used to match slot durations; very large differences may still sound slightly rushed or slow.
   * No explicit background-music separation—this is not needed for the provided test video, but would be required in music-heavy content.
4. **Lip sync (optional)**

   * Uses a **cloud API** (Sync `lipsync-2`), not a fully local model.
   * Free plan requires:

     * Public URLs for input video & audio.
     * Duration < 60s.
     * Output contains a watermark.
   * If the video lacks clear talking faces, lipsync quality may degrade or the job may be rejected.
5. **Scalability / batch processing**

   * Current scripts focus on processing **one video** end-to-end.
   * Offline processing:

     * There are some steps requiring more than Python integration, like registering API accounts, fetching API Keys and uploading video/audio to URLs.
     * We might consider using LLM/VLM agents to streamline the whole process.
   * For large batches, one would add:

     * A job queue for multiple videos.
     * More robust error handling & retry / rate-limit logic.
     * Persistent logging & metrics.

---

## 7. Design Choices & Alternatives

### Why APIs for the MVP?

* **Gemini for translation**:

  * High-quality EN → DE translation with minimal setup; avoids training or hosting a custom translation model.
* **ElevenLabs for TTS & (optional) voice cloning**:

  * Good voice quality, supports German, and has built-in cloning.
* **Sync `lipsync-2` for optional lip sync**:

  * Provides a Wav2Lip-like capability without GPU setup, ideal for a MacBook-only environment.

This keeps the local compute requirements very modest while still demonstrating a **production-style pipeline** that could be swapped to internal HeyGen models/APIs.

### Possible Fully Open-Source Stack (e.g. Single A6000 GPU)

If GPU resources were available and external APIs were not allowed, an alternative stack could be:

* **Translation**:

  * `Llama-3-8B-Instruct` (via vLLM) for EN → DE translation, possibly with prompt-based style control.
* **TTS + voice cloning**:

  * [Coqui-TTS](https://github.com/coqui-ai/TTS) – supports German TTS and voice cloning.
* **Lip sync**:

  * Open-source [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) or Wav2Lip-HD deployed locally.

The overall pipeline structure would remain identical; only the translation/TTS/lipsync components would be swapped.

---

## 8. How to Run a Minimal Demo

If you just want to verify that the core pipeline works (without cloning & lip sync):

1. Set `GOOGLE_API_KEY` and `ELEVENLABS_API_KEY` in `.env`.
2. Run **steps 4.1 → 4.5** only:

   * Translation → TTS segments → Audio alignment → Replace audio.
3. Inspect:

   * `data/output/caption_de/Tanzania-caption_translations_de.jsonl`
   * `data/output/audio/de_aligned/Tanzania_de_aligned.wav`
   * `data/output/video/Tanzania_de_final.mp4`

If everything is configured correctly, `Tanzania_de_final.mp4` should be a **natural-sounding German version** of the original video, with subtitles and visual cuts still aligned to the narration.
