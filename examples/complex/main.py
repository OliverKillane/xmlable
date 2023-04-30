from dataclasses import dataclass
from xmlable import xmlify, write_xsd, write_xml, write_xml_value, parse_xml


@xmlify
@dataclass
class Complex:
    a: dict[tuple[int, str], list[tuple[dict[int, float | str], set[bool]]]]


original = Complex(
    a={(3, "hello"): [({3: 0.4}, {True, False}), ({2: "str"}, {False})]}
)

write_xsd(Complex, "config.xsd")

write_xml(Complex, "config_xml_template.xml")

# and now for an example:
write_xml_value(original, "config_xml_example.xml")
read_config: Complex = parse_xml(Complex, "config_xml_example.xml")

assert read_config == original
