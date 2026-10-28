"""Orquestra os passos e atualiza o status. Cada passo pula se a saída já existe,
então um culto que falhou no render não repete download nem transcrição."""
import json
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import db
from .config import DATA_DIR
from .pipeline import download, render, select_clips, transcribe

log = logging.getLogger("cortes.worker")
_executor = ThreadPoolExecutor(max_workers=1)


def pasta_culto(culto_id: int) -> Path:
    p = DATA_DIR / "cultos" / str(culto_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def enfileirar(culto_id: int) -> None:
    _executor.submit(processar, culto_id)


def retomar_pendentes() -> None:
    for culto_id in db.cultos_inacabados():
        enfileirar(culto_id)


def processar(culto_id: int) -> None:
    culto = db.get_culto(culto_id)
    pasta = pasta_culto(culto_id)
    try:
        db.set_status(culto_id, "baixando")
        audio = pasta / "audio.wav"
        try:
            source = download.encontrar_source(pasta)
        except FileNotFoundError:
            if culto["source"] != "youtube":
                raise
            source, titulo = download.baixar_youtube(culto["url"], pasta)
            if titulo:
                db.set_titulo(culto_id, titulo)
        if not audio.exists():
            download.extrair_audio(source, audio)

        db.set_status(culto_id, "transcrevendo")
        transcript_path = pasta / "transcript.json"
        if transcript_path.exists():
            transcricao = json.loads(transcript_path.read_text(encoding="utf-8"))
        else:
            transcricao = transcribe.transcrever(audio, transcript_path)
        if not transcricao["segmentos"]:
            raise RuntimeError("A transcrição veio vazia. O vídeo tem áudio de fala?")

        db.set_status(culto_id, "selecionando")
        clips = db.listar_clips(culto_id)
        if not clips:
            db.salvar_clips(culto_id, select_clips.selecionar(transcricao))
            clips = db.listar_clips(culto_id)
        if not clips:
            raise RuntimeError("Nenhum trecho válido foi selecionado.")

        db.set_status(culto_id, "renderizando")
        for clip in clips:
            if clip["arquivo"] and (pasta / clip["arquivo"]).exists():
                continue
            arquivo = render.renderizar(source, transcricao, dict(clip), pasta)
            db.set_clip_arquivo(clip["id"], arquivo.name)

        db.set_status(culto_id, "pronto")
    except Exception as exc:  # noqa: BLE001 — qualquer falha vira status visível
        log.error("culto %s falhou:\n%s", culto_id, traceback.format_exc())
        db.set_status(culto_id, "erro", f"{type(exc).__name__}: {exc}")
