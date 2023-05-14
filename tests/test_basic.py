from dataclasses import dataclass
from lxml import etree, objectify
from typing import Any

from xmlable import *


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


def test_scalar_classes():
    @xmlify
    @dataclass
    class Test0:
        pass

    @xmlify
    @dataclass
    class Test1:
        a: int = 3

    @xmlify
    @dataclass
    class Test2:
        a: bool = True

    @xmlify
    @dataclass
    class Test3:
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

    for test_obj in [Test0(), Test1(), Test2(), Test3()]:
        validate(test_obj)


def test_scalar_nested():
    @xmlify
    @dataclass
    class Test0:
        a: int = 3

    @xmlify
    @dataclass
    class Test1:
        x: str
        child: Test0
        y: bool

    @xmlify
    @dataclass
    class Test2:
        child_0: Test0
        child_1: Test1
        z: str

    @xmlify
    @dataclass
    class Test3:
        child_0: Test0
        child_1: Test1
        child_2: Test2
        z: str

    t0 = Test0(a=3)
    t1 = Test1(x="hello", child=t0, y=False)
    t2 = Test2(child_0=t0, child_1=t1, z="world")
    t3 = Test3(child_0=t0, child_1=t1, child_2=t2, z="!")

    for test_obj in [t0, t1, t2, t3]:
        validate(test_obj)


def test_generic_types():
    @xmlify
    @dataclass
    class Test0:
        x: None

    t0 = Test0(x=None)

    @xmlify
    @dataclass
    class Test1:
        x: list[None]

    t1 = Test1(x=[])
    t1_some = Test1(x=[None, None, None])

    @xmlify
    @dataclass
    class Test2:
        x: list[int]
        y: dict[int, str]
        z: set[bool]

    t2 = Test2(x=[1, 2, 3], y={1: "a", 2: "b", 3: "c"}, z={True, False})
    t2_none = Test2(x=[], y={}, z=set())

    @xmlify
    @dataclass
    class Test3:
        x: list[Test1]
        y: dict[str, Test2]

    t3 = Test3(
        x=[t1, t1, t1_some],
        y={
            "hello": t2,
            "world": t2_none,
        },
    )

    @xmlify
    @dataclass
    class Test4:
        x: list[list[dict[int, Test1]]]

    t4 = Test4(
        x=[
            [{2: t1}, {3: t1_some}],
            [{2: t1}, {3: t1_some}],
        ]
    )

    for test_obj in [t0, t1, t1_some, t2, t2_none, t3, t4]:
        validate(test_obj)


def test_basic_unions():
    @xmlify
    @dataclass
    class Test0:
        a: int | None

    t0_some = Test0(3)
    t0_none = Test0(None)

    @xmlify
    @dataclass
    class Test1:
        a: int | float | str | bool | None

    t1_int = Test1(9)
    t1_float = Test1(0.33)
    t1_str = Test1("hello")
    t1_bool = Test1(True)
    t1_none = Test1(None)

    @xmlify
    @dataclass
    class Test2:
        a: int | Test1

    t2_int = Test2(3)
    t2_T1_bool = Test2(t1_bool)
    t2_T1_none = Test2(t1_none)

    for test_obj in [
        t0_some,
        t0_none,
        t1_int,
        t1_float,
        t1_str,
        t1_bool,
        t1_none,
        t2_int,
        t2_T1_bool,
        t2_T1_none,
    ]:
        validate(test_obj)


def test_advanced_test():
    @xmlify
    @dataclass
    class Complex:
        a: dict[tuple[int, str], list[tuple[dict[int, float | str], set[bool]]]]

    c1 = Complex(
        a={(3, "hello"): [({3: 0.4}, {True, False}), ({2: "str"}, {False})]}
    )

    validate(c1)
