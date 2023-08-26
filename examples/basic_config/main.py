from dataclasses import dataclass
from pathlib import Path
from xmlable import xmlify, write_file, parse_file

THIS_DIR = Path(__file__).parent


@xmlify
@dataclass
class Config:
    date: str
    number_of_cores: int
    codes: list[int]
    show_logs: bool


write_file(THIS_DIR / "config.xsd", Config.xsd())
write_file(THIS_DIR / "config_xml_template.xml", Config.xml())

original = Config(
    date="31/02/2023",  # no validation yet :(
    number_of_cores=48,
    codes=[101, 345, 42, 67],
    show_logs=False,
)
write_file(THIS_DIR / "config_xml_example.xml", original.xml_value())

read_config: Config = parse_file(Config, THIS_DIR / "config_xml_example.xml")

assert read_config == original
