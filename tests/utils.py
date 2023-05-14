from lxml import etree, objectify
from typing import Any


def validate(obj: Any):
    schema_name: str = "basic"
    obj_cls = type(obj)

    """ Checks both a valid xml conforms """
    xsd = obj_cls.xsd(schema_name)
    xsd_schema = etree.XMLSchema(xsd)

    xml = obj.xml_value(schema_name)
    xml_str = etree.tostring(xml)
    xml_object = objectify.fromstring(xml_str)

    # validation check
    xsd_schema.assertValid(xml)
    assert obj == obj_cls.parse(
        xml_object
    ), "Parsed object does not match source"
