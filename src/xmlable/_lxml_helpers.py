"""
Helper functions for wrangling to lxml library
- Includes the XMLSchema used
"""

from lxml.objectify import ObjectifiedElement
from lxml.etree import _Element
from typing import Iterable

XMLURL = r"http://www.w3.org/2001/XMLSchema"
XMLSchema = r"{http://www.w3.org/2001/XMLSchema}"


def with_text(e: _Element, text: str) -> _Element:
    e.text = text
    return e


def with_children(parent: _Element, children: Iterable[_Element]) -> _Element:
    for child in children:
        parent.append(child)
    return parent


def with_child(parent: _Element, child: _Element) -> _Element:
    return with_children(parent, [child])


def children(obj: ObjectifiedElement) -> Iterable[ObjectifiedElement]:
    def not_comment(child_obj: ObjectifiedElement):
        return child_obj.tag != "comment"

    return filter(not_comment, obj.getchildren())  # type: ignore[arg-type, operator]
