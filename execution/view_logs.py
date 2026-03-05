"""
view_logs.py
Visualizador de logs de todas as automações.
Uso: python execution/view_logs.py [--automation NOME] [--last N] [--verbose]
"""

import json
import os
import glob
import argparse
from datetime import datetime
from typing import Any

LOGS_DIR = "logs"
LEVEL_ICONS: dict[str, str] = {"INFO": "   ", "WARNING": "[!]", "ERROR": "[X]"}

def load_runs(automation: str | None = None) -> list[Any]:
    pattern = os.path.join(LOGS_DIR, f"{automation}.jsonl" if automation else "*.jsonl")
    files = glob.glob(pattern)
    if not files:
        return []
    runs: list[dict] = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    runs.append(json.loads(line))
    runs.sort(key=lambda r: r["started_at"], reverse=True)
    return runs

def fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return iso

def print_run(run: dict, verbose: bool = False):
    status_icon = "[OK]" if run["status"] == "success" else ("[~]" if run["status"] == "partial" else "[X]")
    print(f"\n{'-'*60}")
    print(f"  {status_icon} [{run['automation']}]  run {run['run_id']}")
    print(f"    Iniciado : {fmt_time(run['started_at'])}")
    print(f"    Duracao  : {run['duration_s']}s   Status: {run['status'].upper()}")
    if run.get("summary"):
        for k, v in run["summary"].items():
            print(f"    {k}: {v}")
    if verbose:
        print(f"\n    Eventos:")
        for e in run.get("events", []):
            icon = LEVEL_ICONS.get(e["level"], "   ")
            data = f"  -> {e.get('data')}" if e.get("data") else ""
            print(f"      {icon} [{e['level']}] {fmt_time(e['ts'])}  {e['msg']}{data}")

def main():
    parser = argparse.ArgumentParser(description="Visualizador de logs de automacoes")
    parser.add_argument("--automation", "-a", help="Filtrar por nome de automacao")
    parser.add_argument("--last", "-n", type=int, default=10, help="Ultimos N runs (padrao: 10)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar eventos detalhados")
    args = parser.parse_args()

    all_runs = load_runs(args.automation)
    if not all_runs:
        print("Nenhum log encontrado.")
        return

    runs: list[Any] = []
    for i, r in enumerate(all_runs):
        if i >= args.last:
            break
        runs.append(r)
    total = len(runs)
    ok = sum(1 for r in runs if r["status"] == "success")
    fail = sum(1 for r in runs if r["status"] not in ("success", "partial"))

    print(f"\n{'='*60}")
    print(f"  LOGS DE AUTOMACOES  |  {total} runs  |  OK: {ok}  FALHA: {fail}")
    print(f"{'='*60}")

    for run in runs:
        print_run(run, verbose=args.verbose)

    print(f"\n{'-'*60}")
    print(f"  Dica: use --verbose para ver todos os eventos de cada run")
    print(f"        use --automation fetch_reddit_posts para filtrar\n")

if __name__ == "__main__":
    main()
