# Plano de ação — plataforma de cortes e conteúdo para igrejas

Evolução do MVP em [`PLANO.md`](PLANO.md). Aqui está o caminho do protótipo até um produto, com as melhorias sobre a ideia inicial.

## 1. Visão

Do culto de domingo a uma semana inteira de conteúdo fiel à mensagem, pronto para postar e com aprovação humana.

O mercado já tem ferramentas genéricas de corte (OpusClip e similares) e soluções específicas para igrejas. Nosso espaço está em ser confiável para o contexto de fé: não distorcer a pregação, acertar termos bíblicos e respeitar a identidade de cada igreja.

## 2. Melhorias sobre a ideia inicial

### Qualidade do corte

| Melhoria | O que resolve | Como |
|---|---|---|
| Enquadramento com rosto | O crop central corta o pregador quando ele anda pelo palco | Detecção de rosto/pessoa (MediaPipe ou OpenCV) e câmera virtual suavizada |
| Legenda animada por palavra | Legenda por frase é pouco chamativa | Word timestamps do Whisper, destaque da palavra falada |
| Vocabulário bíblico | Whisper erra "Gálatas", "Melquisedeque", nomes de ministérios | `initial_prompt` com glossário, mais lista de correções por igreja |
| Detecção de versículos | O post fica sem contexto | Reconhecer citações, buscar o texto na Bíblia (versão licenciada ou domínio público) e mostrar um cartão com a referência |
| Nota e justificativa por corte | O usuário não sabe por que aquele trecho foi escolhido | O LLM devolve nota de gancho, completude e a razão; a interface ordena por nota |
| Corte em fronteira de frase | Cortes que terminam no meio da fala | Ajustar início e fim para o silêncio ou fim de frase mais próximo (VAD) |

### Fidelidade e confiança (diferencial)

- **Trava de fidelidade:** o LLM só pode escolher trechos contíguos. Nada de juntar frases de pontos diferentes, que poderia mudar o sentido da pregação.
- **Aprovação humana obrigatória** antes de publicar, com tela de revisão.
- **Perfil da igreja:** denominação, tom, termos que não devem aparecer e público. Entra no prompt.
- **Verificação de contexto:** sinalizar trechos que dependem do que foi dito antes ("como eu disse...").

### Fluxo do usuário

- **Editor por transcrição:** ajustar início e fim clicando no texto, juntar ou dividir cortes, regenerar um corte só.
- **Kit de marca:** logo, cores, fonte, vinheta de abertura e fecho, nome do pregador (lower-third).
- **Três entradas:** link do YouTube, upload do arquivo e conexão do canal (OAuth), que também resolve a autorização de uso.
- **Detecção automática de culto ao vivo:** quando a live terminar, o processamento começa sozinho.
- **Calendário semanal:** distribui os cortes em segunda a sábado e publica via API (Instagram, YouTube Shorts, TikTok) ou lembra o responsável.

### Conteúdo além do vídeo

Todos partem da mesma transcrição, por isso o custo extra é baixo:

- 5 devocionais curtos
- carrossel de 7 slides (exportado em PNG)
- roteiro de célula/pequeno grupo, com perguntas e versículo-base, em A4
- legenda por rede social com hashtags
- resumo do culto para o WhatsApp
- resumo para quem faltou e esboço da mensagem para o pastor

### Operação

- **Custo previsível:** transcrever só o áudio, cachear tudo por culto, limitar minutos por plano.
- **Retentativas e status claro por etapa,** com aviso por e-mail ou WhatsApp quando terminar.
- **Métricas de uso** e, depois, desempenho dos posts para melhorar a seleção.

### Já no esqueleto

Trava de fidelidade, nota e motivo por corte, aviso de dependência de contexto, legenda por palavra, glossário no Whisper, corte em fronteira de segmento, upload direto com declaração de autorização e etapas reentrantes. Ver [`README.md`](README.md).

## 3. Arquitetura-alvo

```
Web (Rails/Next ou FastAPI+HTMX)  →  API  →  Fila (Redis + RQ/Celery)
                                          ├─ worker de transcrição (GPU ou API)
                                          ├─ worker de seleção (LLM)
                                          └─ worker de render (ffmpeg, CPU)
Postgres  ·  Storage S3/R2 (vídeos e cortes)  ·  CDN  ·  Sentry/logs
```

