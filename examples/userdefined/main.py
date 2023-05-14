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

# public/external interface
from xmlable import xmlify, write_file, parse_file

import re

CONN_STR = "postgresql://user:password@netloc:port/dbname?param1=value1&..."
CONN_PATTERN = "postgresql:\/\/([^:]*):([^@]*)?@([^:]*):(\d+)\/([^\?]*)(\??.*)"


@manual_xmlify
@dataclass
class PostgresConn(IXmlify):
    f"""
    A postgresql connection string of form:
    {CONN_STR}
    """

    user: str
    password: str
    netloc: str
    port: int
    dbname: str
    options: dict[str, str]

    def get_xobject() -> XObject:
        class PGConn(XObject):
            def xsd_out(
                self,
                name: str,
                attribs: dict[str, str] = {},
                add_ns: dict[str, str] = {},
            ) -> _Element:
                return Element(
                    f"{XMLSchema}element",
                    name=name,
                    type="PostgresConn",
                    attrib=attribs,
                )

            def xml_temp(self, name: str) -> _Element:
                return with_text(
                    Element(name), f"Insert connection string here {CONN_STR}"
                )

            def xml_out(self, name: str, val: Any, ctx: XErrorCtx) -> _Element:
                conn = f"postgresql://{val.user}:{val.password}@{val.netloc}:{val.port}/{val.dbname}"
                if len(val.options) > 0:
                    conn += "?" + "&".join(
                        f"{k}={v}" for k, v in val.options.items()
                    )
                return with_text(Element(name), conn)

            def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
                m = re.match(CONN_PATTERN, obj.text)
                if m is not None:
                    (
                        user,
                        password,
                        netloc,
                        port,
                        dbname,
                        raw_params,
                    ) = m.groups()
                    if len(raw_params) > 0:
                        opts = {
                            p.split("=")[0]: p.split("=")[1]
                            for p in raw_params[1:].split("&")
                        }
                    else:
                        opts = {}
                    return PostgresConn(
                        user=user,
                        password=password,
                        netloc=netloc,
                        port=int(port),
                        dbname=dbname,
                        options=opts,
                    )
                else:
                    raise XError(
                        short="Invalid connection string",
                        what=f"Connection string needs to be of form {CONN_STR}, but was {obj.text}",
                        why=f"Only valid strings permissable",
                        ctx=ctx.next("PGConnection"),
                    )

        return PGConn()

    def xsd_forward(add_ns: dict[str, str]) -> _Element:
        # check if the XML namespace has been additionally declared
        # if so we should use this prefix for type
        if (prefix := firstkey(add_ns, XMLURL)) is not None:
            restrict = Element(
                f"{XMLSchema}restriction",
                base=f"{prefix}:string",
            )
        else:
            restrict = Element(
                f"{XMLSchema}restriction",
                base="xs:string",
                nsmap={"xs": XMLURL},
            )

        return with_child(
            Element(f"{XMLSchema}simpleType", name="PGConnection"),
            with_child(
                restrict,
                Element(f"{XMLSchema}pattern", value=CONN_PATTERN),
            ),
        )

    def xsd_dependencies() -> set[type]:
        return {PostgresConn}


@xmlify
@dataclass
class MyConfig:
    foos: int
    conns: list[PostgresConn]


write_file("config.xsd", MyConfig.xsd())
write_file("config_xml_template.xml", MyConfig.xml())

original: MyConfig = MyConfig(
    foos=3,
    conns=[
        PostgresConn(
            user="jimmy",
            password="pass123",
            netloc="localhost",
            port=5432,
            dbname="saul_db",
            options={"secret": "10101"},
        ),
        PostgresConn(
            user="bob",
            password="username",
            netloc="localhost",
            port=5444,
            dbname="other_db",
            options={},
        ),
        PostgresConn(
            user="steve",
            password="pass1234",
            netloc="localhost",
            port=5444,
            dbname="other_db",
            options={"backdoor_key": "bingo"},
        ),
    ],
)

write_file("config_xml_example.xml", original.xml_value())

read_config: MyConfig = parse_file(MyConfig, "config_xml_example.xml")

assert read_config == original
