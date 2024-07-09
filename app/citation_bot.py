import os

from dateutil import parser
from pyzotero import zotero
from utils import utils


def create_pull_request(repo, branch_name, commit_message, pr_title, pr_body):
    main_branch = repo.get_branch("main")
    repo.create_git_ref(f"refs/heads/{branch_name}", main_branch.commit.sha)
    with open("new_citations.md", "r") as file:
        content = file.read()
    repo.create_file("new_citations.md", commit_message, content, branch=branch_name)
    pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base="main")
    return pr.html_url


def main():
    citation_bot_path = os.environ.get("CITATION_BOT_PATH", "posts/citation_bot")
    utils_obj = utils(citation_bot_path, "citations")

    for citation in utils_obj.list:
        if citation.get("zotero_group_id") is None:
            raise ValueError(
                f"No zotero group id found in the file for citation {citation}"
            )
        try:
            zot = zotero.Zotero(citation.get("zotero_group_id"), "group")
            if citation.get("tag"):
                zot.add_parameters(tag=citation.get("tag"))
            items = zot.everything(zot.top())
        except Exception as e:
            print(
                f"Error in connecting to zotero group {citation.get('zotero_group_id')}: {e}"
            )
            continue

        new_items = [
            item
            for item in items
            if parser.isoparse(item["data"]["dateAdded"]).date() > utils_obj.start_date
        ]
        if not new_items:
            print("No new citations found.")
            return

        folder = citation.get("zotero_group_id")
        format_string = citation.get("format")
        entry_processed = []

        for item in new_items:
            data = item["data"]
            data["creators"] = ", ".join(
                creator.get("lastName", "") for creator in data.get("creators", [])
            )
            data["dateAdded"] = (
                parser.isoparse(data["dateAdded"]).date() if "dateAdded" in data else ""
            )
            formatted_text = format_string.format(**data)

            entry_data = {
                "title": data["title"],
                "config": citation,
                "date": data["dateAdded"],
                "rel_file_path": f"{folder}/{item['key']}.md",
                "formatted_text": formatted_text,
            }
            if utils_obj.process_entry(entry_data):
                entry_processed.append(data["title"])

    if not entry_processed:
        print("No new citation found.")
        return

    title = f"Update from citation input bot since {utils_obj.start_date.strftime('%Y-%m-%d')}"
    entry_processed_str = "- " + "\n- ".join(entry_processed)
    body = f"This PR created automatically by citation bot.\n\nCitations processed:\n{entry_processed_str}"
    utils_obj.create_pull_request(title, body)


if __name__ == "__main__":
    main()
