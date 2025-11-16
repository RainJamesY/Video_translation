# code/audio_utils.py

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import soundfile as sf


def extract_speaker_segments_from_audio(
    audio_path: Path,
    segments: List[Dict[str, Any]],
    out_dir: Path,
    num_segments: int = 3,
    min_duration: float = 1.0,
) -> Tuple[List[Path], Path]:
    """
    Extract speaker reference segments from audio based on subtitle timestamps and combine them.

    Args:
        audio_path: Path to the full audio file (e.g. audio_en.wav extracted from video)
        segments: List of subtitle segments from subtitle_parser.load_subtitles
        out_dir: Output directory to store extracted segments and final speaker_ref.wav
        num_segments: Number of subtitle segments to use (>=2 recommended), default 3
        min_duration: Minimum duration for each segment in seconds, default 1.0s

    Returns:
        (segment_paths, speaker_ref_path)
        - segment_paths: List of paths to individual segment WAV files
        - speaker_ref_path: Path to the combined speaker reference audio
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Read the full audio file
    audio, sr = sf.read(str(audio_path))
    # Convert to mono if needed
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    # 2. Select segments to use as reference
    chosen: List[Dict[str, Any]] = []
    for seg in segments:
        text = seg.get("text_en", "") or seg.get("text", "") or ""
        if not text.strip():
            continue

        start = seg["start"]
        end = seg["end"]
        dur = (end - start).total_seconds()
        if dur < min_duration:
            continue

        chosen.append(seg)
        if len(chosen) >= num_segments:
            break

    if not chosen:
        raise RuntimeError(
            f"No subtitle segments found with duration >= {min_duration} seconds."
        )

    # 3. Extract audio clips based on timestamps
    segment_paths: List[Path] = []
    pieces: List[np.ndarray] = []

    for idx, seg in enumerate(chosen, start=1):
        start_sec = seg["start"].total_seconds()
        end_sec = seg["end"].total_seconds()

        start_idx = int(start_sec * sr)
        end_idx = int(end_sec * sr)
        # Prevent out-of-bounds indices
        start_idx = max(0, min(start_idx, len(audio)))
        end_idx = max(0, min(end_idx, len(audio)))

        clip = audio[start_idx:end_idx]
        if clip.size == 0:
            continue

        seg_path = out_dir / f"speaker_seg_{idx:02d}.wav"
        sf.write(str(seg_path), clip, sr)
        segment_paths.append(seg_path)
        pieces.append(clip)

    if not pieces:
        raise RuntimeError("Failed to extract any non-empty audio segments.")

    # 4. Concatenate segments into a single speaker reference file
    combined = np.concatenate(pieces)
    speaker_ref_path = out_dir / "speaker_ref.wav"
    sf.write(str(speaker_ref_path), combined, sr)

    return segment_paths, speaker_ref_path

def extract_speaker_sample(
    audio_path: Path,
    out_path: Path,
    sample_duration: float,
):
    """
    Extract a sample of specified duration from an audio file.
    
    Args:
        audio_path: Path to the input audio file
        out_path: Path to save the extracted sample
        sample_duration: Duration of the sample to extract in seconds
        
    Returns:
        Path to the saved sample file
    """
    audio, sr = sf.read(audio_path)
    total_dur = len(audio) / sr
    dur = min(sample_duration, total_dur)
    sample = audio[: int(dur * sr)]
    sf.write(out_path, sample, sr)
    return out_path


def synthesize_and_align_segments(
    segments,
    tts_client,
    output_path: Path,
    sample_rate: int,
    tol_seconds: float = 0.15,
):
    """
    Core logic: Synthesize each segment with TTS, align duration, and concatenate.
    
    Args:
        segments: List of subtitle segments with text and timing information
        tts_client: TTS client object with synthesize_to_array method
        output_path: Path to save the final audio file
        sample_rate: Sample rate for the output audio
        tol_seconds: Tolerance in seconds for duration alignment
        
    Returns:
        Path to the saved output file
    """
    all_audio = []

    for seg in segments:
        slot = (seg["end"] - seg["start"]).total_seconds()
        # 1) TTS synthesis
        audio = tts_client.synthesize_to_array(seg["text_target"], sample_rate)

        duration = len(audio) / sample_rate
        # 2) Align duration
        if duration > slot + tol_seconds:
            rate = duration / slot
            audio = librosa.effects.time_stretch(audio, rate)
        elif duration < slot - tol_seconds:
            pad_len = int((slot - duration) * sample_rate)
            pad = np.zeros(pad_len, dtype=audio.dtype)
            audio = np.concatenate([audio, pad])

        all_audio.append(audio)

    full = np.concatenate(all_audio)
    sf.write(output_path, full, sample_rate)
    return output_path
