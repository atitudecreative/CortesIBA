"""Passo 3: Claude lê a transcrição e escolhe os trechos.

Trava de fidelidade: o modelo escolhe um intervalo de segmentos contíguos
(primeiro e último ID), nunca frases soltas. Assim um corte não junta falas
de pontos diferentes da pregação. Como os limites são limites de segmento,
o corte também começa e termina em fronteira de frase.
"""
import anthropic
from pydantic import BaseModel, Field

from ..config import CLAUDE_MODEL, CLIP_MAX_S, CLIP_MIN_S, N_CLIPS

SYSTEM = """Você é editor de vídeo de uma igreja evangélica e escolhe cortes curtos \
(Reels, Shorts, TikTok) a partir da transcrição de um culto.

Regras:
- Cada corte é um intervalo contínuo de segmentos: informe o ID do primeiro e do último. \
Não junte trechos separados e não mude o sentido do que o pregador disse.
- Escolha momentos da pregação que se sustentem sozinhos: uma ideia completa, com começo e fim.
- Evite avisos, ofertas, louvor cantado e orações longas.
- Cortes não podem se sobrepor.
- titulo: curto, fiel ao trecho. gancho: frase de abertura para a tela inicial, sem exagero \
nem promessa que o trecho não cumpre.
- nota_gancho e nota_completude de 0 a 10; motivo em uma frase.
- depende_contexto = true se o trecho se apoia no que veio antes ("como eu disse", "esse texto")."""


class Corte(BaseModel):
    primeiro_segmento: int
    ultimo_segmento: int
    titulo: str
    gancho: str
    nota_gancho: float = Field(ge=0, le=10)
    nota_completude: float = Field(ge=0, le=10)
    motivo: str
    depende_contexto: bool


class Selecao(BaseModel):
    cortes: list[Corte]


def _mmss(s: float) -> str:
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def texto_compacto(transcricao: dict) -> str:
    """Uma linha por segmento: [id] mm:ss texto. Mantém o prompt pequeno em cultos longos."""
    return "\n".join(
        f"[{s['id']}] {_mmss(s['inicio'])} {s['texto']}" for s in transcricao["segmentos"]
    )


def selecionar(transcricao: dict, n: int = N_CLIPS, client: anthropic.Anthropic | None = None) -> list[dict]:
    client = client or anthropic.Anthropic()
    prompt = (
        f"Escolha até {n} cortes de {CLIP_MIN_S} a {CLIP_MAX_S} segundos.\n\n"
        f"<transcricao>\n{texto_compacto(transcricao)}\n</transcricao>"
    )
    resp = client.beta.messages.parse(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_format=Selecao,
        # Se o modelo recusar, a API refaz o pedido num modelo de fallback.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("O modelo recusou a seleção de cortes.")
    if resp.parsed_output is None:
        raise RuntimeError(f"Resposta sem cortes (stop_reason={resp.stop_reason}).")
    return validar(resp.parsed_output.cortes, transcricao, n)


def validar(cortes: list[Corte], transcricao: dict, n: int) -> list[dict]:
    """Converte IDs em segundos e descarta cortes inválidos, curtos/longos demais ou sobrepostos."""
    segs = transcricao["segmentos"]
    escolhidos: list[dict] = []
    for c in sorted(cortes, key=lambda c: -(c.nota_gancho + c.nota_completude)):
        a, b = c.primeiro_segmento, c.ultimo_segmento
        if not (0 <= a <= b < len(segs)):
            continue
        inicio, fim = segs[a]["inicio"], segs[b]["fim"]
        if not (CLIP_MIN_S * 0.75 <= fim - inicio <= CLIP_MAX_S * 1.25):
            continue
        if any(inicio < e["fim"] and e["inicio"] < fim for e in escolhidos):
            continue
        escolhidos.append({
            "inicio": inicio,
            "fim": fim,
            "titulo": c.titulo.strip(),
            "gancho": c.gancho.strip(),
            "nota": round((c.nota_gancho + c.nota_completude) / 2, 1),
            "motivo": c.motivo.strip(),
            "depende_contexto": int(c.depende_contexto),
        })
        if len(escolhidos) == n:
            break
    escolhidos.sort(key=lambda e: e["inicio"])
    for i, e in enumerate(escolhidos, 1):
        e["idx"] = i
    return escolhidos
