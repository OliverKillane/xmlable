from dataclasses import dataclass
from xmlable import xmlify
from lxml import objectify


@xmlify
@dataclass
class Test0:
    a: int | None


t0 = Test0(None)

xml_string = "\n".join(t0.xml_value("basic"))
xml_object = objectify.fromstring(xml_string)
Test0.parse(xml_object)
