"""Stamp a guestbook issue onto README.md.

Reads the `issues.opened` event payload, pulls the visitor's handle and the
`Message` field from the issue form, and inserts a row between the
GUESTBOOK markers in README.md. Newest entry first, capped so the section
never grows without bound. Prints the cleaned message so the workflow can
echo it back in the closing comment.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

README = "README.md"
START = "<!-- GUESTBOOK:START -->"
END = "<!-- GUESTBOOK:END -->"
MAX_ENTRIES = 12
MAX_LEN = 140


def extract_message(body: str) -> str:
    # Issue forms render a textarea as "### Message\n\n<text>".
    m = re.search(r"### Message\s*\n(.*?)(?:\n### |\Z)", body, re.S)
    text = m.group(1) if m else body
    # It ends up inside a Markdown table cell that GitHub renders as HTML,
    # so drop anything that could break the table or smuggle in markup.
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[<>|`\[\]]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1].rstrip() + "…"
    return text or "👋"


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        event = json.load(f)

    issue = event["issue"]
    labels = {l["name"] for l in issue.get("labels", [])}
    if "guestbook" not in labels:
        print("not a guestbook issue, skipping", file=sys.stderr)
        return 0

    login = issue["user"]["login"]
    message = extract_message(issue.get("body") or "")
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = f"| [@{login}](https://github.com/{login}) | {message} | {date} |"

    with open(README, encoding="utf-8") as f:
        readme = f.read()

    head, rest = readme.split(START, 1)
    block, tail = rest.split(END, 1)

    rows = [ln for ln in block.strip().splitlines() if ln.startswith("| [@")]
    rows.insert(0, row)
    rows = rows[:MAX_ENTRIES]

    table = "\n".join(
        ["| Visitor | Note | Stamped |", "|---|---|---|", *rows]
    )
    readme = f"{head}{START}\n{table}\n{END}{tail}"

    with open(README, "w", encoding="utf-8") as f:
        f.write(readme)

    # Hand the cleaned message back to the workflow for the closing comment.
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"message={message}\n")
    print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