Etapas independentes e reentrantes: se o render falha, não repete a transcrição.

## 4. Fases e entregas

| Fase | Prazo | Entrega | Pronto quando |
|---|---|---|---|
| 0. Validação | 1 semana | Rodar o esqueleto com 3 cultos reais da IBA; entrevistar 3 a 5 mídias de igreja | Lista das 5 maiores dores e quanto aceitariam pagar |
| 1. MVP fechado | 3 semanas | Upload + YouTube, transcrição, 10 cortes com legenda por palavra, revisão e download | Uma igreja piloto publica cortes sem ajuda técnica |
| 2. Qualidade | 3 semanas | Rosto no enquadramento, glossário bíblico, corte em fronteira de frase, nota por corte, editor por transcrição | Pelo menos 7 em 10 cortes aprovados sem edição |
| 3. Marca e conteúdo | 3 semanas | Kit de marca, devocionais, carrossel, roteiro de célula, legendas por rede | Pacote semanal gerado em um clique |
| 4. Produto | 4 semanas | Contas, planos, Pix e cartão, limites, e-mails de status, termos e LGPD, Postgres, fila e storage em nuvem | Primeiras cobranças reais |
| 5. Automação | 4 semanas | Conexão do canal, detecção de live, calendário e publicação | Culto vira agenda da semana sem intervenção |

Total estimado: cerca de 4 meses para uma pessoa dedicada. Pode ser menos se reaproveitarmos partes do bot Stark.

## 5. Modelo de negócio (hipótese a validar na fase 0)

- **Grátis:** 1 culto de teste, com marca d'água.
- **Avulso:** pagamento por culto, de olho em igrejas pequenas.
- **Mensal/anual:** por número de cultos e usuários, com kit de marca e calendário.
- **Pagamento brasileiro:** Pix e boleto (Asaas, Mercado Pago), além de cartão.
- **Custo por culto a medir:** transcrição + LLM + render + armazenamento. A margem depende disso, então medir desde a fase 1.

## 6. Riscos e como tratar

| Risco | Tratamento |
|---|---|
| Termos do YouTube ao baixar vídeos | Priorizar upload e canal conectado; exigir declaração de autorização |
| Direitos autorais (música de louvor, pregador convidado) | Detectar trechos de música e evitar cortá-los; aviso nos termos |
| LGPD: imagem e voz de fiéis, inclusive crianças | Política de privacidade, consentimento da igreja, exclusão de dados a pedido |
| Distorção da mensagem pelo LLM | Só trechos contíguos, revisão humana, perfil da igreja |
| Custo de GPU/transcrição | Medir, limitar por plano, API ou GPU sob demanda |
| Concorrência | Foco em fidelidade, glossário bíblico, marca e fluxo semanal em pt-BR |
| Qualidade do áudio dos cultos | Pré-processamento (denoise/normalização) e aviso de qualidade baixa |

## 7. Métricas

- Tempo do link ao pacote pronto (meta: menos de 15 min por culto de 1h)
- % de cortes aprovados sem edição (meta fase 2: 70%)
- Custo por culto processado
- Igrejas ativas por semana e retenção em 4 semanas
- Cortes publicados por culto

## 8. Decisões que precisamos tomar

1. **Stack final:** manter Python/FastAPI (reaproveita o Stark) ou migrar para Rails/Next.
2. **Transcrição:** modelo local em GPU ou API paga.
3. **Escopo religioso:** só evangélico ou também católico (missas têm liturgia e música diferentes).
4. **Quem é o piloto:** a IBA serve como primeiro cliente e fonte de cultos para testar.
5. **Nome e marca:** definir antes da fase 4.
6. **Modelo de preço:** avulso, assinatura ou os dois.

## 9. Próximos passos imediatos

1. Rodar o esqueleto com um culto real e medir tempo e qualidade.
2. Conversar com 3 a 5 mídias de igreja para validar as dores e o preço.
3. Escolher as 3 melhorias de maior impacto para a fase 2 (sugestão: enquadramento com rosto, legenda por palavra e glossário bíblico).
4. Registrar nome, domínio e rascunho dos termos de uso.
