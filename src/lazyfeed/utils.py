import io
import xml.etree.ElementTree as ET
from rich.console import Console
from lazyfeed.models import Feed
from lazyfeed.settings import APP_NAME

console = Console(emoji=True)


def export_opml(feeds: list[Feed]):
    """
    Export a list of RSS feeds into an OPML formatted string.
    """

    opml = ET.Element("opml", version="1.0")

    head = ET.SubElement(opml, "head")
    title = ET.SubElement(head, "title")
    title.text = f"RSS feeds from {APP_NAME}"
    body = ET.SubElement(opml, "body")

    for feed in feeds:
        ET.SubElement(
            body,
            "outline",
            text=feed.title,
            type="rss",
            xmlUrl=feed.url,
        )

    tree = ET.ElementTree(opml)
    output_buffer = io.BytesIO()

    tree.write(output_buffer, encoding="utf-8", xml_declaration=True)

    opml_output = output_buffer.getvalue().decode("utf-8")
    output_buffer.close()

    return opml_output


def import_opml(input: str) -> list[str]:
    """
    Import RSS feeds from an OPML formatted string.
    """

    feeds = []

    root = ET.fromstring(input)
    for outline in root.findall(".//outline"):
        xml_url = outline.get("xmlUrl")
        if xml_url:
            feeds.append(xml_url)

    return feeds
