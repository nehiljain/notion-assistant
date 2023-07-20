"""Helper functions for the Notion Assistant."""
import json
import os
from typing import List
from typing import Optional

import bs4
import markdown
import pendulum
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from notion_client import Client
from pydantic import BaseModel


load_dotenv()


notion = Client(auth=os.environ["NOTION_TOKEN"])


# Pydantic models


class TextObject(BaseModel):
    """A Notion text object."""

    content: str
    link: Optional[str] = None


class RichTextObject(BaseModel):
    """A Notion rich text object."""

    type: str = "text"
    text: TextObject


class HeadingBlock(BaseModel):
    """A Notion heading block."""

    rich_text: List[RichTextObject]
    color: str = "default"
    is_toggleable: bool = False


class ParagraphBlock(BaseModel):
    """A Notion paragraph block."""

    rich_text: List[RichTextObject] = []
    color: str = "default"
    children: Optional[List["Block"]] = []


class BulletedListItemBlock(BaseModel):
    """A Notion bulleted list item block."""

    rich_text: List[RichTextObject]
    color: str = "default"
    children: Optional[List["Block"]] = []


class NumberedListItemBlock(BaseModel):
    """A Notion numbered list item block."""

    rich_text: List[RichTextObject]
    color: str = "default"
    children: Optional[List["Block"]] = []


class ImageBlock(BaseModel):
    """A Notion image block."""

    external: dict


class Block(BaseModel):
    """A Notion block."""

    type: str
    paragraph: Optional[ParagraphBlock]
    heading_1: Optional[HeadingBlock]
    heading_2: Optional[HeadingBlock]
    heading_3: Optional[HeadingBlock]
    bulleted_list_item: Optional[BulletedListItemBlock]
    numbered_list_item: Optional[NumberedListItemBlock]
    image: Optional[ImageBlock]


class DividerBlock(BaseModel):
    """Divider block."""

    divider: dict = {}


Block.update_forward_refs()

# Block creation functions


def create_text_object(content: str) -> TextObject:
    """Create a text notion object from a string."""
    return TextObject(content=content)


def create_divider_block() -> dict:
    """Create a divider notion block."""
    return {"type": "divider", "divider": {}}


def create_rich_text_object(content: str) -> RichTextObject:
    """Create a rich text notion object from a string."""
    return RichTextObject(text=create_text_object(content))


def create_paragraph_block(tag) -> dict:
    """Create a paragraph notion block from an HTML paragraph tag."""
    text = tag.get_text() if tag else ""
    return {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [create_rich_text_object(text)],
            "children": [],
            "color": "default",
        },
    }


def create_heading_block(tag, level) -> dict:
    """Create a heading notion block from an HTML heading tag."""
    return {
        "type": f"heading_{level}",
        f"heading_{level}": {
            "rich_text": [create_rich_text_object(tag.get_text())],
            "color": "default",
            "is_toggleable": False,
        },
    }


def create_bulleted_list_item_block(tag) -> dict:
    """Create a bulleted list item notion block from an HTML list item tag."""
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [create_rich_text_object(tag.get_text())],
            "color": "default",
            "children": [],
        },
    }


def create_numbered_list_item_block(tag) -> dict:
    """Create a numbered list item notion block from an HTML list item tag."""
    return {
        "type": "numbered_list_item",
        "numbered_list_item": {
            "rich_text": [create_rich_text_object(tag.get_text())],
            "color": "default",
            "children": [],
        },
    }


def create_image_block(tag) -> dict:
    """Create an image notion block from an HTML image tag."""
    return {"type": "image", "image": {"external": {"url": tag["src"]}}}


# Map HTML tags to block creation functions
tag_to_block = {
    "p": create_paragraph_block,
    "h1": lambda tag: create_heading_block(tag, 1),
    "h2": lambda tag: create_heading_block(tag, 2),
    "h3": lambda tag: create_heading_block(tag, 3),
    "li": create_bulleted_list_item_block,
    "img": create_image_block,
    "ol": create_numbered_list_item_block,
}


class PydanticJSONEncoder(json.JSONEncoder):
    """A JSON encoder that can handle Pydantic models."""

    def default(self, obj):
        """Handle Pydantic models."""
        if isinstance(obj, BaseModel):
            return obj.dict()
        return super().default(obj)


def markdown_to_blocks(markdown_text: str) -> str:
    """Convert markdown text to Notion blocks array."""
    html = markdown.markdown(markdown_text)
    soup = BeautifulSoup(html, "html.parser")
    blocks = [create_divider_block()]
    for tag in soup.descendants:  # Use .descendants to include nested tags
        if isinstance(tag, bs4.Tag):  # Make sure the descendant is a tag (not a string)
            if tag.name == "li":
                if tag.parent.name == "ol":
                    create_block = create_numbered_list_item_block
                else:
                    create_block = create_bulleted_list_item_block
            else:
                create_block = tag_to_block.get(tag.name)
            if create_block:
                block = create_block(tag)
                blocks.append(
                    block
                )  # Use append() instead of += [block] for efficiency
    json_blocks = json.loads(json.dumps(blocks, cls=PydanticJSONEncoder))
    return json_blocks


def markdown_to_blocks2(markdown_text: str) -> str:
    """Convert markdown text to Notion blocks array."""
    html = markdown.markdown(markdown_text)
    soup = BeautifulSoup(html, "html.parser")
    blocks = [create_divider_block()]
    for tag in soup:
        if tag.name == "li":
            # Check the parent tag of the list item
            if tag.parent.name == "ol":
                create_block = create_numbered_list_item_block
            else:  # default to unordered list if not in an ordered list
                create_block = create_bulleted_list_item_block
        else:
            create_block = tag_to_block.get(tag.name)

        if create_block:
            block = create_block(tag)
            blocks += [block]
    json_blocks = json.loads(json.dumps(blocks, cls=PydanticJSONEncoder))
    return json_blocks


def append_blocks_to_page(page_id: str, blocks: List[dict]) -> dict:
    """Append blocks to a Notion page with notion sdk/api."""
    for index in range(0, len(blocks), 90):
        notion.blocks.children.append(
            block_id=page_id, children=blocks[index : index + 90]
        )
    return notion.pages.retrieve(page_id=page_id)


def update_refs_property(
    page: dict, property_name: str, titles: List[str], title_to_id: dict
):
    """Update the areas property."""
    prop = page["properties"][property_name]
    try:
        for title in titles:
            ref_id = title_to_id.get(title.strip())
            if ref_id is None:
                raise ValueError(f"No {property_name} found with title {title}")
            prop["relation"].append({"id": ref_id})
            print(f"Updating Areas property with {title}: {page['id']}")
        notion.pages.update(page_id=page["id"], properties={property_name: prop})
    except KeyError:
        print(f"Page does not have Areas property: {page.id} - {page.title}")


def update_is_ai_analysis_done_property(page: dict, page_text: str):
    """Update the is AI analysis done property."""
    try:
        if (
            "AI Analysis".lower() in page_text.lower()
            and "main points".lower() in page_text.lower()
        ):
            page_dict = page
            is_ai_analyzed_prop = page_dict["properties"]["is_ai_analyzed"]
            is_ai_analyzed_prop["checkbox"] = True
            print(f"Updating is_ai_analyzed property: {page_dict['id']}")
            notion.pages.update(
                page_id=page_dict["id"],
                properties={"is_ai_analyzed": is_ai_analyzed_prop},
            )
    except KeyError:
        print(f"Page does not have is_ai_analyzed property: {page.id} - {page.title}")


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
