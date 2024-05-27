import os
from datetime import datetime

import feedparser
import yaml
from bs4 import BeautifulSoup
from github import Github


class feed_bot:
    def __init__(self):
        feed_file = os.path.join("app", os.environ.get("FEED_FILE", "feeds.yml"))
        try:
            with open(feed_file, "r") as file:
                self.configs = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"File {feed_file} not found")

        access_token = os.environ.get("GITHUB_TOKEN")
        g = Github(access_token)
        repo_name = os.environ.get("REPO", "arash77/galaxy-social")
        self.repo = g.get_repo(repo_name)

        self.feed_bot_path = "posts/feed_bot"

        self.existing_files = set(
            pr_file.filename
            for pr in self.repo.get_pulls(state="all")
            for pr_file in pr.get_files()
            if pr_file.filename.startswith(self.feed_bot_path)
        )

    def create_pr(self):
        branch_name = f"feed-update-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=self.repo.get_branch("main").commit.sha,
        )

        feed_list = self.configs.get("feeds")
        for feed in feed_list:
            try:
                feed_data = feedparser.parse(feed)
            except Exception as e:
                print(f"Error in parsing feed {feed}: {e}")
                continue
            folder = feed_data.feed.title.replace(" ", "_").lower()
            for entry in feed_data.entries:
                sub_folder = entry.link.split("/")[-1] or entry.link.split("/")[-2]
                file_path = f"{self.feed_bot_path}/{folder}/{sub_folder}.md"

                if file_path in self.existing_files:
                    continue

                medias = "\n".join(
                    [f"  - {media}" for media in self.configs.get("media")]
                )

                summary = BeautifulSoup(entry.summary, "html.parser")
                if entry.summary == entry.content[0].value:
                    print(f"Entry {entry.title} has no summary")
                    try:
                        summary = summary.find("p")
                    except:
                        summary = ""

                summary = summary.get_text(strip=True).replace("\n", " ")
                md_content = f"---\nmedia:\n{medias}\n---\n{entry.title}\n{summary}\n\nRead more: {entry.link}\n"

                self.repo.create_file(
                    path=file_path,
                    message=f"Add {entry.title} to feed",
                    content=md_content,
                    branch=branch_name,
                )

        try:
            self.repo.create_pull(
                title="Update from feeds",
                body="This PR created automatically by feed bot.",
                base="main",
                head=branch_name,
            )
        except Exception as e:
            self.repo.get_git_ref(f"heads/{branch_name}").delete()
            print(f"Error in creating PR: {e}")


if __name__ == "__main__":
    feed_bot_cls = feed_bot()
    feed_bot_cls.create_pr()
