from dataclasses import dataclass
from pathlib import Path
from pgconn import PostgresConn

# public/external interface
from xmlable import (
    xmlify,
    parse_file,
    write_xml_value,
    write_xml_template,
    write_xsd,
)

THIS_DIR = Path(__file__).parent


@xmlify
@dataclass
class MyConfig:
    foos: int
    conns: list[PostgresConn]


write_xsd(THIS_DIR / "config.xsd", MyConfig)
write_xml_template(THIS_DIR / "config_xml_template.xml", MyConfig)

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

write_xml_value(THIS_DIR / "config_xml_example.xml", original)

read_config: MyConfig = parse_file(
    MyConfig, THIS_DIR / "config_xml_example.xml"
)

assert read_config == original
