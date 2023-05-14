from dataclasses import dataclass
from xmlable import xmlify, write_file, parse_file


@xmlify
@dataclass
class Config:
    date: str
    number_of_cores: int
    codes: list[int]
    show_logs: bool


write_file(
    "config.xsd",
    Config.xsd(namespaces={"xmlSchema": "http://www.w3.org/2001/XMLSchema"}),
)
write_file("config_xml_template.xml", Config.xml())

original = Config(
    date="31/02/2023",  # no validation yet :(
    number_of_cores=48,
    codes=[101, 345, 42, 67],
    show_logs=False,
)
write_file("config_xml_example.xml", original.xml_value())

read_config: Config = parse_file(Config, "config_xml_example.xml")

assert read_config == original
