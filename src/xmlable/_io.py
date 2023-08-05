"""
Easy file IO for users
- Need to make it obvious when an xml has been overwritten
- Easy parsing from a file
"""

from typing import Any
from termcolor import colored
from lxml.objectify import parse as objectify_parse
from lxml.etree import _ElementTree

from xmlable._utils import typename
from xmlable._xobject import is_xmlified
from xmlable._errors import ErrorTypes


def write_file(file_path: str, tree: _ElementTree):
    print(colored(f"Overwriting {file_path}", "red", attrs=["blink"]))
    with open(file=file_path, mode="wb") as f:
        tree.write(f, xml_declaration=True, encoding="utf-8", pretty_print=True)
    print(colored(f"Complete!", "green", attrs=["blink"]))


def parse_file(cls: type, file_path: str) -> Any:
    """
    Parse a file, validate and produce instance of cls
    INV: cls must be an xmlified class
    """
    if not is_xmlified(cls):
        raise ErrorTypes.NotXmlified(cls)
    with open(file=file_path, mode="r") as f:
        return cls.parse(objectify_parse(f).getroot())  # type: ignore[attr-defined]
