from dataclasses import dataclass
from typing import Any
from types import FunctionType
from inspect import getmembers, isclass, cleandoc

# Exceptions


class NotAClassError(Exception):
    def __init__(self, attempted: object):
        message = (
            f"""{attempted} is not a class, so cannot have xmlconfig derived"""
        )
        super(NotAClassError, self).__init__(message)


class MemberNoType(Exception):
    def __init__(self, classname: str, member: str, value: Any):
        message = f"""{classname}.{member} has value {value}, but no type from which to derive xml config. In class {classname}, use {member}: <type> = {value}"""
        super(MemberNoType, self).__init__(message)


# Class metadata handling


@dataclass
class MemberMeta:
    docs: str | None
    name: str
    type: type
    default_value: Any | None


@dataclass
class ClassMetaData:
    cls: type
    doc: str | None
    name: str
    superclasses: list[type]
    members: list[MemberMeta]


def get_metadata(cls: type) -> ClassMetaData:
    if not isclass(cls):
        raise NotAClassError(cls)

    name = cls.__name__
    member_annos = cls.__annotations__
    defined_members = {}
    for member in getmembers(cls)[::-1]:
        match member:
            case (m, d) if type(d) != type and not m.startswith("__"):
                # Do not add methods
                if type(d) != FunctionType:
                    defined_members[m] = d
            case _:
                break

    members = []
    for m in set.union(set(member_annos.keys()), set(defined_members.keys())):
        match member_annos.get(m), defined_members.get(m):
            case None, d:
                raise MemberNoType(classname=name, member=m, value=d)
            case t, d if t is not None:
                # Note: MyPy bug #13046 makes redundant if guard necessar
                members.append(
                    MemberMeta(docs="", name=m, type=t, default_value=d)
                )
            case _:
                assert (
                    False
                ), "unreachable: if not d or t => not in either set => not in union"

    # using method resolution order to get superclasses
    superclasses: list[type] = [sc for sc in cls.__mro__]

    doc: str | None = cls.__doc__
    if doc is not None:
        doc = cleandoc(doc)

    return ClassMetaData(cls, doc, name, superclasses, members)


def xmlify(cls: type) -> type:
    cmd = get_metadata(cls)

    def xsd_out() -> str:
        return f"xsd out:   {cmd}"

    def xml_out() -> str:
        return f"xml out:   {cmd}"

    def xml_in(xml) -> cls:
        return "this obj"

    cls.xsd_out = xsd_out
    cls.xml_out = xml_out
    cls.xml_in = xml_in

    return cls
