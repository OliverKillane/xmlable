from dataclasses import dataclass
import pytest

from xmlable import *
from xmlable._errors import XError


def test_xmlified():
    with pytest.raises(XError):

        @dataclass
        class A:
            mem: int

        @xmlify
        @dataclass
        class B:
            mem: A


def test_reserved_attrs():
    with pytest.raises(XError):

        @xmlify
        @dataclass
        class A:
            get_xobject: int

    with pytest.raises(XError):

        @xmlify
        @dataclass
        class A:
            comment: int

    with pytest.raises(XError):

        @xmlify
        @dataclass
        class A:
            xsd_forward: int
