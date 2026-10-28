# Plano técnico — Cortes de culto (nome provisório)

**Objetivo:** colar o link de um culto no YouTube e receber cortes verticais 9:16 com legenda. Este MVP cobre só o fluxo principal. Devocionais, carrossel e roteiro de célula entram depois como novos passos do pipeline.

## Fluxo

```
POST /cultos {url}
   └─ cria registro (status=pendente) e enfileira o job
        1. baixando        yt-dlp  → source.mp4 + audio.m4a
        2. transcrevendo   faster-whisper → transcript.json (segmentos com tempo)
        3. selecionando    Claude lê a transcrição → N trechos (início, fim, título, gancho)
        4. renderizando    ffmpeg: recorte + 9:16 + legenda queimada → clip_XX.mp4
        5. pronto
GET /cultos/{id}   página com status (polling a cada 3 s) e os cortes
```

## Stack

| Peça | Escolha | Por quê |
|---|---|---|
| API + páginas | FastAPI + Jinja2 | Simples; mesmo Python do bot Stark |
| Fila | `ThreadPoolExecutor(1)` no processo | Suficiente no MVP; trocar por RQ/Celery quando houver mais de um usuário |
| Banco | SQLite | Zero setup; migrar para Postgres depois |
| Download | yt-dlp | Já instalado |
| Transcrição | faster-whisper (local) | Sem custo por minuto; modelo `small` ou `medium` para pt-BR |
| Seleção dos trechos | Claude via API (`claude-sonnet-5-5`) | Entende o sentido da pregação, não só palavras-chave |
| Render | ffmpeg | Já instalado |

## Estrutura

```
app/main.py        rotas
app/db.py          SQLite (cultos, clips)
app/worker.py      orquestra os 4 passos e atualiza status
app/pipeline/      download.py · transcribe.py · select_clips.py · render.py
app/templates/     index.html · culto.html
data/              vídeos e cortes (ignorado no git)
```

## Marcos

1. **MVP (este esqueleto):** link → transcrição → 10 cortes 9:16 com legenda.
2. **Qualidade dos cortes:** legenda por palavra (word timestamps), crop com rosto (detecção) em vez de centro, nome/logo da igreja, opção 16:9.
3. **Conteúdo extra:** devocionais, carrossel de 7 slides, roteiro de célula (novos prompts sobre a mesma transcrição).
4. **Produto:** contas, planos e pagamento, limite por plano, fila real, armazenamento em S3/R2, domínio e LGPD.

## Riscos e cuidados

- **YouTube:** baixar vídeo pode ferir os termos do YouTube. No produto, o usuário deve ser dono do canal (ou ter autorização) e o ideal é aceitar upload direto do arquivo.
- **Direitos e privacidade:** rosto e voz de fiéis; incluir termos de uso e política de privacidade.
- **Custo e tempo:** Whisper local em CPU é lento (um culto de 1h pode levar dezenas de minutos). Para produção, usar GPU ou uma API de transcrição.
- **Limite de contexto:** cultos longos geram transcrições grandes; `select_clips.py` já trabalha com texto compacto por segmento.
- **Segurança:** validar que a URL é do YouTube antes de chamar o yt-dlp; nunca passar entrada do usuário para o shell.
