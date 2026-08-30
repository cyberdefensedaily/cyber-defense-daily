#!/usr/bin/env python3
"""
Generates the daily Cyber Defense Daily brief.

Calls Claude with the hosted web_search tool to research the day's top
cyber/defense/tech stories, asks for a structured JSON response, then
renders that into an HTML file matching the site's existing dossier
design -- clearly labeled AI-GENERATED / HUMAN-REVIEWED.

Writes:
  daily/YYYY-MM-DD.html   <- today's brief
  daily/index.html        <- regenerated listing of all briefs, newest first

This script does NOT publish anything by itself. The GitHub Action that
calls this script opens a Pull Request with these file changes; nothing
goes live until a human reviews and merges that PR.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
DAILY_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = """You are writing the daily brief for Cyber Defense Daily, an
independent cyber/defense/tech policy publication. The account's voice: plain,
direct, sourced, allergic to hype -- explicitly "not the hot-take version."
No breathless framing, no unearned superlatives, no filler. Short declarative
sentences preferred over long clause-stacked ones.

Research and select the 3-5 most significant cyber, defense, or tech policy
stories from roughly the last 24-48 hours. Prioritize stories with real
substance -- policy changes, disclosed vulnerabilities with broad impact,
government/military cyber actions, major breaches with confirmed details --
over speculative or lightly-sourced items.

For each story, write 2-4 sentences of substance: what happened, why it
matters, and what's still unresolved or disputed if anything is. Do not
editorialize beyond what the facts support.

Respond with ONLY valid JSON in exactly this shape, no other text:

{
  "headline": "A short, direct headline for today's brief, not clickbait",
  "dek": "One sentence under 20 words summarizing today's brief",
  "stories": [
    {
      "heading": "Short headline for this specific story",
      "body": "2-4 sentences of substance.",
      "source_name": "Publication or organization name",
      "source_url": "https://... the actual URL of the primary source"
    }
  ]
}

Every story MUST have a real, verifiable source_url from your search results.
Never invent a URL or a statistic. If you are not confident in a detail,
omit it rather than guess."""


def generate_brief() -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[
            {
                "role": "user",
                "content": f"Today's date is {today_str}. Research and write today's brief.",
            }
        ],
    )

    # Find the final text block (the JSON response) -- with the hosted
    # web_search tool, the API executes searches server-side and returns
    # the model's final answer as a text block once it's done searching.
    text_parts = [block.text for block in response.content if block.type == "text"]
    raw_text = "\n".join(text_parts).strip()

    # Model may wrap in a code fence despite instructions; strip if present.
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print("Failed to parse model output as JSON.", file=sys.stderr)
        print("Raw output was:", file=sys.stderr)
        print(raw_text, file=sys.stderr)
        raise e

    return data


def render_html(data: dict, date_str: str, case_number: str) -> str:
    stories_html = ""
    sources_html = ""
    for i, story in enumerate(data["stories"], start=1):
        stories_html += f"""
      <h2>{escape(story['heading'])}</h2>
      <p>{escape(story['body'])} [{i}]</p>
