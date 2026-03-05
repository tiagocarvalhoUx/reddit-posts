"""
send_email.py
Gera e envia um e-mail HTML profissional com os top posts do Reddit.
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(__file__))
from logger import AutomationLogger

# Carrega .env
_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_ENV):
    with open(_ENV) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()

DATA_FILE   = ".tmp/reddit_top_posts.json"
TO_EMAIL    = "tiago_carvalho07@yahoo.com.br"
SUBJECT     = "Reddit Pulse · Top Posts da Semana"

# --- SMTP config via .env ---
SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
FROM_EMAIL = os.getenv("EMAIL_FROM", "")
FROM_PASS  = os.getenv("EMAIL_PASSWORD", "")


# ---------------------------------------------------------------------------
# HTML EMAIL TEMPLATE
# ---------------------------------------------------------------------------

def rank_badge(rank: int) -> str:
    colors = {
        1: ("#b45309", "#fef3c7"),
        2: ("#475569", "#f1f5f9"),
        3: ("#9a3412", "#ffedd5"),
    }
    bg, text_c = colors.get(rank, ("#6b7280", "#f9fafb"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{text_c};'
        f'border-radius:99px;padding:2px 10px;font-size:11px;font-weight:700;'
        f'letter-spacing:.5px;">#{rank}</span>'
    )


def stat_pill(icon: str, value: str, color: str) -> str:
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'background:{color}18;color:{color};border-radius:99px;'
        f'padding:3px 10px;font-size:11px;font-weight:600;">'
        f'{icon} {value}</span>'
    )


def post_card(post: dict, accent: str) -> str:
    image_block = ""
    if post.get("image_url"):
        image_block = (
            f'<div style="position:relative;width:100%;aspect-ratio:16/7;overflow:hidden;'
            f'border-radius:12px 12px 0 0;background:#e2e8f0;">'
            f'<img src="{post["image_url"]}" alt="" width="100%" '
            f'style="width:100%;height:180px;object-fit:cover;display:block;" />'
            f'</div>'
        )
    else:
        emoji = "⚡" if accent == "#f97316" else "🤖"
        gradient = (
            "linear-gradient(135deg,#fff7ed,#fed7aa)" if accent == "#f97316"
            else "linear-gradient(135deg,#fdf4ff,#e9d5ff)"
        )
        image_block = (
            f'<div style="width:100%;height:140px;border-radius:12px 12px 0 0;'
            f'background:{gradient};display:flex;align-items:center;justify-content:center;'
            f'font-size:48px;">{emoji}</div>'
        )

    subreddit_pill = (
        f'<span style="display:inline-block;background:{accent}18;color:{accent};'
        f'border-radius:99px;padding:2px 10px;font-size:11px;font-weight:600;">'
        f'{post["subreddit"]}</span>'
    )

    flair_html = ""
    if post.get("flair"):
        flair_html = (
            f'<span style="display:inline-block;background:#f1f5f9;color:#64748b;'
            f'border-radius:99px;padding:2px 8px;font-size:10px;margin-left:6px;">'
            f'{post["flair"]}</span>'
        )

    date_str = post.get("created_utc", "").replace(" UTC", "")

    return f"""
<div style="background:#ffffff;border-radius:14px;margin-bottom:16px;
     box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden;border:1px solid #e2e8f0;">

  {image_block}

  <div style="padding:18px 20px 20px;">

    <!-- rank + flair row -->
    <div style="margin-bottom:10px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
      {rank_badge(post["rank"])}
      {subreddit_pill}
      {flair_html}
    </div>

    <!-- title -->
    <h3 style="margin:0 0 8px;font-size:15px;font-weight:700;line-height:1.4;color:#0f172a;">
      <a href="{post["url"]}" style="color:#0f172a;text-decoration:none;">{post["title"]}</a>
    </h3>

    <!-- author + date -->
    <p style="margin:0 0 12px;font-size:11px;color:#94a3b8;">
      u/{post.get("author","?")} &nbsp;·&nbsp; {date_str}
    </p>

    <!-- stats -->
    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;">
      {stat_pill("▲", f'{post["upvotes"]:,} upvotes', "#f97316")}
      {stat_pill("💬", f'{post["comments"]:,} comentários', "#64748b")}
      {stat_pill("⚡", f'{post["engagement_score"]:,} pts', accent)}
    </div>

    <!-- CTA button -->
    <a href="{post["url"]}"
       style="display:inline-block;background:{accent};color:#ffffff;
              border-radius:8px;padding:9px 20px;font-size:13px;font-weight:600;
              text-decoration:none;letter-spacing:.2px;">
      Ver post →
    </a>

  </div>
