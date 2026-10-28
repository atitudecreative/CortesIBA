"""Passo 1: obter o vídeo (YouTube ou upload) e extrair o áudio para transcrição."""
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def validar_url_youtube(url: str) -> str:
    """Aceita só links de vídeo do YouTube. Devolve a URL normalizada ou levanta ValueError."""
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https") or (p.hostname or "").lower() not in YOUTUBE_HOSTS:
        raise ValueError("Use um link do YouTube (youtube.com ou youtu.be).")
    host = p.hostname.lower()
    if host == "youtu.be":
        video_id = p.path.lstrip("/").split("/")[0]
    elif p.path == "/watch":
        video_id = parse_qs(p.query).get("v", [""])[0]
    elif p.path.startswith(("/live/", "/shorts/")):
        video_id = p.path.split("/")[2]
    else:
        video_id = ""
    if not (len(video_id) == 11 and all(ch.isalnum() or ch in "-_" for ch in video_id)):
        raise ValueError("Não encontrei o ID do vídeo no link.")
    return f"https://www.youtube.com/watch?v={video_id}"


def baixar_youtube(url: str, pasta: Path) -> tuple[Path, str]:
    """Baixa até 1080p em mp4. Usa a API do yt-dlp, sem shell."""
    import yt_dlp

    opts = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(pasta / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return encontrar_source(pasta), info.get("title") or ""


def encontrar_source(pasta: Path) -> Path:
    arquivos = sorted(p for p in pasta.glob("source.*") if p.suffix != ".part")
    if not arquivos:
        raise FileNotFoundError("Vídeo de origem não encontrado.")
    return arquivos[0]


def extrair_audio(source: Path, destino: Path) -> Path:
    """Áudio mono 16 kHz: é o que o Whisper usa e reduz muito o tamanho."""
    tmp = destino.with_suffix(".tmp.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
         "-vn", "-ac", "1", "-ar", "16000", str(tmp)],
        check=True,
    )
    tmp.replace(destino)
    return destino
