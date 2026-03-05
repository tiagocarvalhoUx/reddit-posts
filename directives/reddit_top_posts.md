# Directive: Reddit Top Posts por Tópico

## Objetivo
Buscar os 100 posts mais recentes no Reddit para cada tópico definido, filtrar os da última semana e retornar os 5 com maior engajamento e relevância por tópico.

## Inputs
- `topics`: lista de termos de busca (ex: ["n8n", "automation"])
- `top_n`: número de posts a retornar por tópico (padrão: 5)

## Tools/Scripts
- `execution/fetch_reddit_posts.py`

## Output
- `.tmp/reddit_top_posts.json` — dados completos
- Tabela no terminal com os top posts por tópico

## Processo
1. Para cada tópico, buscar os 100 posts mais recentes via Reddit JSON API
2. Filtrar apenas posts criados nos últimos 7 dias
3. Calcular score de engajamento: upvotes + (comentários * 3)
4. Ranquear e retornar os top N por tópico
5. Salvar resultado em `.tmp/reddit_top_posts.json`

## Edge Cases
- Rate limit da Reddit API: aguardar 2s entre requests entre tópicos, 1s entre subreddits
- Posts removidos/deleted: ignorar
- API retorna menos de 100 posts: prosseguir com o que houver e registrar warning
- Busca global por "automation" traz muito ruído (CNC, jogos, etc): usar busca por subreddits específicos (n8n, nocode, zapier, automation, selfhosted) combinada com query refinada

## Notas Técnicas
- Reddit JSON API pública: `https://www.reddit.com/search.json`
- Não requer autenticação para leitura pública
- Parâmetros: `q`, `sort=new`, `limit=100`, `t=week`
- User-Agent obrigatório para evitar bloqueio
