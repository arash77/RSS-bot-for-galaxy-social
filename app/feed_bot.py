import os
import re

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser
from utils import utils


def main():
    feed_bot_path = os.environ.get("FEED_BOT_PATH", "posts/feed_bot")
    utils_obj = utils(feed_bot_path, "feeds")

    for feed in utils_obj.list:
        if feed.get("url") is None:
            raise ValueError(f"No url found in the file for feed {feed}")
        try:
            feed_data = feedparser.parse(feed.get("url"))
        except Exception as e:
            print(f"Error in parsing feed {feed.get('url')}: {e}")
            continue

        folder = feed_data.feed.title.replace(" ", "_").lower()
        format_string = feed.get("format")
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
                    print(f"Placeholder {placeholder} not found in entry {entry.title}")
            formatted_text = format_string.format(**values)

            entry_data = {
                "title": entry.title,
                "config": feed,
                "date": published_date,
                "rel_file_path": f"{folder}/{file_name}.md",
                "formatted_text": formatted_text,
            }
            if utils_obj.process_entry(entry_data):
                feeds_processed.append(f"[{entry.title}]({entry.link})")

    if not feeds_processed:
        print("No new feeds found.")
        return

    title = (
        f"Update from feeds input bot since {utils_obj.start_date.strftime('%Y-%m-%d')}"
    )
    feeds_processed_str = "- " + "\n- ".join(feeds_processed)
    body = f"This PR created automatically by feed bot.\n\nFeeds processed:\n{feeds_processed_str}"
    utils_obj.create_pull_request(title, body)


if __name__ == "__main__":
    main()
