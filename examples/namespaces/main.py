from dataclasses import dataclass
from pathlib import Path
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
class Config:
    date: str
    number_of_cores: int
    codes: list[int]
    show_logs: bool


write_xsd(
    THIS_DIR / "config.xsd",
    Config,
    namespaces={"xmlSchema": "http://www.w3.org/2001/XMLSchema"},
)
write_xml_template(THIS_DIR / "config_xml_template.xml", Config)

original = Config(
    date="31/02/2023",  # no validation yet :(
    number_of_cores=48,
    codes=[101, 345, 42, 67],
    show_logs=False,
)
write_xml_value(THIS_DIR / "config_xml_example.xml", original)

read_config: Config = parse_file(Config, THIS_DIR / "config_xml_example.xml")

assert read_config == original
