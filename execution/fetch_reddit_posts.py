"""
fetch_reddit_posts.py
Busca os posts mais recentes no Reddit por tópico e retorna os top N por engajamento.
"""

import requests
import json
import time
import os
import sys
from datetime import datetime, timezone
from typing import cast

sys.path.insert(0, os.path.dirname(__file__))
from logger import AutomationLogger

# --- Config ---
# Para "automation", restringimos a subreddits de workflow/tech para evitar ruído
TOPICS = {
    "n8n": {
        "query": "n8n",
        "subreddits": None,  # busca global, já é nicho
    },
    "automation": {
        "query": "automation workflow OR nocode OR zapier OR make.com OR n8n OR AI agent",
        "subreddits": ["n8n", "nocode", "zapier", "automation", "selfhosted", "MachineLearning", "artificial"],
    },
}
TOP_N = 5
LIMIT = 100
TIME_FILTER = "week"
_TMP_DIR = os.environ.get("TMP_DIR", ".tmp")
OUTPUT_FILE = os.path.join(_TMP_DIR, "reddit_top_posts.json")

HEADERS = {
    "User-Agent": "antigravity-agent/1.0 (research bot)"
}

def fetch_posts(query: str, subreddits: list[str] | None = None, limit: int = 100) -> list[dict]:
    """Busca posts no Reddit. Se subreddits fornecidos, busca em cada um e agrega."""
    all_posts = []

    if subreddits:
        # Busca dentro de cada subreddit relevante
        for sub in subreddits:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {"q": query, "sort": "new", "limit": limit, "t": TIME_FILTER, "restrict_sr": "true"}
            try:
                r = requests.get(url, headers=HEADERS, params=params, timeout=15)
                r.raise_for_status()
                posts = r.json().get("data", {}).get("children", [])
                all_posts.extend([p["data"] for p in posts])
                time.sleep(1)
            except requests.RequestException as e:
                print(f"    ERRO em r/{sub}: {e}")
        # Deduplicar por id
        seen = set()
        unique = []
        for p in all_posts:
            if p["id"] not in seen:
                seen.add(p["id"])
                unique.append(p)
        print(f"  {len(unique)} posts únicos após busca em {len(subreddits)} subreddits")
        return unique
    else:
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "sort": "new", "limit": limit, "t": TIME_FILTER, "type": "link"}
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            r.raise_for_status()
            posts = r.json().get("data", {}).get("children", [])
            print(f"  {len(posts)} posts retornados")
            return [p["data"] for p in posts]
        except requests.RequestException as e:
            print(f"  ERRO: {e}")
            return []

def is_within_week(created_utc: float) -> bool:
    """Verifica se o post foi criado nos últimos 7 dias."""
    now = datetime.now(timezone.utc).timestamp()
    return (now - created_utc) <= 7 * 24 * 3600

def engagement_score(post: dict) -> int:
    """Score: upvotes + comentários * 3 (comentários valem mais para relevância)."""
    return post.get("score", 0) + post.get("num_comments", 0) * 3

def extract_image(post: dict) -> str | None:
    """Extrai a melhor URL de imagem disponível no post."""
    # 1. Preview de alta qualidade (encoded — decodificar &amp; → &)
    try:
        preview = post.get("preview", {}).get("images", [])
        if preview:
            url = preview[0]["source"]["url"]
            return url.replace("&amp;", "&")
    except (KeyError, IndexError):
        pass
    # 2. Thumbnail (menor, mas sempre disponível quando existe)
    thumb = post.get("thumbnail", "")
    if thumb and thumb.startswith("http"):
        return thumb
    return None

def process_topic(topic: str) -> list[dict]:
    """Busca, filtra e ranqueia posts de um tópico."""
    cfg = TOPICS[topic]
    query: str = str(cfg["query"])
    subs: list[str] | None = cast(list[str], cfg["subreddits"]) if isinstance(cfg["subreddits"], list) else None
    raw_posts = fetch_posts(query, subs)

    # Filtrar deletados e fora da semana
    valid = [
        p for p in raw_posts
        if p.get("title") and not p.get("removed_by_category")
        and is_within_week(p.get("created_utc", 0))
    ]

    if len(valid) < len(raw_posts):
        print(f"  [{topic}] {len(raw_posts) - len(valid)} posts fora da semana ou removidos, ignorados")

    # Ranquear por engajamento
    ranked = sorted(valid, key=engagement_score, reverse=True)
    top = ranked[:TOP_N]

    # Formatar saída
    result = []
    for i, p in enumerate(top, 1):
        result.append({
            "rank": i,
            "title": p.get("title"),
            "subreddit": f"r/{p.get('subreddit')}",
            "url": f"https://reddit.com{p.get('permalink')}",
            "upvotes": p.get("score", 0),
            "comments": p.get("num_comments", 0),
            "engagement_score": engagement_score(p),
            "created_utc": datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "author": p.get("author"),
            "flair": p.get("link_flair_text"),
            "image_url": extract_image(p),
        })
    return result

def print_results(all_results: dict):
    """Imprime tabela de resultados no terminal."""
    for topic, posts in all_results.items():
        print(f"\n{'='*60}")
        print(f"TOP {TOP_N} POSTS — '{topic.upper()}' (últimos 7 dias)")
        print(f"{'='*60}")
        if not posts:
            print("  Nenhum post encontrado.")
            continue
        for p in posts:
            print(f"\n  #{p['rank']} [{p['engagement_score']} pts] {p['title'][:70]}")
            print(f"      {p['subreddit']} | {p['upvotes']} upvotes | {p['comments']} comentários | {p['created_utc']}")
            print(f"      {p['url']}")

def main():
    os.makedirs(_TMP_DIR, exist_ok=True)
    log = AutomationLogger("fetch_reddit_posts")
    log.info("Iniciando busca", {"topics": list(TOPICS.keys()), "top_n": TOP_N, "time_filter": TIME_FILTER})

    all_results = {}
    status = "success"

    for topic in TOPICS:
        log.info(f"Buscando tópico: {topic}")
        try:
            results = process_topic(topic)
            all_results[topic] = results
            log.info(f"Tópico '{topic}' concluído", {"posts_found": len(results)})
        except Exception as e:
            log.error(f"Falha no tópico '{topic}'", {"error": str(e)})
            all_results[topic] = []
            status = "partial"
        time.sleep(2)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    log.info(f"Resultados salvos", {"output": OUTPUT_FILE})

    print_results(all_results)

    summary = {t: len(p) for t, p in all_results.items()}
    log.finish(status=status, summary={"posts_per_topic": summary, "output": OUTPUT_FILE})

if __name__ == "__main__":
    main()
