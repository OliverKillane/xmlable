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
class Complex:
    a: dict[tuple[int, str], list[tuple[dict[int, float | str], set[bool]]]]


write_xsd(THIS_DIR / "config.xsd", Complex)
write_xml_template(THIS_DIR / "config_xml_template.xml", Complex)

original = Complex(
    a={(3, "hello"): [({3: 0.4}, {True, False}), ({2: "str"}, {False})]}
)
write_xml_value(THIS_DIR / "config_xml_example.xml", original)

read_config: Complex = parse_file(Complex, THIS_DIR / "config_xml_example.xml")

assert read_config == original
