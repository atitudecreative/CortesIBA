"""Passo 2: transcrição local com faster-whisper, com tempo por palavra."""
import json
from pathlib import Path

from ..config import GLOSSARIO, WHISPER_DEVICE, WHISPER_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")
    return _model


def transcrever(audio: Path, destino: Path) -> dict:
    segments, info = _get_model().transcribe(
        str(audio),
        language="pt",
        initial_prompt=GLOSSARIO,
        word_timestamps=True,
        vad_filter=True,
    )
    out = {"duracao": info.duration, "segmentos": []}
    for i, s in enumerate(segments):
        out["segmentos"].append({
            "id": i,
            "inicio": round(s.start, 2),
            "fim": round(s.end, 2),
            "texto": s.text.strip(),
            "palavras": [
                {"inicio": round(w.start, 2), "fim": round(w.end, 2), "palavra": w.word.strip()}
                for w in (s.words or [])
            ],
        })
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    tmp.replace(destino)
    return out
