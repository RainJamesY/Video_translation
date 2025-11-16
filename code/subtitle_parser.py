# code/subtitle_parser.py
import srt

def load_subtitles(path):
    with open(path, "r", encoding="utf-8") as f:
        subs = list(srt.parse(f.read()))
    segments = []
    for s in subs:
        segments.append(
            {
                "index": s.index,
                "start": s.start,
                "end": s.end,
                "text_en": s.content.strip(),
            }
        )
    return segments
