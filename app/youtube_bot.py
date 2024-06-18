import os
import re
from datetime import datetime, timedelta

import yaml
from bs4 import BeautifulSoup
from github import Github, GithubException
from pytube import Channel
import feedparser


class youtube_bot:
    def __init__(self):
        youtube_config_file = os.environ.get("YOUTUBE_CONFIG_FILE")
        access_token = os.environ.get("GALAXY_SOCIAL_BOT_TOKEN")
        repo_name = os.environ.get("REPO")
        self.youtube_bot_path = os.environ.get("YOUTUBE_BOT_PATH", "posts/youtube_bot")

        with open(youtube_config_file, "r") as file:
            self.configs = yaml.safe_load(file)

        g = Github(access_token)
        self.repo = g.get_repo(repo_name)

        self.existing_files = set(
            pr_file.filename
            for pr in self.repo.get_pulls(state="open")
            for pr_file in pr.get_files()
            if pr_file.filename.startswith(self.youtube_bot_path)
        )
        git_tree = self.repo.get_git_tree(self.repo.default_branch, recursive=True)
        self.existing_files.update(
            file.path
            for file in git_tree.tree
            if file.path.startswith(self.youtube_bot_path) and file.path.endswith(".md")
        )

    def create_pr(self):
        now = datetime.now()
        start_date = now.date() - timedelta(days=8)

        branch_name = f"youtube-update-{now.strftime('%Y%m%d%H%M%S')}"
        self.repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=self.repo.get_branch("main").commit.sha,
        )

        youtube_channel_list = self.configs.get("youtube")
        if youtube_channel_list is None:
            raise ValueError("No youtube channel found in the file")
        for youtube_channel in youtube_channel_list:
            if youtube_channel.get("channel") is None:
                raise ValueError(
                    f"No channel url found in the file for {youtube_channel}"
                )
            elif youtube_channel.get("media") is None:
                raise ValueError(f"No media found in the file for {youtube_channel}")
            elif youtube_channel.get("format") is None:
                raise ValueError(f"No format found in the file for {youtube_channel}")
            try:
                channel = Channel(youtube_channel.get("channel"))
                feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel.channel_id}"
                feed_data = feedparser.parse(feed_url)
            except Exception as e:
                print(
                    f"Error in parsing feed of {youtube_channel.get('channel')} youtube channel: {e}"
                )
                continue

            folder = feed_data.feed.title.replace(" ", "_").lower()
            feeds_processed = []
            for entry in feed_data.entries:
                date_entry = (
                    entry.get("published")
                    or entry.get("pubDate")
                    or entry.get("updated")
                )
                date_str = (
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                    if "." in date_entry
                    else "%Y-%m-%dT%H:%M:%S%z"
                )
                published_date = datetime.strptime(date_entry, date_str).date()

                file_name = entry.link.split("/")[-1] or entry.link.split("/")[-2]
                file_name = (
                    file_name.split("?v=")[-1] if "?v=" in file_name else file_name
                )
                file_path = f"{self.youtube_bot_path}/{folder}/{file_name}.md"

                if published_date < start_date:
                    print(f"Skipping as it is older: {file_name}")
                    continue

                if file_path in self.existing_files:
                    print(f"Skipping as file already exists: {file_path} ")
                    continue

                if entry.link is None:
                    print(f"No link found: {file_name}")
                    continue

                print(f"Processing: {file_name}")
                md_config = yaml.dump(
                    {
                        key: youtube_channel[key]
                        for key in ["media", "mentions", "hashtags"]
                        if key in youtube_channel
                    }
                )

                format_string = youtube_channel.get("format")
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
                        elif placeholder == "media_thumbnail":
                            values[placeholder] = (
                                f'![{entry.title}]({entry.media_thumbnail[0]["url"]})'
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
                    message=f"Add {entry.title}",
                    content=md_content,
                    branch=branch_name,
                )

                feeds_processed.append(entry.title)

        try:
            title = (
                f"Update from Youtube input bot since {start_date.strftime('%Y-%m-%d')}"
            )
            feeds_processed_str = "- " + "\n- ".join(feeds_processed)
            body = f"This PR created automatically by youtube bot.\n\Youtube videos processed:\n{feeds_processed_str}"
            self.repo.create_pull(
                title=title,
                body=body,
                base="main",
                head=branch_name,
            )
            print(f"PR created for {branch_name}")
        except GithubException as e:
            self.repo.get_git_ref(f"heads/{branch_name}").delete()
            print(
                f"Error in creating PR: {e.data.get('errors')[0].get('message')}\nRemoving branch {branch_name}"
            )


if __name__ == "__main__":
    youtube_bot_cls = youtube_bot()
    youtube_bot_cls.create_pr()
