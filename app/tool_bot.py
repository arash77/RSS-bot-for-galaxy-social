import os
import re

import requests
from bs4 import BeautifulSoup
from dateutil import parser
from utils import utils


def main():
    bot_path = os.environ.get("TOOL_BOT_PATH", "posts/tool_bot")
    config_name = "tools"
    utils_obj = utils(bot_path, config_name)

    for config in utils_obj.list:
        if config.get("url") is None:
            raise ValueError(f"No url found in the file for tool api: {config}")
        try:
            data = requests.get(config.get("url") + "/api/tools").json()
            items = {
                section.get("name"): section.get("elems")
                for section in data
                if section.get("model_class") == "ToolSection"
            }
        except Exception as e:
            print(f"Error in parsing tools {config.get('url')}: {e}")
            continue

        folder = config.get("url").split("//")[-1]
        format_string = config.get("format")
        processed = []

        for key, value in items:
            for item in value:
                if item.get("model_class") == "ToolSectionLabel":
                    continue
                # if it is new

                tool_id = (
                    item["id"].split("/")[-2]
                    if "toolshed" in item["id"]
                    else item["id"]
                )
                item["link"] = f"{config.get('url')}/root?tool_id={tool_id}"

                formatted_text = format_string.format(**item)

                file_name = tool_id
                entry_data = {
                    "title": item.get("name"),
                    "config": config,
                    "date": utils_obj.start_date,
                    "rel_file_path": f"{folder}/{file_name}.md",
                    "formatted_text": formatted_text,
                }
                if utils_obj.process_entry(entry_data):
                    processed.append(f"[{item.get('name')}]({item.get('link')})")

    title = (
        f"Update from tools input bot since {utils_obj.start_date.strftime('%Y-%m-%d')}"
    )
    processed_str = "- " + "\n- ".join(processed)
    body = f"This PR created automatically by tools bot.\n\nTools processed:\n{processed_str}"
    utils_obj.create_pull_request(title, body)


if __name__ == "__main__":
    main()
