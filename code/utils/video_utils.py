# code/video_utils.py
import subprocess
from pathlib import Path

def extract_audio(video_path: Path, audio_path: Path, sample_rate: int = 16000):
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-y",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True)

def mux_video_audio(video_path: Path, audio_path: Path, output_path: Path):
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-shortest",
        "-y",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
