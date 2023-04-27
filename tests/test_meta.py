from xmlable import xmlify


def test_can_xmilfy() -> None:
    # Test classes
    @xmlify
    class A:
        x: int = 3
        y: float = 4
        z: str

    @xmlify
    class B:
        child: A
        other: bool

    print(B.xsd_out())
    print(B.xml_out())
    print(B.xml_in("hello"))

    assert True, "TODO: need to make actual test"
