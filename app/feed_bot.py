import os
import re
from datetime import datetime

import feedparser
import yaml
from bs4 import BeautifulSoup
from github import Github


class feed_bot:
    def __init__(self):
        feed_file = os.environ.get("FEED_FILE", "app/feeds.yml")
        try:
            with open(feed_file, "r") as file:
                self.configs = yaml.safe_load(file)

        except FileNotFoundError:
            raise FileNotFoundError(f"File {feed_file} not found")

        access_token = os.environ.get("GITHUB_TOKEN")
        g = Github(access_token)
        repo_name = os.environ.get("REPO")
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
        if feed_list is None:
            raise ValueError("No feeds found in the file")
        for feed in feed_list:
            if feed.get("url") is None:
                raise ValueError(f"No url found in the file for feed {feed}")
            elif feed.get("media") is None:
                raise ValueError(f"No media found in the file for feed {feed}")
            elif feed.get("format") is None:
                raise ValueError(f"No format found in the file for feed {feed}")
            try:
                feed_data = feedparser.parse(feed.get("url"))
            except Exception as e:
                print(f"Error in parsing feed {feed.get('url')}: {e}")
                continue
            folder = feed_data.feed.title.replace(" ", "_").lower()
            for entry in feed_data.entries:
                if file_path in self.existing_files:
                    print(f"File {file_path} already exists")
                    continue

                if entry.link is None:
                    print(f"No link found for entry {entry.title}")
                    continue

                sub_folder = entry.link.split("/")[-1] or entry.link.split("/")[-2]
                file_path = f"{self.feed_bot_path}/{folder}/{sub_folder}.md"

                md_config = yaml.dump(
                    {
                        key: feed[key]
                        for key in ["media", "mentions", "hashtags"]
                        if key in feed
                    }
                )

                format_string = feed.get("format")
                placeholders = re.findall(r"{(.*?)}", format_string)
                values = {}
                for placeholder in placeholders:
                    if placeholder in entry:
                        if "<p>" in entry[placeholder]:
                            soup = BeautifulSoup(entry[placeholder], "html.parser")
                            first_paragraph = soup.find("p")
                            values[placeholder] = first_paragraph.get_text().replace(
                                "\n", " "
                            )
                        else:
                            values[placeholder] = entry[placeholder]
                    else:
                        print(
                            f"Placeholder {placeholder} not found in entry {entry.title}"
                        )
                formatted_text = format_string.format(**values)

                md_content = f"---\n{md_config}---\n{formatted_text}"

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
