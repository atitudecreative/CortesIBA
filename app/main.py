"""Rotas: formulário, criação do culto, página de status e download dos cortes."""
import logging
import re
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import db, worker
from .pipeline.download import validar_url_youtube
from .config import UPLOAD_EXTS

logging.basicConfig(level=logging.INFO)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    worker.retomar_pendentes()
    yield


app = FastAPI(title="Cortes de culto", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"cultos": db.listar_cultos(), "erro": None})


@app.post("/cultos")
def criar_culto(
    request: Request,
    url: str = Form(""),
    arquivo: UploadFile | None = File(None),
    autorizado: bool = Form(False),
):
    def erro(msg: str):
        ctx = {"cultos": db.listar_cultos(), "erro": msg}
        return templates.TemplateResponse(request, "index.html", ctx, status_code=400)

    if not autorizado:
        return erro("Confirme que a igreja tem autorização para usar este vídeo.")

    if arquivo is not None and arquivo.filename:
        ext = Path(arquivo.filename).suffix.lower()
        if ext not in UPLOAD_EXTS:
            return erro(f"Formato não aceito. Use: {', '.join(sorted(UPLOAD_EXTS))}.")
        culto_id = db.criar_culto("upload")
        db.set_titulo(culto_id, Path(arquivo.filename).stem[:200])
        with open(worker.pasta_culto(culto_id) / f"source{ext}", "wb") as f:
            shutil.copyfileobj(arquivo.file, f)
    elif url.strip():
        try:
            url = validar_url_youtube(url)
        except ValueError as e:
            return erro(str(e))
        culto_id = db.criar_culto("youtube", url)
    else:
        return erro("Cole um link do YouTube ou envie o arquivo do culto.")

    worker.enfileirar(culto_id)
    return RedirectResponse(f"/cultos/{culto_id}", status_code=303)


def _culto_ou_404(culto_id: int):
    culto = db.get_culto(culto_id)
    if culto is None:
        raise HTTPException(404, "Culto não encontrado")
    return culto


@app.get("/cultos/{culto_id}", response_class=HTMLResponse)
def ver_culto(request: Request, culto_id: int):
    culto = _culto_ou_404(culto_id)
    ctx = {"culto": culto, "clips": db.listar_clips(culto_id), "etapas": db.STATUS}
    return templates.TemplateResponse(request, "culto.html", ctx)


@app.get("/cultos/{culto_id}/status")
def status(culto_id: int):
    culto = _culto_ou_404(culto_id)
    return {"status": culto["status"], "erro": culto["erro"]}


@app.post("/cultos/{culto_id}/reprocessar")
def reprocessar(culto_id: int):
    culto = _culto_ou_404(culto_id)
    if culto["status"] == "erro":
        db.set_status(culto_id, "pendente")
        worker.enfileirar(culto_id)
    return RedirectResponse(f"/cultos/{culto_id}", status_code=303)


@app.get("/cultos/{culto_id}/clips/{nome}")
def baixar_clip(culto_id: int, nome: str):
    # Só serve os cortes renderizados, nunca o vídeo de origem.
    if not re.fullmatch(r"clip_\d{2}\.mp4", nome):
        raise HTTPException(404)
    _culto_ou_404(culto_id)
    caminho = worker.pasta_culto(culto_id) / nome
    if not caminho.exists():
        raise HTTPException(404)
    return FileResponse(caminho, media_type="video/mp4", filename=f"culto{culto_id}_{nome}")
