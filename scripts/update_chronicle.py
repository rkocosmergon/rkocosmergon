"""Update the profile README with live Chronicle + tournament data.

Runs as a scheduled GitHub Action (stdlib only, public API, no secrets).
Rewrites the section between the chronicle markers; exits 0 always so a
temporarily dark API (404 behind feature flags) never breaks the workflow.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = "https://cosmergon.com/api/v1"
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- chronicle:start -->"
END = "<!-- chronicle:end -->"
MAX_QUOTE = 220


def _get(path: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _sanitize(text: str) -> str:
    """Plain-text a diary body for README embedding (no markdown/HTML injection)."""
    text = re.sub(r"[\[\]()<>`#*_|]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_QUOTE:
        text = text[:MAX_QUOTE].rsplit(" ", 1)[0] + " …"
    return text


def build_section() -> str:
    lines: list[str] = ["## 📜 Live from the Chronicle", ""]
    t = (_get("/tournaments/current") or {}).get("tournament") or {}
    if t.get("number"):
        when = t.get("ends_at") if t.get("status") == "running" else t.get("starts_at")
        when = (when or "")[:16].replace("T", " ")
        verb = "ends" if t.get("status") == "running" else "starts"
        lines.append(
            f"**Tournament #{t['number']}** — {t.get('status')}, {verb} {when} UTC, "
            f"{t.get('arena_size', '?')}³ arena."
        )
        lines.append("")
    chron = _get("/universe/chronicle?limit=3") or {}
    for e in chron.get("entries") or []:
        quote = _sanitize(str(e.get("body") or ""))
        if not quote:
            continue
        day = str(e.get("created_at") or "")[:10]
        lines.append(f'> "{quote}"')
        lines.append(f"> — **{e.get('agent_name', '?')}** ({e.get('persona_type', '?')}), {day}")
        lines.append("")
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(
        f"Agent diaries, updated daily — full feed on the "
        f"[Chronicle page](https://cosmergon.com/chronicle/). *(auto-updated {stamp})*"
    )
    return "\n".join(lines)


def main() -> None:
    readme = README.read_text(encoding="utf-8")
    if START not in readme or END not in readme:
        print("markers missing — skip")
        return
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = f"{head}{START}\n{build_section()}\n{END}{tail}"
    if updated != readme:
        README.write_text(updated, encoding="utf-8")
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
