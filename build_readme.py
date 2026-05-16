"""GitHub profile README auto-updater for CHUNSEM.

Inspired by tw93/tw93's build_readme.py. Trimmed to two auto sections:
- `github_stats`: followers + total stars + total forks across owned non-fork repos
- `recent_commits`: latest commits across owned public non-fork repos (drop in
  for tw93's "Latest Releases", since the author ships fewer tagged releases
  and more commit-level progress)

All other content (bio, Now, Featured) is hand-edited between runs.
"""

from __future__ import annotations

import os
import pathlib
import re
from datetime import datetime, timezone

from github import Auth, Github

ROOT = pathlib.Path(__file__).parent.resolve()
TOKEN = os.environ.get("GH_TOKEN", "")
COMMITS_PER_REPO = 3
COMMITS_TOTAL = 6
MSG_MAX_LEN = 60


def replace_chunk(content: str, marker: str, chunk: str, inline: bool = False) -> str:
    pattern = re.compile(
        rf"<!-- {marker} starts -->.*<!-- {marker} ends -->",
        re.DOTALL,
    )
    if not inline:
        chunk = f"\n{chunk}\n"
    return pattern.sub(f"<!-- {marker} starts -->{chunk}<!-- {marker} ends -->", content)


def truncate_middle(text: str, max_len: int = MSG_MAX_LEN) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_len:
        return text
    keep = max_len - 3
    left = (keep + 1) // 2
    right = keep // 2
    return f"{text[:left]}...{text[-right:]}"


def fetch_github_stats(token: str) -> dict[str, int]:
    g = Github(auth=Auth.Token(token))
    user = g.get_user()
    total_stars = 0
    total_forks = 0
    for repo in user.get_repos(type="owner"):
        if repo.fork:
            continue
        total_stars += repo.stargazers_count
        total_forks += repo.forks_count
    return {
        "followers": user.followers,
        "stars": total_stars,
        "forks": total_forks,
    }


def fetch_recent_commits(token: str) -> list[dict]:
    g = Github(auth=Auth.Token(token))
    user = g.get_user()
    commits: list[dict] = []
    for repo in user.get_repos(type="owner"):
        if repo.fork or repo.private:
            continue
        try:
            for commit in list(repo.get_commits())[:COMMITS_PER_REPO]:
                msg = commit.commit.message.split("\n", 1)[0]
                when = commit.commit.author.date
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                commits.append({
                    "repo": repo.name,
                    "repo_url": repo.html_url,
                    "msg": truncate_middle(msg),
                    "url": commit.html_url,
                    "when": when,
                })
        except Exception as exc:
            print(f"[warn] commits for {repo.name}: {exc}")
    commits.sort(key=lambda c: c["when"], reverse=True)
    return commits[:COMMITS_TOTAL]


def render_commits(commits: list[dict]) -> str:
    if not commits:
        return "• 暂无公开活动 — 主仓库 Sensing-lab 当前私库 alpha，公开后会自动同步"
    return "<br>".join(
        f"• [{c['repo']}]({c['repo_url']}) {c['msg']} - {c['when'].strftime('%Y-%m-%d')}"
        for c in commits
    )


def main() -> None:
    if not TOKEN:
        print("[skip] GH_TOKEN not set — README left untouched. "
              "Locally: GH_TOKEN=$(gh auth token) python build_readme.py")
        return
    readme = ROOT / "README.md"
    content = readme.read_text(encoding="utf-8")

    stats = fetch_github_stats(TOKEN)
    stats_text = f"{stats['followers']:,} followers, {stats['stars']:,} stars, {stats['forks']:,} forks"
    content = replace_chunk(content, "github_stats", stats_text, inline=True)

    commits = fetch_recent_commits(TOKEN)
    content = replace_chunk(content, "recent_commits", render_commits(commits))

    readme.write_text(content, encoding="utf-8")
    print(f"[ok] {stats_text} · {len(commits)} commits rendered")


if __name__ == "__main__":
    main()
