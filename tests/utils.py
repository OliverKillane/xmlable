from lxml import etree, objectify
from typing import Any


def validate(obj: Any):
    schema_name: str = "basic"
    obj_cls = type(obj)

    """Checks both a valid xml conforms"""
    xsd_string = "\n".join(obj_cls.xsd(schema_name))
    xsd_parsed = etree.fromstring(xsd_string)
    xsd_schema = etree.XMLSchema(xsd_parsed)

    xml_string = "\n".join(obj.xml_value(schema_name))
    xml_parsed = etree.fromstring(xml_string)
    xml_object = objectify.fromstring(xml_string)

    # validation check
    xsd_schema.assertValid(xml_parsed)
    assert obj == obj_cls.parse(
        xml_object
    ), "Parsed object does not match source"