"""
        sources_html += (
            f'[{i}] {escape(story["source_name"])} '
            f'&mdash; <a href="{story["source_url"]}" target="_blank" '
            f'rel="noopener">{escape(story["source_url"])}</a><br>\n        '
        )

    pretty_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(data['headline'])} — Cyber Defense Daily</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{{
    --paper:#f3f4f2; --line:#d3d6cf; --navy:#0d1f3c; --navy-2:#152c52;
    --navy-3:#22406f; --ink:#1c2534; --muted:#5b6478; --stamp:#9c2b26;
    --ai-accent:#8a6a1f; --ai-bg:#fbf3df; --white:#ffffff;
  }}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:var(--paper);color:var(--ink);font-family:'Inter',sans-serif;}}
  a{{color:var(--navy-3);}}
  .letterhead{{background:linear-gradient(180deg,var(--navy-2),var(--navy));color:var(--white);padding:28px 20px;text-align:center;border-bottom:3px solid var(--navy-3);}}
  .letterhead .brand{{font-family:'Source Serif 4',serif;font-weight:700;font-size:19px;}}
  .letterhead .brand .dim{{color:rgba(255,255,255,0.55);font-weight:500;}}
  .letterhead .handle{{margin-top:4px;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.5);}}
  main{{max-width:680px;margin:0 auto;padding:44px 20px 70px;}}
  .meta-row{{display:flex;justify-content:space-between;align-items:center;font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted);margin-bottom:14px;}}
  .meta-row .case{{color:var(--navy-3);font-weight:600;}}
  .ai-badge{{display:inline-flex;align-items:center;gap:8px;background:var(--ai-bg);border:1px solid var(--ai-accent);color:var(--ai-accent);font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;padding:8px 14px;margin-bottom:24px;}}
  h1{{font-family:'Source Serif 4',serif;font-weight:700;font-size:clamp(26px,4.5vw,36px);line-height:1.2;color:var(--navy);margin-bottom:10px;}}
  .dek{{font-size:16.5px;color:var(--muted);line-height:1.55;margin-bottom:30px;}}
  article{{font-size:16.5px;line-height:1.72;color:var(--ink);}}
  article h2{{font-family:'Source Serif 4',serif;font-weight:600;font-size:21px;color:var(--navy);margin:34px 0 12px;padding-top:22px;border-top:1px solid var(--line);}}
  article p{{margin-bottom:18px;}}
  .sources{{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);line-height:1.9;}}
  .sources .label{{display:block;color:var(--navy-3);font-weight:600;margin-bottom:8px;letter-spacing:0.06em;}}
  .back-link{{display:block;margin-top:40px;font-family:'IBM Plex Mono',monospace;font-size:12px;}}
</style>
</head>
<body>
  <header class="letterhead">
    <div class="brand">Cyber Defense <span class="dim">Daily</span></div>
    <div class="handle">@cyber.defense.daily</div>
  </header>
  <main>
    <div class="meta-row">
      <span class="case">{case_number}</span>
      <span>{pretty_date}</span>
    </div>
    <div class="ai-badge">&#9679; AI-Generated &middot; Human-Reviewed</div>
    <h1>{escape(data['headline'])}</h1>
    <p class="dek">{escape(data['dek'])}</p>
    <article>
      {stories_html}
      <div class="sources">
        <span class="label">Sources</span>
        {sources_html}
      </div>
    </article>
    <a class="back-link" href="/daily/">&larr; All daily briefs</a>
  </main>
</body>
</html>
"""


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def rebuild_index():
    """Regenerate daily/index.html by scanning existing dated files."""
    files = sorted(
        [f for f in DAILY_DIR.glob("*.html") if f.name != "index.html"],
        reverse=True,
    )

    rows = ""
    for f in files:
        date_str = f.stem  # YYYY-MM-DD
        try:
            pretty = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            continue
        # Pull the headline out of the file's <h1> for the listing.
        content = f.read_text()
        m = re.search(r"<h1>(.*?)</h1>", content)
        headline = m.group(1) if m else date_str
        rows += f"""
      <a class="brief-row" href="/daily/{f.name}">
        <span class="brief-date">{pretty}</span>
        <span class="brief-headline">{headline}</span>
      </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Briefs — Cyber Defense Daily</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{--paper:#f3f4f2;--line:#d3d6cf;--navy:#0d1f3c;--navy-2:#152c52;--navy-3:#22406f;--ink:#1c2534;--muted:#5b6478;--ai-accent:#8a6a1f;--ai-bg:#fbf3df;--white:#fff;}}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:var(--paper);color:var(--ink);font-family:'Inter',sans-serif;}}
  a{{color:inherit;text-decoration:none;}}
  .letterhead{{background:linear-gradient(180deg,var(--navy-2),var(--navy));color:var(--white);padding:28px 20px;text-align:center;border-bottom:3px solid var(--navy-3);}}
  .letterhead .brand{{font-family:'Source Serif 4',serif;font-weight:700;font-size:19px;}}
  .letterhead .brand .dim{{color:rgba(255,255,255,0.55);font-weight:500;}}
  main{{max-width:680px;margin:0 auto;padding:44px 20px 70px;}}
  h1{{font-family:'Source Serif 4',serif;font-size:32px;color:var(--navy);margin-bottom:8px;}}
  .sub{{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--ai-accent);background:var(--ai-bg);border:1px solid var(--ai-accent);display:inline-block;padding:6px 12px;margin-bottom:30px;}}
  .brief-row{{display:flex;flex-direction:column;gap:4px;padding:16px 0;border-bottom:1px solid var(--line);}}
  .brief-row:hover .brief-headline{{color:var(--navy-3);}}
  .brief-date{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);}}
  .brief-headline{{font-family:'Source Serif 4',serif;font-weight:600;font-size:18px;color:var(--ink);}}
</style>
</head>
<body>
  <header class="letterhead">
    <div class="brand">Cyber Defense <span class="dim">Daily</span></div>
  </header>
  <main>
    <h1>Daily Briefs</h1>
    <div class="sub">AI-Generated &middot; Human-Reviewed, Daily</div>
    {rows if rows else '<p style="color:var(--muted)">No briefs published yet.</p>'}
  </main>
</body>
</html>
"""
    (DAILY_DIR / "index.html").write_text(index_html)


def main():
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y-%m-%d")
    out_path = DAILY_DIR / f"{date_str}.html"

    if out_path.exists():
        print(f"Brief for {date_str} already exists, skipping generation.")
        return

    data = generate_brief()

    # Simple sequential case number based on how many briefs exist so far.
    existing = len(list(DAILY_DIR.glob("*.html")))
    case_number = f"CDD-DAILY-{existing + 1:04d}"

    html = render_html(data, date_str, case_number)
    out_path.write_text(html)
    print(f"Wrote {out_path}")

    rebuild_index()
    print("Rebuilt daily/index.html")


if __name__ == "__main__":
    main()
