# Cortes de culto (nome provisório)

Cole o link de um culto no YouTube (ou envie o arquivo) e receba cortes verticais 9:16 com legenda.

- [`PLANO.md`](PLANO.md): plano técnico do MVP (este esqueleto).
- [`PLANO_DE_ACAO.md`](PLANO_DE_ACAO.md): caminho do protótipo até o produto.

## Rodar

Requisitos: Python 3.11+, `ffmpeg` no PATH e uma chave da API da Anthropic.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
uvicorn app.main:app --reload
```

Abra http://localhost:8000. Na primeira transcrição o faster-whisper baixa o modelo (`small`, cerca de 500 MB).

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `WHISPER_MODEL` | `small` | `medium` acerta mais em pt-BR, mas é mais lento |
| `WHISPER_DEVICE` | `auto` | `cuda` para usar GPU |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | modelo que escolhe os trechos |
| `N_CLIPS` | `10` | número máximo de cortes |
| `CORTES_DATA_DIR` | `./data` | vídeos, transcrições, cortes e o SQLite |

## Como funciona

```
POST /cultos {url | arquivo}
   └─ cria registro (status=pendente) e enfileira o job
        1. baixando        yt-dlp (ou upload) → source.mp4 + audio.wav
        2. transcrevendo   faster-whisper → transcript.json (segmentos e palavras com tempo)
        3. selecionando    Claude lê a transcrição → até N trechos (início, fim, título, gancho, nota, motivo)
        4. renderizando    ffmpeg: recorte + 9:16 + legenda queimada → clip_XX.mp4
        5. pronto
GET /cultos/{id}   página com status (polling a cada 3 s) e os cortes
```

Cada etapa pula se a saída já existe. Se o render falhar, "Tentar de novo" não refaz download nem transcrição. Ao subir o servidor, cultos inacabados voltam para a fila.

Já entram neste esqueleto algumas melhorias do plano de ação:

- **Trava de fidelidade**: o modelo escolhe um intervalo de segmentos contíguos (primeiro e último ID). Não dá para juntar frases de pontos diferentes, e o corte sempre começa e termina em fronteira de segmento.
- **Nota e motivo por corte**, com a página ordenada por nota, e aviso quando o trecho depende do que foi dito antes.
- **Legenda por palavra**: blocos de até 3 palavras com destaque da palavra falada (word timestamps do Whisper).
- **Glossário bíblico** no `initial_prompt` do Whisper (`app/config.py`).
- **Upload direto** e declaração de autorização obrigatória.
- Recusas do modelo usam o fallback do servidor (`fallbacks="default"`).

Ainda não: enquadramento com rosto (o crop é central), editor por transcrição, kit de marca, conteúdo extra.

## Estrutura

```
app/main.py        rotas
app/db.py          SQLite (cultos, clips)
app/worker.py      orquestra os 4 passos e atualiza o status
app/config.py      configuração e glossário
app/pipeline/      download.py · transcribe.py · select_clips.py · render.py
app/templates/     base.html · index.html · culto.html
data/              vídeos e cortes (ignorado no git)
```

## Segurança

- Só links de vídeo do YouTube são aceitos; a URL é reconstruída a partir do ID do vídeo antes de chegar ao yt-dlp.
- yt-dlp é chamado pela API Python e o ffmpeg com lista de argumentos. Nenhuma entrada do usuário passa por shell.
- A rota de download só entrega arquivos `clip_XX.mp4`, nunca o vídeo original.
- Sem autenticação: rode só localmente até a fase 4.
