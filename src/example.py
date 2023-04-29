from xmlable import xmlify
from dataclasses import dataclass


@xmlify
@dataclass
class Test:
    c: dict[int, str]
    a: int = 3
    b: float = 3.22


@xmlify
@dataclass
class Bob:
    c: list[dict[int, tuple[str, str]]]


@xmlify
@dataclass
class Zoom:
    j: Test
    c: int
    x: Bob


@xmlify
@dataclass
class Based:
    a: dict[int, int]


@xmlify
@dataclass
class BCont:
    b: int | str


# x = Zoom(j=Test({1: 2}, 2), c=4, x=Bob(c=[{3: ("aaaa", "bbbb")}]))


@xmlify
@dataclass
class Test1:
    a: int = 3


x = Test1()

for l in x.xml_template_values("basic", "basic"):
    print(l)

for l in Test1.xsd_conf("basic"):
    print(l)
