import json
import os
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from github import Github

URL = "https://themes.gohugo.io/"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class Repo:
    def __init__(self, name, url, stargazers_count, forks_count, tags, updated_at):
        self.name = name
        self.url = url
        self.stargazers_count = stargazers_count
        self.forks_count = forks_count
        self.tags = tags
        self.updated_at = updated_at

    def to_markdown(self):
        tags = " ".join([f'`{tag}`' for tag in self.tags])
        return f"|[{self.name}]({self.url})|{self.stargazers_count}|{self.forks_count}|{tags}|{self.updated_at}|\n"

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "stargazers_count": self.stargazers_count,
            "forks_count": self.forks_count,
            "tags": self.tags,
            "updated_at": self.updated_at,
        }


def fetch_themes():
    response = requests.get(URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    # body > div.flex.w-full.xl\:w-6xl.h-full.flex-auto.mx-auto > main > ul > li:nth-child(1) > div > a
    themes = soup.select("body > div.flex.w-full.xl\:w-6xl.h-full.flex-auto.mx-auto > main > ul > li > div > a")
    return [urljoin(URL, theme["href"]) for theme in themes if "href" in theme.attrs]


def fetch_theme_details(theme_url):
    response = requests.get(theme_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract GitHub URL
    git_url_elem = soup.select_one(
        "body > div.relative.isolate.overflow-hidden.min-h-screen > div.mx-auto.max-w-7xl.px-6.pt-10.lg\:flex.lg\:px-8 > div.mx-auto.max-w-2xl.lg\:mx-0.lg\:shrink-0.lg\:pt-8 > div.mt-12.flex.items-center.gap-x-3 > a.rounded-md.bg-blue-600.px-3\.5.py-2\.5.text-sm.font-semibold.text-white.shadow-xs.hover\:bg-blue-500.focus-visible\:outline-2.focus-visible\:outline-offset-2.focus-visible\:outline-blue-600"
    )
    git_url = git_url_elem["href"] if git_url_elem else None

    # Extract tags
    tags_elems = soup.select(
        "body > div.relative.isolate.overflow-hidden.min-h-screen > div.mx-auto.max-w-7xl.px-6.pt-10.lg\:flex.lg\:px-8 > div.mx-auto.max-w-2xl.lg\:mx-0.lg\:shrink-0.lg\:pt-8 > div:nth-child(3) > div > dl > div:nth-child(5) > dd > a"
    )
    tags = [tag_elem.get_text(strip=True) for tag_elem in tags_elems]

    return git_url, tags


def fetch_github_repo_info(github, git_url):
    try:
        path_parts = git_url.strip("/").split("/")[-2:]
        owner, repo_name = path_parts[0], path_parts[1]
        repo = github.get_repo(f"{owner}/{repo_name}")
        return {
            "name": repo.name,
            "url": repo.html_url,
            "stargazers_count": repo.stargazers_count,
            "forks_count": repo.forks_count,
            "updated_at": repo.pushed_at.strftime("%Y-%m-%d"),
        }
    except Exception as e:
        print(f"Error fetching GitHub repo info for {git_url}: {e}")
        return None


def main():
    github = Github(GITHUB_TOKEN)
    themes = fetch_themes()
    repos = []

    themes = sorted(themes)
    total_themes = len(themes)
    for idx, theme_url in enumerate(themes):
        git_url, tags = fetch_theme_details(theme_url)
        if not git_url:
            continue

        repo_info = fetch_github_repo_info(github, git_url)
        if not repo_info:
            continue

        repos.append(
            Repo(
                name=repo_info["name"],
                url=repo_info["url"],
                stargazers_count=repo_info["stargazers_count"],
                forks_count=repo_info["forks_count"],
                tags=tags,
                updated_at=repo_info["updated_at"],
            )
        )
        print(f'[{idx}/{total_themes}] {theme_url} is done!')

    # Sort by stars
    repos.sort(key=lambda r: r.stargazers_count, reverse=True)

    # Write to README.md
    with open("README.md", "w", encoding="utf-8") as f:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"# Hugo theme stars\n")
        f.write(f"Update by month (Updated at {now})\n\n")
        f.write("|Name|Stars|Forks|Tags|Updated Date|\n")
        f.write(":---:|:---:|:---:|----|:---:\n")
        for repo in repos:
            f.write(repo.to_markdown())

    # Write to themes.json
    with open("themes.json", "w", encoding="utf-8") as json_file:
        json.dump([repo.to_dict() for repo in repos], json_file, indent=4)


if __name__ == "__main__":
    main()
