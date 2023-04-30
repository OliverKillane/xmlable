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
from typing import Any, Generator, dataclass_transform
from lxml.objectify import ObjectifiedElement
from xmlable._utils import get
from xmlable._errors import XErrorCtx, XError

from xmlable._xobject import (
    GNS_POST,
    GNS_PRE,
    XObject,
    gen_xobject,
    indent,
    stringify_mods,
    typename,
)


def validate_class(cls):
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
        ).add_note(f"\nTry:\n@xmlify\n@dataclass\nclass {cls_name}:")

    for reserved in [
        "xsd_forward",
        "xsd_dependencies",
        "get_xobject",
        "xsd",
        "xml",
        "xml_value",
        "parse",
    ]:
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
                self, name: str, depth: int, mods: dict[str, Any] = {}
            ) -> Generator[str, None, None]:
                yield f'{indent(depth)}<{GNS_POST}element name="{name}" type="{cls_name}"{stringify_mods(mods)} />'

            def xml_out(
                self, name: str, depth: int, val: Any, ctx: XErrorCtx
            ) -> Generator[str, None, None]:
                if len(meta_xobjects) > 0:
                    yield f"{indent(depth)}<{name}>"
                    for m, xobj in meta_xobjects:
                        yield from xobj.xml_out(
                            m.name,
                            depth + 1,
                            get(val, m.name),
                            ctx.next(m.name),
                        )
                    yield f"{indent(depth)}</{name}>"
                else:
                    yield f"{indent(depth)}<{name}/>"

            def xml_temp(
                self, name: str, depth: int
            ) -> Generator[str, None, None]:
                if len(meta_xobjects) > 0:
                    yield f"{indent(depth)}<{name}>"
                    for m, xobj in meta_xobjects:
                        yield from xobj.xml_temp(m.name, depth + 1)
                    yield f"{indent(depth)}</{name}>"
                else:
                    yield f"{indent(depth)}<{name}/>"

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

        def xsd_forward(depth: int) -> Generator[str, None, None]:
            yield f'{indent(depth)}<{GNS_POST}complexType name="{cls_name}">'
            yield f"{indent(depth+1)}<{GNS_POST}sequence>"
            for m, xobj in meta_xobjects:
                yield from xobj.xsd_out(m.name, depth + 2, {})
            yield f"{indent(depth+1)}</{GNS_POST}sequence>"
            yield f"{indent(depth)}</{GNS_POST}complexType>"

        def xsd_dependencies() -> set[type]:
            return forward_decs

        def get_xobject():
            return cls_xobject

        def xsd(
            schema_name: str,
            xmlns: str = "http://www.w3.org/2001/XMLSchema",
            options: dict[str, str] = {},
            imports: dict[str, str] = {},
        ) -> Generator[str, None, None]:
            # yield '<?xml version="1.0" encoding="utf-8"?>'
            options_str = "".join(f' {k}="{v}"' for k, v in options.items())
            yield f'<{GNS_POST}schema xmlns{GNS_PRE}="{xmlns}"{options_str}>'
            for ns, schloc in imports.items():
                yield f'{indent(1)}<import namespace="{ns}" schemaLocation="{schloc}"/>'
            yield f""

            visited: set[type] = set()
            dec_order: list[type] = []

            def toposort(curr: type, visited: set[type], dec_order: list[type]):
                visited.add(curr)
                deps = curr.xsd_dependencies()
                for d in deps:
                    if d not in visited:
                        toposort(d, visited, dec_order)
                dec_order.append(curr)

            toposort(cls, visited, dec_order)

            for dec in dec_order:
                yield from dec.xsd_forward(1)
                yield f""

            yield from cls_xobject.xsd_out(schema_name, 1)
            yield f"</{GNS_POST}schema>"

        def xml(schema_name: str) -> Generator[str, None, None]:
            # yield f'<?xml version="1.0" encoding="utf-8"?>'
            yield from cls_xobject.xml_temp(schema_name, 0)

        def xml_value(self, schema_name: str) -> Generator[str, None, None]:
            yield from cls_xobject.xml_out(
                schema_name, 0, self, XErrorCtx([schema_name])
            )

        def parse(obj: ObjectifiedElement) -> Any:
            return cls_xobject.xml_in(obj, XErrorCtx([obj.tag]))

        # helper methods for gen_xobject, and other dataclasses to generate their
        # x methods
        cls.xsd_forward = xsd_forward
        cls.xsd_dependencies = xsd_dependencies
        cls.get_xobject = get_xobject

        # x methods for user
        cls.xsd = xsd
        cls.xml = xml
        setattr(cls, "xml_value", xml_value)  # needs to use self to get values
        cls.parse = parse

        # Mark the class as xmlified
        cls.xmlified = True

        return cls
    except XError as e:
        # NOTE: Trick to remove dirty 'internal' traceback, and raise from
        #       xmlify (makes more sense to user than seeing internals)
        e.__traceback__ = None
        raise e
