from dataclasses import dataclass
from xmlable import xmlify, write_xsd, write_xml, write_xml_value, parse_xml


@xmlify
@dataclass
class Config:
    date: str
    number_of_cores: int
    codes: list[int]
    show_logs: bool


write_xsd(Config, "config.xsd")

write_xml(Config, "config_xml_template.xml")

original = Config(
    date="31/02/2023",  # no validation yet :(
    number_of_cores=48,
    codes=[101, 345, 42, 67],
    show_logs=False,
)
# and now for an example:
write_xml_value(original, "config_xml_example.xml")

# and now read it back
read_config: Config = parse_xml(Config, "config_xml_example.xml")

assert read_config == original
