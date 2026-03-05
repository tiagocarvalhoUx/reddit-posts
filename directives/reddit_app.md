# Directive: Gerar App de Visualização de Posts

## Objetivo
Gerar um arquivo HTML auto-contido que exibe os top posts por tópico em uma interface moderna.

## Inputs
- `.tmp/reddit_top_posts.json` — gerado por `fetch_reddit_posts.py`

## Tools/Scripts
- `execution/generate_app.py`

## Output
- `.tmp/app.html` — abre direto no browser, sem servidor necessário

## Processo
1. Ler `.tmp/reddit_top_posts.json`
2. Gerar HTML com dados embedados
3. Salvar em `.tmp/app.html`
4. Abrir no browser: `start .tmp/app.html`

## Fluxo completo (atualizar dados + abrir app)
```bash
python execution/fetch_reddit_posts.py && python execution/generate_app.py
start .tmp/app.html
```
