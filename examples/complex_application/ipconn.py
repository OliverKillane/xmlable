from dataclasses import dataclass
from typing import Any

from lxml.etree import Element, _Element
from lxml.objectify import ObjectifiedElement

# internal modules for custom impl
from xmlable._lxml_helpers import with_child, with_text, XMLSchema, XMLURL
from xmlable._errors import XError, XErrorCtx
from xmlable._xobject import XObject
from xmlable._user import IXmlify
from xmlable._manual import manual_xmlify
from xmlable._utils import firstkey

import re

CONN_STR = "proto:xxx.xxx.xxx.xxx:pppp"
CONN_PATTERN = "(.*):(\d*)\.(\d*)\.(\d*)\.(\d*):(\d*)"


@manual_xmlify
@dataclass
class IPv4Conn(IXmlify):
    f"""
    A connection string of form:
    """
    protocol: str
    ip: tuple[int, int, int, int]
    port: int

    def get_xobject() -> XObject:
        class XIPv4Conn(XObject):
            def xsd_out(
                self,
                name: str,
                attribs: dict[str, str] = {},
                add_ns: dict[str, str] = {},
            ) -> _Element:
                return Element(
                    f"{XMLSchema}element",
                    name=name,
                    type="IPv4Conn",
                    attrib=attribs,
                )

            def xml_temp(self, name: str) -> _Element:
                return with_text(
                    Element(name), f"Insert connection string here {CONN_STR}"
                )

            def xml_out(self, name: str, val: Any, ctx: XErrorCtx) -> _Element:
                conn = f"{val.protocol}:{val.ip[0]}.{val.ip[1]}.{val.ip[2]}.{val.ip[3]}:{val.port}"
                return with_text(Element(name), conn)

            def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
                m = re.match(CONN_PATTERN, obj.text)
                if m is not None:
                    (
                        proto,
                        ip0,
                        ip1,
                        ip2,
                        ip3,
                        port,
                    ) = m.groups()

                    return IPv4Conn(
                        protocol=proto,
                        ip=(int(ip0), int(ip1), int(ip2), int(ip3)),
                        port=int(port),
                    )
                else:
                    raise XError(
                        short="Invalid connection string",
                        what=f"Connection string needs to be of form {CONN_STR}, but was {obj.text}",
                        why=f"Only valid strings permissable",
                        ctx=ctx.next("IPv4Conn"),
                    )

        return XIPv4Conn()

    def xsd_forward(add_ns: dict[str, str]) -> _Element:
        # check if the XML namespace has been additionally declared
        # if so we should use this prefix for type
        if (prefix := firstkey(add_ns, XMLURL)) is not None:
            restrict = Element(
                f"{XMLSchema}restriction",
                base=f"{prefix}:string",
            )
        else:
            new_ns = "xs"
            while new_ns in add_ns:
                new_ns += "s"
            restrict = Element(
                f"{XMLSchema}restriction",
                base=f"{new_ns}:string",
                nsmap={new_ns: XMLURL},
            )

        return with_child(
            Element(f"{XMLSchema}simpleType", name="IPv4Conn"),
            with_child(
                restrict,
                Element(f"{XMLSchema}pattern", value=CONN_PATTERN),
            ),
        )

    def xsd_dependencies() -> set[type]:
        return {IPv4Conn}
