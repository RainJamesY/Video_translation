# code/run_align_concat_audio_v2.py

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import librosa
import soundfile as sf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Align per-segment German TTS audio to original subtitle timings "
            "and concatenate into a single WAV track (librosa-based, less distortion)."
        )
    )
    parser.add_argument(
        "--jsonl",
        required=True,
        help="Translations JSONL with timing info.",
    )
    parser.add_argument(
        "--segments_dir",
        required=True,
        help="Directory containing per-segment mp3 files (e.g. seg_0001.mp3).",
    )
    parser.add_argument(
        "--orig_audio",
        required=True,
        help="Original full audio file (for total duration & sample rate).",
    )
    parser.add_argument(
        "--out_wav",
        required=True,
        help="Path to save the final aligned German WAV file.",
    )
    parser.add_argument(
        "--sample_rate",
        type=int,
        default=None,
        help="Target sample rate for output. "
             "If not set, use the sample rate of the original audio.",
    )
    parser.add_argument(
        "--max_segments",
        type=int,
        default=None,
        help="Optional: only process first N segments (for debugging).",
    )
    parser.add_argument(
        "--max_rel_stretch",
        type=float,
        default=0.2,
        help="Ignore time-stretch if relative duration diff is <= this (e.g. 0.2=20%).",
    )
    parser.add_argument(
        "--max_abs_stretch",
        type=float,
        default=0.4,
        help="Ignore time-stretch if abs duration diff is <= this seconds.",
    )
    return parser.parse_args()


def load_translations_jsonl(path: Path) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            segments.append(obj)
    return segments


def get_slot_times(seg: Dict[str, Any]) -> Tuple[float, float]:
    """Get start_sec / end_sec from JSONL."""
    if "start_sec" in seg and "end_sec" in seg:
        return float(seg["start_sec"]), float(seg["end_sec"])
    if "start" in seg and "end" in seg:
        return float(seg["start"]), float(seg["end"])
    raise KeyError("Segment does not contain recognizable start/end time keys.")


def main() -> None:
    args = parse_args()

    jsonl_path = Path(args.jsonl)
    segments_dir = Path(args.segments_dir)
    orig_audio_path = Path(args.orig_audio)
    out_wav_path = Path(args.out_wav)

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")
    if not segments_dir.exists():
        raise FileNotFoundError(f"Segments directory not found: {segments_dir}")
    if not orig_audio_path.exists():
        raise FileNotFoundError(f"Original audio file not found: {orig_audio_path}")

    # 1) Load original audio to get duration & sample rate
    orig_audio, orig_sr = librosa.load(orig_audio_path, sr=None, mono=True)
    print(f"[INFO] Original audio duration: {len(orig_audio) / orig_sr:.3f} s, sr={orig_sr}")

    # Output sample rate: if not specified by user, keep the same as original audio
    if args.sample_rate is None:
        sr = orig_sr
    else:
        sr = args.sample_rate
        if sr != orig_sr:
            print(f"[INFO] Resampling original audio from {orig_sr} -> {sr} for total length only.")
            # Only used to calculate total duration, no need to actually resample the original track
    total_samples = int(round(len(orig_audio) * (sr / orig_sr)))
    print(f"[INFO] Target output sample rate: {sr}, total samples: {total_samples}")

    # 2) Read subtitles/translations
    all_segments = load_translations_jsonl(jsonl_path)
    print(f"[INFO] Loaded {len(all_segments)} segments from JSONL.")

    if args.max_segments is not None:
        all_segments = all_segments[: args.max_segments]
        print(f"[INFO] Truncated to first {len(all_segments)} segments for this run.")

    # Add time helper fields & sort
    processed: List[Dict[str, Any]] = []
    for seg in all_segments:
        start_sec, end_sec = get_slot_times(seg)
        seg["_start_sec"] = start_sec
        seg["_end_sec"] = end_sec
        seg["_duration_sec"] = max(0.0, end_sec - start_sec)
        processed.append(seg)
    processed.sort(key=lambda x: x["_start_sec"])

    # 3) Allocate an empty track
    track = np.zeros(total_samples, dtype=np.float32)

    for i, seg in enumerate(processed, start=1):
        idx = seg.get("index", i)
        start_sec = seg["_start_sec"]
        end_sec = seg["_end_sec"]
        slot_duration = seg["_duration_sec"]

        start_sample = int(round(start_sec * sr))
        end_sample = int(round(end_sec * sr))
        if end_sample <= start_sample:
            continue
        slot_len = end_sample - start_sample

        seg_path = segments_dir / f"seg_{idx:04d}.mp3"
        if not seg_path.exists():
            print(f"[WARN] Missing TTS file for idx={idx}: {seg_path} -> slot filled with silence.")
            continue

        print(
            f"[SEG ] ({i}/{len(processed)}) idx={idx}, "
            f"slot=[{start_sec:.3f}, {end_sec:.3f}] dur={slot_duration:.3f}s"
        )

        # 3.1 Read mp3 as float32, directly using librosa, set sr=output sample rate
        audio, seg_sr = librosa.load(seg_path, sr=sr, mono=True)

        cur_len = len(audio)
        cur_dur = cur_len / sr
        if cur_len == 0:
            continue

        # 3.2 Decide whether to do time-stretch
        diff_sec = slot_duration - cur_dur
        rel_diff = abs(diff_sec) / max(slot_duration, 1e-6)

        # Default strategy: small differences only do padding/truncation; large differences do time-stretch
        need_stretch = (
            rel_diff > args.max_rel_stretch
            and abs(diff_sec) > args.max_abs_stretch
        )

        if not need_stretch:
            # No stretching, directly crop/pad to slot_len
            if cur_len >= slot_len:
                aligned = audio[:slot_len]
            else:
                pad = slot_len - cur_len
                aligned = np.pad(audio, (0, pad), mode="constant")
        else:
            # Need time-stretch, try to match slot duration
            # librosa rate = original duration / target duration
            rate = cur_dur / slot_duration
            # Limit the range to avoid excessive distortion
            rate = float(np.clip(rate, 0.7, 1.3))
            print(f"      -> time-stretch with rate={rate:.3f}")
            stretched = librosa.effects.time_stretch(audio, rate=rate)

            # Then crop/pad to exact slot_len
            if len(stretched) >= slot_len:
                aligned = stretched[:slot_len]
            else:
                pad = slot_len - len(stretched)
                aligned = np.pad(stretched, (0, pad), mode="constant")

        # 3.3 Fill into the corresponding position in the track
        end_pos = min(start_sample + slot_len, total_samples)
        aligned = aligned[: end_pos - start_sample]
        track[start_sample:end_pos] = aligned

    # 4) If there's a length discrepancy at the end (due to floating point errors), simply truncate/pad with zeros
    if len(track) > total_samples:
        track = track[:total_samples]
    elif len(track) < total_samples:
        pad = total_samples - len(track)
        track = np.pad(track, (0, pad), mode="constant")

    print(f"[INFO] Final aligned track duration: {len(track) / sr:.3f} s")

    # 5) Write WAV
    out_wav_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_wav_path, track, sr)
    print(f"[DONE] Saved aligned German audio to: {out_wav_path}")


if __name__ == "__main__":
    main()


'''
python -m code.audio_align.run_align_concat_audio \
  --jsonl data/output/caption_de/Tanzania-caption_translations_de.jsonl \
  --segments_dir data/output/audio/de_segments \
  --orig_audio data/output/audio/speaker_ref/Tanzania-2_en.wav \
  --out_wav data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav \
  --sample_rate 16000 
'''