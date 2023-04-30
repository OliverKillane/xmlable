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

from xmlable._xobject import (
    GNS_POST,
    GNS_PRE,
    XObject,
    gen_xobject,
    indent,
    stringify_mods,
    typename,
)


@dataclass_transform()
def xmlify(cls: type) -> type:
    if not is_dataclass(cls):
        assert False, "must be a dataclass"

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
            self, name: str, depth: int, val: Any
        ) -> Generator[str, None, None]:
            if len(meta_xobjects) > 0:
                yield f"{indent(depth)}<{name}>"
                for m, xobj in meta_xobjects:
                    yield from xobj.xml_out(m.name, depth + 1, get(val, m.name))
                yield f"{indent(depth)}</{name}>"
            else:
                yield f"{indent(depth)}<{name}/>"

        def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
            if len(meta_xobjects) > 0:
                yield f"{indent(depth)}<{name}>"
                for m, xobj in meta_xobjects:
                    yield from xobj.xml_temp(m.name, depth + 1)
                yield f"{indent(depth)}</{name}>"
            else:
                yield f"{indent(depth)}<{name}/>"

        def xml_in(self, obj: ObjectifiedElement) -> Any:
            parsed: dict[str, Any] = {}
            for m, xobj in meta_xobjects:
                if (m_obj := get(obj, m.name)) is not None:
                    parsed[m.name] = xobj.xml_in(m_obj)
                else:
                    assert False, "member is not present!"
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

    def xml(
        schema_name: str, val: Any | None = None
    ) -> Generator[str, None, None]:
        # yield f'<?xml version="1.0" encoding="utf-8"?>'
        yield from cls_xobject.xml_temp(schema_name, 0)

    def xml_value(self, schema_name: str) -> Generator[str, None, None]:
        yield from cls_xobject.xml_out(schema_name, 0, self)

    def parse(obj: ObjectifiedElement) -> Any:
        return cls_xobject.xml_in(obj)

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
