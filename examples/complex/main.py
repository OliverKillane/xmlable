from dataclasses import dataclass
from pathlib import Path
from xmlable import xmlify, write_file, parse_file

THIS_DIR = Path(__file__).parent


@xmlify
@dataclass
class Complex:
    a: dict[tuple[int, str], list[tuple[dict[int, float | str], set[bool]]]]


write_file(THIS_DIR / "config.xsd", Complex.xsd())
write_file(THIS_DIR / "config_xml_template.xml", Complex.xml())

original = Complex(
    a={(3, "hello"): [({3: 0.4}, {True, False}), ({2: "str"}, {False})]}
)
write_file(THIS_DIR / "config_xml_example.xml", original.xml_value())

read_config: Complex = parse_file(Complex, THIS_DIR / "config_xml_example.xml")

assert read_config == original
