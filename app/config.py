"""Configuração lida do ambiente, com padrões para rodar localmente."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("CORTES_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.getenv("CORTES_DB", DATA_DIR / "cortes.db"))

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # small ou medium para pt-BR
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # "cuda" se houver GPU

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
N_CLIPS = int(os.getenv("N_CLIPS", "10"))
CLIP_MIN_S = 20
CLIP_MAX_S = 90

UPLOAD_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}

# Termos que o Whisper costuma errar; entra como initial_prompt.
GLOSSARIO = (
    "Culto evangélico em português. Gênesis, Êxodo, Levítico, Deuteronômio, "
    "Josué, Eclesiastes, Isaías, Jeremias, Ezequiel, Habacuque, Sofonias, "
    "Mateus, Lucas, Romanos, Coríntios, Gálatas, Efésios, Filipenses, "
    "Colossenses, Tessalonicenses, Hebreus, Apocalipse, Melquisedeque, "
    "Nabucodonosor, Getsêmani, Gólgota, Pentecostes, aleluia, amém, hosana."
)
