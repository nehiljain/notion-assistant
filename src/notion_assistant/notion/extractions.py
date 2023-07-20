"""Helper functions for the Notion Assistant."""
from datetime import datetime
from typing import Optional

import pandas as pd
from notion2md.exporter.block import StringExporter
from pydantic import BaseModel
from pydantic import Field


def extract_id(data: dict) -> str:
    """Extract the id from the data."""
    return data["id"]


def extract_stars(data: dict) -> Optional[str]:
    """Extract the stars from the data."""
    future_value_rank = data["properties"].get("Future Value Rank", {}).get("select")
    return future_value_rank.get("name") if future_value_rank else None


def extract_project_name(data: dict) -> Optional[str]:
    """Extract the project name from the data."""
    related_projects = (
        data["properties"]
        .get("Related to Projects Database (Related to Media Vault (Property))", {})
        .get("relation")
    )
    projects = data["properties"].get("Projects", {}).get("relation")

    # If there are related_projects or projects,
    # retrieve the first one's name. If not, default to None.
    project_name = None
    if related_projects:
        project_name = related_projects[0].get("name") if related_projects[0] else None
    elif projects:
        project_name = projects[0].get("name") if projects[0] else None

    return project_name


def extract_is_archived(data: dict) -> bool:
    """Extract the is archived property from the data."""
    return data["archived"]


def extract_created_at(data: dict) -> datetime:
    """Extract the created at datetime from the data."""
    created_time = data.get("created_time") or data.get("properties", {}).get(
        "created_at", {}
    ).get("created_time")
    return (
        datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        if created_time
        else None
    )


def extract_last_updated_at(data: dict) -> datetime:
    """Extract the last updated at datetime from the data."""
    last_edited_time = data.get("last_edited_time") or data.get("properties", {}).get(
        "updated_at", {}
    ).get("last_edited_time")
    return (
        datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))
        if last_edited_time
        else None
    )


def extract_title(data: dict) -> str:
    """Extract the title from the data."""
    title_data = data["properties"].get("Title") or data["properties"].get("Name")
    return (
        title_data["title"][0]["plain_text"]
        if title_data and title_data.get("title")
        else None
    )


def extract_num_highlights(data: dict) -> int:
    """Extract the number of highlights from the data."""
    highlights = data["properties"].get("Highlights", {})
    return (
        int(highlights.get("number", 0))
        if highlights and highlights.get("number") is not None
        else 0
    )


def extract_url(data: dict) -> str:
    """Extract the Notion URL from the data."""
    return data["url"]


def extract_external_url(data: dict) -> Optional[str]:
    """Extract the external URL from the data."""
    url_property = data["properties"].get("URL", {})
    return url_property.get("url") if url_property else None


class NotionDbPage(BaseModel):
    """A Notion page based on Notion database."""

    id: str = Field(description="id of the page")
    raw_data: dict = Field(description="raw data of the page")
    url: str = Field(description="Notion URL of the page")


class AreaPage(BaseModel):
    """A Notion page based on Notion database."""

    id: str = Field(description="id of the page")
    markdown_content: Optional[str] = Field(description="Markdown content of the page")
    created_at: datetime = Field(description="Created at datetime of the page")
    updated_at: datetime = Field(description="Updated at datetime of the page")
    title: str = Field(description="Title of the page")
    url: str = Field(description="Notion URL of the page")


class ParaPage(BaseModel):
    """A Notion page based on PARA system."""

    id: str = Field(description="id of the page")
    stars: Optional[str] = Field(description="Future value rank of the page")
    project_name: Optional[str] = Field(
        description="Project name of the page in the relationship to projects database"
    )
    is_archived: bool = Field(description="Is the page archived property")
    markdown_content: Optional[str] = Field(description="Markdown content of the page")
    created_at: datetime = Field(description="Created at datetime of the page")
    last_updated_at: datetime = Field(
        description="Last updated at datetime of the page"
    )
    title: str = Field(description="Title of the page")
    num_highlights: int = Field(description="Number of highlights in the page")
    url: str = Field(description="Notion URL of the page")
    external_url: Optional[str] = Field(
        description="External URL of the page from the source where it was clipped from"
    )


def extract_para_page_attributes(data: dict) -> ParaPage:
    """Extract page attributes from the data."""
    return ParaPage(
        id=extract_id(data),
        stars=extract_stars(data),
        project_name=extract_project_name(data),
        is_archived=extract_is_archived(data),
        markdown_content=StringExporter(block_id=extract_id(data)).export(),
        created_at=extract_created_at(data),
        last_updated_at=extract_last_updated_at(data),
        title=extract_title(data),
        num_highlights=extract_num_highlights(data),
        url=extract_url(data),
        external_url=extract_external_url(data),
    )


def extract_area_page_attributes(data: dict) -> AreaPage:
    """Extract page attributes from the data."""
    return AreaPage(
        id=extract_id(data),
        markdown_content=StringExporter(block_id=extract_id(data)).export(),
        created_at=extract_created_at(data),
        updated_at=extract_last_updated_at(data),
        title=extract_title(data),
        url=extract_url(data),
    )


def extract_raw_page_attributes(data: dict) -> NotionDbPage:
    """Extract raw page attributes from the data."""
    return NotionDbPage(id=extract_id(data), raw_data=data, url=extract_url(data))


def get_page_titles(df: pd.DataFrame) -> set:
    """Return a set of all unique page titles in the DataFrame."""
    return df["title"].unique()
