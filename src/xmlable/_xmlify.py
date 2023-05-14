""" XMLable
A decorator to allow creation of xml config based on python dataclasses

Given a dataclass:
- Produce an xsd schema based on the class
- Produce an xml template based on the class
- Given any instance of the class, make a best-effort attempt at turning it into
  a filled xml
- Create a parser for parsing the xml
"""

from dataclasses import fields, is_dataclass
from typing import Any, dataclass_transform
from lxml.objectify import ObjectifiedElement
from lxml.etree import Element, _Element
from xmlable._utils import get
from xmlable._errors import XErrorCtx, XError
from xmlable._manual import manual_xmlify

from xmlable._utils import typename
from xmlable._lxml_helpers import with_children, with_child, XMLSchema
from xmlable._xobject import XObject, gen_xobject


def validate_class(cls: type):
    """
    Validate tha the class can be xmlified
    - Must be a dataclass
    - Cannot have any members called 'comment' (lxml parses comments as this tag)
    - Cannot have
    """
    cls_name = typename(cls)
    if not is_dataclass(cls):
        raise XError(
            short="Non-Dataclass",
            what=f"{cls_name} is not a dataclass",
            why=f"xmlify uses dataclasses to get fields",
            ctx=XErrorCtx([cls_name]),
            notes=[f"\nTry:\n@xmlify\n@dataclass\nclass {cls_name}:"],
        )

    reserved_attrs = [
        "xsd_forward",
        "xsd_dependencies",
        "get_xobject",
        "xsd",
        "xml",
        "xml_value",
        "parse",
    ]

    # TODO: cleanup repetition
    for f in fields(cls):
        if f.name in reserved_attrs:
            raise XError(
                short=f"Reserved Attribute",
                what=f"{cls_name}.{f.name} is used by xmlify, so it cannot be a field of the class",
                why=f"xmlify aguments {cls_name} by adding methods it can then use for xsd, xml generation and parsing",
                ctx=XErrorCtx([cls_name]),
            )
        elif f.name == "comment":
            raise XError(
                short=f"Comment Attribute",
                what=f"xmlifed classes cannot use comment as an attribute",
                why=f"comment is used as a tag name for comments by lxml, so comments inserted on xml generation could conflict",
                ctx=XErrorCtx([cls_name]),
            )

    for reserved in reserved_attrs:
        if hasattr(cls, reserved):
            raise XError(
                short=f"Reserved Attribute",
                what=f"{cls_name}.{reserved} is used by xmlify, so it cannot be a normal attribute of the class",
                why=f"xmlify aguments {cls_name} by adding methods it can then use for xsd, xml generation and parsing",
                ctx=XErrorCtx([cls_name]),
            )
    if hasattr(cls, "comment"):
        raise XError(
            short=f"Comment Attribute",
            what=f"xmlifed classes cannot use comment as an attribute",
            why=f"comment is used as a tag name for comments by lxml, so comments inserted on xml generation could conflict",
            ctx=XErrorCtx([cls_name]),
        )


@dataclass_transform()
def xmlify(cls: type) -> type:
    try:
        validate_class(cls)

        cls_name = typename(cls)
        forward_decs = {cls}
        meta_xobjects = [
            (f, gen_xobject(f.type, forward_decs)) for f in fields(cls)
        ]

        class UserXObject(XObject):
            def xsd_out(
                self,
                name: str,
                attribs: dict[str, str] = {},
                add_ns: dict[str, str] = {},
            ) -> _Element:
                return Element(
                    f"{XMLSchema}element",
                    name=name,
                    type=cls_name,
                    attrib=attribs,
                )

            def xml_temp(self, name: str) -> _Element:
                return with_children(
                    Element(name),
                    [xobj.xml_temp(m.name) for m, xobj in meta_xobjects],
                )

            def xml_out(self, name: str, val: Any, ctx: XErrorCtx) -> _Element:
                return with_children(
                    Element(name),
                    [
                        xobj.xml_out(
                            m.name,
                            get(val, m.name),
                            ctx.next(m.name),
                        )
                        for m, xobj in meta_xobjects
                    ],
                )

            def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
                parsed: dict[str, Any] = {}
                for m, xobj in meta_xobjects:
                    if (m_obj := get(obj, m.name)) is not None:
                        parsed[m.name] = xobj.xml_in(m_obj, ctx.next(m.name))
                    else:
                        raise XError(
                            short="Non member tag",
                            what=f"In {obj.tag} {cls_name}.{m.name} could not be found.",
                            why=f"All members, including {cls_name}.{m.name} must be present",
                            ctx=ctx,
                        )
                return cls(**parsed)

        cls_xobject = UserXObject()

        def xsd_forward(add_ns: dict[str, str]) -> _Element:
            return with_child(
                Element(f"{XMLSchema}complexType", name=cls_name),
                with_children(
                    Element(f"{XMLSchema}sequence"),
                    [
                        xobj.xsd_out(m.name, attribs={}, add_ns=add_ns)
                        for m, xobj in meta_xobjects
                    ],
                ),
            )

        def xsd_dependencies() -> set[type]:
            return forward_decs

        def get_xobject():
            return cls_xobject

        # helper methods for gen_xobject, and other dataclasses to generate their
        # x methods
        cls.xsd_forward = xsd_forward  # type: ignore[attr-defined]
        cls.xsd_dependencies = xsd_dependencies  # type: ignore[attr-defined]
        cls.get_xobject = get_xobject  # type: ignore[attr-defined]

        return manual_xmlify(cls)
    except XError as e:
        # NOTE: Trick to remove dirty 'internal' traceback, and raise from
        #       xmlify (makes more sense to user than seeing internals)
        e.__traceback__ = None
        raise e
