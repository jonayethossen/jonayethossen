#!/usr/bin/env python3
"""
Fetches real, live stats from the GitHub public API for a given user and
rewrites the block between <!--STATS:START--> and <!--STATS:END--> in
README.md. Designed to run inside a GitHub Actions workflow using the
built-in GITHUB_TOKEN, so it is never rate-limited the way the shared
github-readme-stats.vercel.app demo instance is.
"""

import os
import re
import sys
import requests

USERNAME = os.environ.get("GH_USERNAME", "jonayethossen")
TOKEN = os.environ.get("GITHUB_TOKEN")
README_PATH = os.environ.get("README_PATH", "README.md")

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

LANGUAGE_COLORS = {
    "JavaScript": "F7DF1E",
    "TypeScript": "3178C6",
    "Python": "3776AB",
    "HTML": "E34F26",
    "CSS": "1572B6",
    "Java": "007396",
    "PHP": "777BB4",
    "C++": "00599C",
    "C": "A8B9CC",
    "Go": "00ADD8",
    "Ruby": "CC342D",
}
DEFAULT_COLOR = "6e7681"


def fetch_all_repos(username):
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def fetch_followers(username):
    resp = requests.get(
        f"https://api.github.com/users/{username}", headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("followers", 0)


def build_stats_block(username):
    repos = fetch_all_repos(username)
    followers = fetch_followers(username)

    non_fork_repos = [r for r in repos if not r.get("fork")]
    total_repos = len(repos)
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)

    lang_counts = {}
    for r in non_fork_repos:
        lang = r.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    top_langs = sorted(lang_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

    lang_badges = "\n".join(
        f'<img src="https://img.shields.io/badge/{lang.replace(" ", "_")}-{count}_repos-'
        f'{LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)}?style=flat-square" />'
        for lang, count in top_langs
    )

    block = f"""<p align="center">
<img src="https://img.shields.io/badge/Public_Repos-{total_repos}-2ea44f?style=for-the-badge&logo=github&logoColor=white" />
<img src="https://img.shields.io/badge/Total_Stars-{total_stars}-yellow?style=for-the-badge&logo=github&logoColor=white" />
<img src="https://img.shields.io/badge/Followers-{followers}-blue?style=for-the-badge&logo=github&logoColor=white" />
</p>

**Most Used Languages** (by repository count)

<p align="center">
{lang_badges}
</p>"""
    return block


def update_readme(block):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"<!--STATS:START-->.*?<!--STATS:END-->", re.DOTALL
    )
    new_content = pattern.sub(
        f"<!--STATS:START-->\n{block}\n<!--STATS:END-->", content
    )

    if new_content == content:
        print("No changes to README (stats already up to date, or markers not found).")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    block = build_stats_block(USERNAME)
    changed = update_readme(block)
    if changed:
        print("README.md updated with fresh stats.")
    sys.exit(0)


if __name__ == "__main__":
    main()
