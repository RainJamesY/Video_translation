# code/main.py
from pathlib import Path
import argparse

from config import settings
from subtitle_parser import load_subtitles
from code.utils.video_utils import extract_audio, mux_video_audio
from audio_utils import (
    extract_speaker_sample,
    synthesize_and_align_segments,
)
from translation_api import TranslatorAPI
from tts_api import TTSAPI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate an English video to German using APIs."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to input video file (e.g. data/input/sample.mp4)",
    )
    parser.add_argument(
        "--subs",
        required=True,
        help="Path to input subtitle file in SRT format (e.g. data/input/sample.srt)",
    )
    parser.add_argument(
        "--out_dir",
        default="data/output",
        help="Directory to store intermediate and final outputs.",
    )
    parser.add_argument(
        "--target_lang",
        default="de",
        help="Target language code for translation / TTS (default: de).",
    )
    parser.add_argument(
        "--speaker_seconds",
        type=float,
        default=settings.speaker_sample_seconds,
        help="Duration in seconds for the speaker reference sample.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    video_path = Path(args.video)
    subs_path = Path(args.subs)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) extract original audio
    audio_en_path = out_dir / f"{video_path.stem}_en.wav"
    extract_audio(
        video_path,
        audio_en_path,
        sample_rate=settings.sample_rate,
    )

    # 2) load subtitles
    segments = load_subtitles(subs_path)

    # 3) translate EN -> target_lang
    translator = TranslatorAPI(
        api_key=settings.translate_api_key,
        base_url=settings.translate_base_url,
        model_name=settings.translate_model,
    )

    for seg in segments:
        seg["text_target"] = translator.translate(
            seg["text_en"], src="en", tgt=args.target_lang
        )

    # 4) extract speaker reference from original audio
    speaker_ref_path = out_dir / f"{video_path.stem}_speaker_ref.wav"
    extract_speaker_sample(
        audio_en_path,
        speaker_ref_path,
        sample_duration=args.speaker_seconds,
    )

    # 5) initialize TTS client (voice cloning)
    tts_client = TTSAPI(
        api_key=settings.tts_api_key,
        base_url=settings.tts_base_url,
        # 如果有现成 voice_id 就用，没有则在 TTSAPI 内部用 speaker_ref 创建
        voice_id=settings.tts_voice_id,
        speaker_ref_path=speaker_ref_path,
        sample_rate=settings.sample_rate,
    )

    # 6) synthesize + align + concatenate all segments into one track
    audio_target_path = out_dir / f"{video_path.stem}_{args.target_lang}.wav"
    synthesize_and_align_segments(
        segments=segments,
        tts_client=tts_client,
        output_path=audio_target_path,
        sample_rate=settings.sample_rate,
    )

    # 7) mux new audio back into video
    final_video_path = out_dir / f"{video_path.stem}_{args.target_lang}.mp4"
    mux_video_audio(
        video_path=video_path,
        audio_path=audio_target_path,
        output_path=final_video_path,
    )

    print(f"[Done] Output video written to: {final_video_path}")


if __name__ == "__main__":
    main()
