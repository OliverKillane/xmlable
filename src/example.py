from xmlable import *


@xmlify
class AA:
    a: int = 3
    b: float
    c: str = "helllloooo"


@xmlify
class BB:
    z: AA
    j: bool


@xmlify_main("this file!")
class CC:
    y: float
    x: int


def p(g):
    for x in g:
        print(x)


print(BB.get_xmlify())

p(BB.get_xmlify().generate_xml(0))
