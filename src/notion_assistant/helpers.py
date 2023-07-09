"""Helper functions for the Notion Assistant."""
import os
import time
from collections import namedtuple

import pendulum
import requests
from notion_client import Client
from notion_client.helpers import iterate_paginated_api
from thefuzz import fuzz
from tqdm import tqdm


notion = Client(auth=os.environ["NOTION_TOKEN"])

Database = namedtuple("Database", ["id", "title"])
Page = namedtuple("Page", ["url", "id", "title"])


def get_all_pages_for_database(database_id: str):
    """Get all the pages for a database."""
    page_collection = []
    for block in tqdm(
        iterate_paginated_api(notion.databases.query, database_id=database_id)
    ):
        for page in block:
            try:
                page_collection += [
                    Page(
                        page["url"],
                        page["id"],
                        page["properties"]["Name"]["title"][0]["plain_text"],
                    )
                ]
            except (IndexError, KeyError):
                if (
                    page["properties"].get("Title")
                    and len(page["properties"]["Title"]["title"]) > 0
                ):
                    page_collection += [
                        Page(
                            page["url"],
                            page["id"].replace("-", ""),
                            page["properties"]["Title"]["title"][0]["plain_text"],
                        )
                    ]
                else:
                    print(f"Page is faulty: {page['id'].replace('-', '')}")
    return page_collection


def get_all_page_content_as_text(page_id: str) -> str:
    """Get all the content of a page as text by fetching the child blocks."""
    result_content = ""
    blocks = iterate_paginated_api(notion.blocks.children.list, block_id=page_id)
    for blocks_page in blocks:
        for block in blocks_page:
            for item in [
                "paragraph",
                "heading_1",
                "heading_2",
                "heading_3",
                "toggle",
                "m",
            ]:
                if item in block and "rich_text" in block[item]:
                    plain_text_list = [
                        text["plain_text"] for text in block[item]["rich_text"]
                    ]
                    result_content += "\n\n".join(plain_text_list)

    return result_content


def filter_pages_with_no_ai_analysis_content(pages: list[Page]):
    """Filter the pages that dont have AI analysis content."""
    pages_without_ai_analysis = []
    for page in tqdm(pages[:20]):
        page_content = get_all_page_content_as_text(page.id)
        if (
            "AI Analysis".lower() not in page_content.lower()
            and "main points".lower() not in page_content.lower()
        ):
            pages_without_ai_analysis += [page]
    return pages_without_ai_analysis


def update_notion_database_with_parent_name(database):
    """Update the database with the parent name."""
    try:
        tnow = pendulum.now().to_datetime_string()
        parent_page = notion.pages.retrieve(page_id=database["parent"]["page_id"])
        parent_page_title = parent_page["properties"]["Title"]["title"][0]["plain_text"]

        title_block = [{"text": {"content": f"{parent_page_title}-{tnow}"}}]
        notion.databases.update(database_id=database["id"], title=title_block)
        return database["id"]

    except (IndexError, KeyError):
        return None


def get_all_database_ids():
    """Get all database ids."""
    database_collection = []
    db_filter = {"value": "database", "property": "object"}
    bad_database_collection = []
    for block in tqdm(iterate_paginated_api(notion.search, filter=db_filter)):
        for database in block:
            try:
                database_collection += [
                    Database(database["id"], database["title"][0]["plain_text"])
                ]
            except (IndexError, KeyError) as error:
                print(error)
                print(f"Database is faulty: {database['id'].replace('-', '')}")
                if update_notion_database_with_parent_name(database):
                    bad_database_collection += [
                        Database(database["id"].replace("-", ""), None)
                    ]
    return database_collection, bad_database_collection


def filter_database_on_name(database_collection: list[Database], name: str):
    """Filter the database on name using fuzzy matching."""
    db_fuzz = [
        database
        for database in database_collection
        if fuzz.partial_ratio(database.title.lower(), name.lower()) > 90
    ]
    print(f"Total number of databases that are accurate: {len(db_fuzz)} {db_fuzz}")
    return db_fuzz[0]


def trigger_pipedream_for_pages(pages: list[Page]):
    """Trigger Pipedream for each page in pages list."""
    url = "https://eo47mn7edy2ug3b.m.pipedream.net"
    for page in pages:
        print(f"Triggering Pipedream for page: {page.title}, {page.id}")
        data = {"page_id": page.id}

        _ = requests.post(url, json=data)
        time.sleep(120)


if __name__ == "__main__":
    db, bdbs = get_all_database_ids()
    print(f"Total number of databases that are accurate: {len(db)}")
    # print(db)
    # print(f"Total number of databases that are faulty: {len(bdbs)}")
    # print(bdbs)
    vault_db = filter_database_on_name(db, "library")
    all_vault_pages = get_all_pages_for_database(vault_db.id)
    print(f"Total number of pages in vault: {len(all_vault_pages)}")
    pages_to_trigger = filter_pages_with_no_ai_analysis_content(all_vault_pages)
    print(f"Total number of pages that need analysis: {len(pages_to_trigger)}")
    print("Triggerin pipedream via http")
    trigger_pipedream_for_pages(pages_to_trigger)

# TODO: Find all the untitled pages and find a heuristic to name them
# TODO: Find all the pages that have the same name and union them
# TODO Figure out how to solve for max token lenght
