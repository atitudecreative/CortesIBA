"""Passo 4: ffmpeg recorta, enquadra em 9:16 e queima a legenda (destaque por palavra)."""
import subprocess
from pathlib import Path

W, H = 1080, 1920
PALAVRAS_POR_BLOCO = 3
PAD_FIM = 0.25  # respiro depois da última palavra

ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,80,80,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
DESTAQUE = r"{\c&H00D7FF&}"  # amarelo (ASS usa BGR)
NORMAL = r"{\c&HFFFFFF&}"


def _ts(s: float) -> str:
    s = max(s, 0)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def _limpar(txt: str) -> str:
    return txt.replace("\\", "").replace("{", "(").replace("}", ")").upper()


def palavras_no_intervalo(transcricao: dict, inicio: float, fim: float) -> list[dict]:
    return [
        w for s in transcricao["segmentos"] if s["fim"] >= inicio and s["inicio"] <= fim
        for w in s["palavras"] if w["inicio"] >= inicio - 0.05 and w["fim"] <= fim + 0.05
    ]


def blocos(palavras: list[dict]) -> list[list[dict]]:
    """Agrupa palavras em blocos curtos, quebrando também na pontuação."""
    out, atual = [], []
    for w in palavras:
        atual.append(w)
        if len(atual) == PALAVRAS_POR_BLOCO or w["palavra"][-1:] in ".,!?;:":
            out.append(atual)
            atual = []
    if atual:
        out.append(atual)
    return out


def gerar_ass(palavras: list[dict], inicio: float, fim: float) -> str:
    linhas = [ASS_HEADER]
    for bloco in blocos(palavras):
        for i, w in enumerate(bloco):
            ini = w["inicio"] - inicio
            fim_w = (bloco[i + 1]["inicio"] if i + 1 < len(bloco) else w["fim"]) - inicio
            texto = " ".join(
                (DESTAQUE if j == i else NORMAL) + _limpar(x["palavra"]) for j, x in enumerate(bloco)
            )
            linhas.append(f"Dialogue: 0,{_ts(ini)},{_ts(min(fim_w, fim - inicio))},Default,,0,0,0,,{texto}\n")
    return "".join(linhas)


def renderizar(source: Path, transcricao: dict, clip: dict, pasta: Path) -> Path:
    nome = f"clip_{clip['idx']:02d}"
    inicio, fim = clip["inicio"], clip["fim"] + PAD_FIM
    ass = pasta / f"{nome}.ass"
    ass.write_text(gerar_ass(palavras_no_intervalo(transcricao, inicio, fim), inicio, fim), encoding="utf-8")

    destino = pasta / f"{nome}.mp4"
    tmp = pasta / f"{nome}.tmp.mp4"
    # Crop central em 9:16 (MVP). O filtro ass recebe nome relativo, por isso cwd=pasta.
    vf = f"crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale={W}:{H},setsar=1,ass={ass.name}"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-ss", f"{inicio:.2f}", "-t", f"{fim - inicio:.2f}", "-i", str(source.resolve()),
         "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", tmp.name],
        check=True, cwd=pasta,
    )
    tmp.replace(destino)
    return destino