</div>"""


def section_block(topic: str, posts: list, accent: str, icon: str) -> str:
    label = "n8n" if topic == "n8n" else "Automation"
    cards = "".join(post_card(p, accent) for p in posts)
    return f"""
<div style="margin-bottom:36px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;
              padding-bottom:12px;border-bottom:2px solid {accent}30;">
    <span style="font-size:22px;">{icon}</span>
    <h2 style="margin:0;font-size:18px;font-weight:800;color:#0f172a;">
      Top 5 · {label}
    </h2>
    <span style="margin-left:auto;background:{accent}15;color:{accent};
                 border-radius:99px;padding:3px 12px;font-size:11px;font-weight:700;">
      {len(posts)} posts
    </span>
  </div>
  {cards}
</div>"""


def build_email_html(data: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y · %H:%M UTC")

    n8n_section  = section_block("n8n",        data.get("n8n", []),        "#f97316", "⚡")
    auto_section = section_block("automation",  data.get("automation", []), "#8b5cf6", "🤖")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 16px;">
  <tr><td align="center">

    <!-- Container -->
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <!-- HEADER -->
      <tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
                     border-radius:16px 16px 0 0;padding:32px 32px 28px;text-align:center;">

        <div style="display:inline-flex;align-items:center;gap:8px;
                    background:rgba(249,115,22,0.15);border:1px solid rgba(249,115,22,0.3);
                    border-radius:99px;padding:6px 16px;margin-bottom:16px;">
          <span style="width:6px;height:6px;border-radius:50%;background:#f97316;display:inline-block;"></span>
          <span style="color:#f97316;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">
            Reddit Pulse
          </span>
        </div>

        <h1 style="margin:0 0 8px;color:#f8fafc;font-size:26px;font-weight:800;letter-spacing:-.3px;">
          Top Posts da Semana
        </h1>
        <p style="margin:0 0 16px;color:#94a3b8;font-size:13px;">
          Os posts mais relevantes sobre n8n e automação no Reddit
        </p>
        <span style="display:inline-block;background:rgba(255,255,255,0.06);
                     border:1px solid rgba(255,255,255,0.1);border-radius:8px;
                     padding:4px 14px;color:#64748b;font-size:11px;">
          {now}
        </span>

      </td></tr>

      <!-- BODY -->
      <tr><td style="background:#f8fafc;padding:28px 24px 8px;">
        {n8n_section}
        {auto_section}
      </td></tr>

      <!-- FOOTER -->
      <tr><td style="background:#0f172a;border-radius:0 0 16px 16px;
                     padding:20px 32px;text-align:center;">
        <p style="margin:0;color:#475569;font-size:11px;">
          Gerado por <strong style="color:#94a3b8;">Antigravity Agent</strong>
          &nbsp;·&nbsp; dados via Reddit JSON API
        </p>
      </td></tr>

    </table>
  </td></tr>
  </table>

</body>
</html>"""


def send(html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"]    = FROM_EMAIL
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))

    password = FROM_PASS.replace(" ", "")  # remove espaços de App Passwords

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(FROM_EMAIL, password)
            server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(FROM_EMAIL, password)
            server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())


def main():
    log = AutomationLogger("send_email")
    log.info("Carregando dados", {"input": DATA_FILE})

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    html = build_email_html(data)
    log.info("HTML do e-mail gerado")

    if not FROM_EMAIL or not FROM_PASS:
        log.error("Credenciais de e-mail não configuradas", {"vars": "EMAIL_FROM, EMAIL_PASSWORD"})
        print("  ERRO: configure EMAIL_FROM e EMAIL_PASSWORD no arquivo .env")
        sys.exit(1)

    log.info(f"Enviando para {TO_EMAIL}", {"smtp": f"{SMTP_HOST}:{SMTP_PORT}"})
    send(html)
    log.finish(status="success", summary={"to": TO_EMAIL})
    print(f"\n  E-mail enviado para {TO_EMAIL}")


if __name__ == "__main__":
    main()
