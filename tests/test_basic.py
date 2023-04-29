from dataclasses import dataclass
from xmlable import xmlify
from utils import validate

BASIC_SCHEMA_NAME = "basic"


def test_scalar_classes():
    @xmlify
    @dataclass
    class Test:
        a: int = 3

    validate(
        Test.xsd_conf("basic"),
        Test().xml_template_values("basic", "basic"),
    )


def test_boolean():
    @xmlify
    @dataclass
    class Test:
        a: bool = True

    validate(
        Test.xsd_conf("basic"),
        Test().xml_template_values("basic", "basic"),
    )


def test_large_scalar():
    @xmlify
    @dataclass
    class Test:
        aint: int = 3
        afloat: float = 0.3
        astr: str = "hi"
        abool: bool = True
        bint: int = 3
        bfloat: float = 0.3
        bstr: str = "hi"
        bbool: bool = True
        cint: int = 3
        cfloat: float = 0.3
        cstr: str = "hi"
        cbool: bool = True
        dint: int = 3
        dfloat: float = 0.3
        dstr: str = "hi"
        dbool: bool = True

    validate(
        Test.xsd_conf("basic"),
        Test().xml_template_values("basic", "basic"),
    )
