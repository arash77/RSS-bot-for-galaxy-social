import os
import re
from datetime import datetime, timedelta

from dateutil import parser
from github import Github
from pyzotero import zotero


def check_new_citations(items):
    formatted_citations = []
    format_string = "- {title} on {dateAdded}, By:{creators}"
    for item in items:
        data = item["data"]
        data["creators"] = ", ".join(
            creator.get("lastName") for creator in data.get("creators", [])
        )
        data["dateAdded"] = (
            parser.isoparse(data["dateAdded"]).date() if "dateAdded" in data else ""
        )
        formatted_text = format_string.format(**data)
        formatted_citations.append(formatted_text)

    return "\n".join(formatted_citations)


def create_markdown_file(citations):
    content = f"# New Citations\n\nNew citations have been found. Here are the details:\n\n{citations}"
    with open("new_citations.md", "w") as f:
        f.write(content)


def create_pull_request(repo, branch_name, commit_message, pr_title, pr_body):
    main_branch = repo.get_branch("main")
    repo.create_git_ref(f"refs/heads/{branch_name}", main_branch.commit.sha)
    with open("new_citations.md", "r") as file:
        content = file.read()
    repo.create_file("new_citations.md", commit_message, content, branch=branch_name)
    pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base="main")
    return pr.html_url


def main():
    zot = zotero.Zotero("1732893", "group")
    zot.add_parameters(
        tag=">UseGalaxy.eu || >RNA Workbench || RNA workbench || >ASaiM || >Live EU || >Proteomics EU || >Metagenomics EU || >ML Workbench || >ChemicalToolbox",
    )

    last_check = os.environ.get("LAST_CHECK_DATE")
    if last_check:
        last_check = parser.isoparse(last_check)
    else:
        last_check = datetime.now() - timedelta(days=7)

    items = zot.everything(zot.top())
    new_items = [
        item
        for item in items
        if parser.isoparse(item["data"]["dateAdded"]).date() > last_check.date()
    ]
    if not new_items:
        print("No new citations found.")
        return

    new_citations = check_new_citations(new_items)

    create_markdown_file(new_citations)
    # g = Github(os.environ["GITHUB_TOKEN"])
    # repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    # branch_name = f"new-citations-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    # commit_message = "Add new citations"
    # pr_title = "New Citations Found"
    # pr_body = "New citations have been detected by the automated system. Please review the changes and merge if appropriate."
    # pr_url = create_pull_request(
    #     repo, branch_name, commit_message, pr_title, pr_body
    # )

    # print(f"Pull request created: {pr_url}")
    os.environ["LAST_CHECK_DATE"] = datetime.now().isoformat()


if __name__ == "__main__":
    main()
