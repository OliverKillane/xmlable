from dataclasses import dataclass
from pgconn import PostgresConn

# public/external interface
from xmlable import xmlify, write_file, parse_file


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
