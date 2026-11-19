"""Transcrit une vidéo avec horodatage mot par mot (faster-whisper).

Usage : python transcribe.py video.mp4 sortie.json [modele]
"""
import json
import subprocess
import sys

import numpy as np

from faster_whisper import WhisperModel


def main():
    src, out = sys.argv[1], sys.argv[2]
    model_name = sys.argv[3] if len(sys.argv) > 3 else "medium"
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    segments, info = model.transcribe(
        audio, language="fr", word_timestamps=True, vad_filter=True, beam_size=5
    )
    data = {"language": info.language, "duration": info.duration, "segments": []}
    for seg in segments:
        data["segments"].append(
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "words": [
                    {"start": w.start, "end": w.end, "word": w.word.strip()}
                    for w in seg.words
                ],
            }
        )
        print(f"[{seg.start:7.1f} -> {seg.end:7.1f}] {seg.text.strip()}", flush=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
