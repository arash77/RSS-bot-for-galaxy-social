import os
import re

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser
from pytube import Channel
from utils import utils


def main():
    youtube_bot_path = os.environ.get("YOUTUBE_BOT_PATH", "posts/youtube_bot")
    utils_obj = utils(youtube_bot_path, "youtube_channels")

    for youtube_channel in utils_obj.list:
        if youtube_channel.get("channel") is None:
            raise ValueError(f"No channel url found in the file for {youtube_channel}")
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
        format_string = youtube_channel.get("format")
        placeholders = re.findall(r"{(.*?)}", format_string)
        feeds_processed = []
        for entry in feed_data.entries:
            date_entry = (
                entry.get("published") or entry.get("pubDate") or entry.get("updated")
            )
            published_date = parser.isoparse(date_entry).date()

            if entry.link is None:
                print(f"No link found: {entry.title}")
                continue

            file_name = entry.link.split("/")[-1] or entry.link.split("/")[-2]
            file_name = file_name.split("?v=")[-1] if "?v=" in file_name else file_name

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
                    print(f"Placeholder {placeholder} not found in entry {entry.title}")
            formatted_text = format_string.format(**values)

            entry_data = {
                "title": entry.title,
                "config": youtube_channel,
                "date": published_date,
                "rel_file_path": f"{folder}/{file_name}.md",
                "formatted_text": formatted_text,
            }
            if utils_obj.process_entry(entry_data):
                feeds_processed.append(f"[{entry.title}]({entry.link})")

    if not feeds_processed:
        print("No new youtube video found.")
        return

    title = f"Update from Youtube input bot since {utils_obj.start_date.strftime('%Y-%m-%d')}"
    feeds_processed_str = "- " + "\n- ".join(feeds_processed)
    body = f"This PR created automatically by youtube bot.\nYoutube videos processed:\n{feeds_processed_str}"
    utils_obj.create_pull_request(title, body)


if __name__ == "__main__":
    main()
