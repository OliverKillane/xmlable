from lxml import etree
from typing import Generator


def validate(
    schema: Generator[str, None, None], xml: Generator[str, None, None]
):
    """Checks both a valid xml conforms"""
    xsd_string = "".join(schema)
    xsd_parsed = etree.fromstring(xsd_string)
    xsd_schema = etree.XMLSchema(xsd_parsed)

    xml_string = "".join(xml)
    xml_parsed = etree.fromstring(xml_string)

    # validation check
    xsd_schema.assertValid(xml_parsed)
