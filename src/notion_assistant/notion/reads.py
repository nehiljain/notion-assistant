"""Functions for the Notion Assistant."""
import os
from typing import List
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from notion2md.exporter.block import StringExporter
from notion_client import Client
from notion_client.helpers import iterate_paginated_api
from pydantic import BaseModel
from thefuzz import fuzz
from tqdm import tqdm

from src.notion_assistant.notion.extractions import extract_raw_page_attributes


load_dotenv()
notion = Client(auth=os.environ["NOTION_TOKEN"])


class Database(BaseModel):
    """Database model."""

    id: str
    title: Optional[str]


def get_non_ai_analyzed_pages(database_id: str) -> List[dict]:
    """Get all the pages that are not AI analyzed."""
    return [
        page
        for block in tqdm(
            iterate_paginated_api(
                notion.databases.query,
                database_id=database_id,
                filter={"property": "is_ai_analyzed", "checkbox": {"equals": False}},
            )
        )
        for page in block
    ]


def get_all_pages_for_database(database_id: str) -> List[dict]:
    """Get all the pages that are not AI analyzed."""
    return (
        page
        for block in iterate_paginated_api(
            notion.databases.query, database_id=database_id
        )
        for page in block
    )


def get_all_page_content_as_text(page_id: str) -> str:
    """Get all the content of a page as text by fetching the child blocks."""
    return StringExporter(block_id=page_id).export()


def get_all_database_ids():
    """Get all database ids."""
    database_collection = []
    db_filter = {"value": "database", "property": "object"}
    bad_database_collection = []
    for block in tqdm(iterate_paginated_api(notion.search, filter=db_filter)):
        for database in block:
            try:
                database_collection += [
                    Database(
                        id=database["id"], title=database["title"][0]["plain_text"]
                    )
                ]
            except (IndexError, KeyError) as error:
                print(error)
                print(f"Database is faulty: {database['id'].replace('-', '')}")
                bad_database_collection += [
                    Database(id=database["id"].replace("-", ""))
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


def get_database_as_df(db_id):
    """Get the database as a dataframe."""
    return pd.DataFrame(
        [
            extract_raw_page_attributes(data).dict()
            for data in get_all_pages_for_database(db_id)
        ]
    )


def get_page_titles(df: pd.DataFrame) -> set:
    """Return a set of all unique page titles in the DataFrame."""
    return df["title"].unique()


def get_ref_title_to_id_mapping(db_id: str) -> dict:
    """Create a mapping of area titles to their IDs."""
    area_df = pd.DataFrame(
        [
            extract_raw_page_attributes(data).dict()
            for data in get_all_pages_for_database(db_id)
        ]
    )
    return {
        row["raw_data"]["properties"]["Name"]["title"][0]["plain_text"]: row["id"]
        for _, row in area_df.iterrows()
    }
