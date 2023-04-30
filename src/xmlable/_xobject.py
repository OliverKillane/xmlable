""" XObjects
XObjects are an intermediate representation for python types -> xsd/xml
- Produced by @xmlify decorated classes, and by gen_xobject
- Associated xsd, xml and parsing 
"""


from dataclasses import dataclass
from types import NoneType, UnionType
from lxml.objectify import ObjectifiedElement
from abc import ABC, abstractmethod
from typing import Any, Callable, Generator, Iterable, get_args

from xmlable._utils import get, opt_get


GNS_POST = "xsd:"
GNS_PRE = ":xsd"


def typename(t: type) -> str:
    return t.__name__


def indent(depth: int) -> str:
    return " " * 2 * depth


def stringify_mods(mods: dict[str, Any]) -> str:
    return "".join(f' {key}="{val}"' for key, val in mods.items())


def xcomment(txt: str) -> str:
    return f"<!-- {txt} -->"


def children(obj: ObjectifiedElement) -> Iterable[ObjectifiedElement]:
    return filter(
        lambda child_obj: child_obj.tag != "comment", obj.getchildren()
    )


class XObject(ABC):
    """Any XObject wraps the xsd generation,
    We can map types to XObjects to get the xsd, template xml, etc
    """

    @abstractmethod
    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        """Generate the xsd schema for the object"""
        pass

    @abstractmethod
    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        """
        Generate commented output for the xml representation
        - Contains no values, only comments
        - Not valid xml (can contain nested comments, comments instead of values)
        """
        pass

    @abstractmethod
    def xml_out(
        self, name: str, depth: int, val: Any
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def xml_in(self, obj: ObjectifiedElement) -> Any:
        pass


@dataclass
class BasicObj(XObject):
    """
    An xobject for a simple type (e.g string, int)
    """

    type_str: str
    convert_fn: Callable[[Any], str]
    parse_fn: Callable[[ObjectifiedElement], Any]

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}" type="{self.type_str}"{stringify_mods(mods)}/>'

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}> Fill me with an {self.type_str} </{name}>"

    def xml_out(
        self, name: str, depth: int, val: Any
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>{self.convert_fn(val)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> Any:
        return self.parse_fn(obj)


@dataclass
class ListObj(XObject):
    """
    An ordered list of objects
    """

    item_xobject: XObject
    list_elem_name: str = "listitem"
    struct_name: str = "list"

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}"{stringify_mods(mods)}>'
        yield f'{indent(depth + 1)}<{GNS_POST}complexType> {xcomment("this is a list!")}'
        yield f"{indent(depth + 2)}<{GNS_POST}sequence>"
        yield from self.item_xobject.xsd_out(
            self.list_elem_name,
            depth + 3,
            {"minOccurs": 0, "maxOccurs": "unbounded"},
        )
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 1)}</{GNS_POST}complexType>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{name}>{xcomment(f"This is a {self.struct_name}")}'
        yield from self.item_xobject.xml_temp(self.list_elem_name, depth + 1)
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: list[Any]
    ) -> Generator[str, None, None]:
        if len(val) > 0:
            yield f"{indent(depth)}<{name}>"
            for item_val in val:
                yield from self.item_xobject.xml_out(
                    self.list_elem_name, depth + 1, item_val
                )
            yield f"{indent(depth)}</{name}>"
        else:
            yield f'{indent(depth)}<{name}/>{xcomment("Empty List!")}'

    def xml_in(self, obj: ObjectifiedElement) -> list[Any]:
        parsed = []
        for child in children(obj):
            print(str(child))
            if child.tag != self.list_elem_name:
                assert False, "This should be here!"
            else:
                parsed.append(self.item_xobject.xml_in(child))
        return parsed


@dataclass
class StructObj(XObject):
    """An order list of key-value pairs"""  # TODO: make objects variable length tuple

    objects: list[tuple[str, XObject]]
    struct_name: str = "struct"

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}"{stringify_mods(mods)}>'
        yield f"{indent(depth + 2)}<{GNS_POST}sequence>"
        for member, xobj in self.objects:
            yield from xobj.xsd_out(member, depth + 3)
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{name}>{xcomment(f"This is a {self.struct_name}")}'
        for member, xobj in self.objects:
            yield from xobj.xml_temp(member, depth + 1)
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: tuple[Any, ...]
    ) -> Generator[str, None, None]:
        if len(val) != len(self.objects):
            assert False, "must be same"

        yield f"{indent(depth)}<{name}>"
        for (member, xobj), v in zip(self.objects, val):
            yield from xobj.xml_out(member, depth + 1, v)
        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> list[tuple[str, Any]]:
        parsed = []
        for child, (name, xobj) in zip(children(obj), self.objects):
            if child.tag != name:
                assert False, "Must be name"
            parsed.append((name, xobj.xml_in(child)))
        return parsed


class TupleObj(XObject):
    """An anonymous struct"""

    def __init__(
        self,
        objects: tuple[XObject, ...],
        elem_gen: Callable[[int], str] = lambda i: f"tupleitem{i}",
    ):
        self.elem_gen = elem_gen
        self.struct: StructObj = StructObj(
            [(self.elem_gen(i), xobj) for i, xobj in enumerate(objects)],
            struct_name="tuple",
        )

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield from self.struct.xsd_out(name, depth, mods)

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield from self.struct.xml_temp(name, depth)

    def xml_out(
        self, name: str, depth: int, val: tuple[Any, ...]
    ) -> Generator[str, None, None]:
        yield from self.struct.xml_out(name, depth, val)

    def xml_in(self, obj: ObjectifiedElement) -> tuple[Any, ...]:
        # Assumes the objects are in the correct order
        return list(zip(*self.struct.xml_in(obj)))[1]


class SetOBj(XObject):
    """An unordered collection of unique elements"""

    def __init__(self, inner: XObject, elem_name: str = "setitem"):
        self.list = ListObj(inner, elem_name, struct_name="set")

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield from self.list.xsd_out(name, depth, mods)

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield from self.list.xml_temp(name, depth)

    def xml_out(
        self, name: str, depth: int, val: set[Any]
    ) -> Generator[str, None, None]:
        yield from self.list.xml_out(name, depth, list(val))

    def xml_in(self, obj: ObjectifiedElement) -> set[Any]:
        parsed: set[Any] = set()
        for item in self.list.xml_in(obj):
            if item in parsed:
                assert False, "cannot already be present"
            parsed.add(item)
        return parsed


@dataclass
class DictObj(XObject):
    """An unordered collection of key-value pair elements"""

    key_xobject: XObject
    val_xobject: XObject
    key_name: str = "key"
    val_name: str = "val"
    item_name: str = "dictitem"

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}"{stringify_mods(mods)}>'
        yield f'{indent(depth + 1)}<{GNS_POST}complexType> {xcomment("this is a dictionary!")}'
        yield f"{indent(depth + 2)}<{GNS_POST}sequence>"
        yield f'{indent(depth + 3)}<{GNS_POST}element name="{self.item_name}" minOccurs="0" maxOccurs="unbounded">'
        yield f"{indent(depth + 4)}<{GNS_POST}complexType>"
        yield f"{indent(depth + 5)}<{GNS_POST}sequence>"
        yield from self.key_xobject.xsd_out(self.key_name, depth + 6)
        yield from self.val_xobject.xsd_out(self.val_name, depth + 6)
        yield f"{indent(depth + 5)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 4)}</{GNS_POST}complexType>"
        yield f"{indent(depth + 3)}</{GNS_POST}element>"
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 1)}</{GNS_POST}complexType>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        yield f'{indent(depth + 1)}<{self.item_name}>{xcomment("This is a dictionary")}'
        yield from self.key_xobject.xml_out(self.key_name, depth + 2, None)
        yield from self.val_xobject.xml_out(self.val_name, depth + 2, None)
        yield f"{indent(depth + 1)}</{self.item_name}>"
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: dict[Any, Any]
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        for k, v in val.items():
            yield f"{indent(depth + 1)}<{self.item_name}>"
            yield from self.key_xobject.xml_out(self.key_name, depth + 2, k)
            yield from self.val_xobject.xml_out(self.val_name, depth + 2, v)
            yield f"{indent(depth + 1)}</{self.item_name}>"
        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> dict[Any, Any]:
        parsed = {}
        for child in children(obj):
            if child.tag != self.item_name:
                assert False, "This shouldnt be here!"
            else:
                k = self.key_xobject.xml_in(get(child, self.key_name))
                v = self.val_xobject.xml_in(get(child, self.val_name))
                parsed[k] = v
                # Check for other tags? Fail better?
        return parsed


@dataclass
class UnionObj(XObject):
    """A variant, can be one of several different types"""

    xobjects: dict[type, XObject]
    elem_gen: Callable[[type], str] = lambda t: f"variant{typename(t)}"

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}"{stringify_mods(mods)}>'
        yield f'{indent(depth + 1)}<{GNS_POST}complexType> {xcomment("this is a union!")}'
        yield f"{indent(depth + 2)}<{GNS_POST}sequence>"
        for t, xobj in self.xobjects.items():
            yield from xobj.xsd_out(
                self.elem_gen(t), depth + 3, {"minOccurs": 0}
            )
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 1)}</{GNS_POST}complexType>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        yield f"{indent(depth)}<!-- This is a union, the following variants are possible"

        for t, xobj in self.xobjects.items():
            yield from xobj.xml_out(self.elem_gen(t), depth + 1, None)

        yield f"{indent(depth)}-->"
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: Any
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        t = type(val)

        if (val_xobj := self.xobjects.get(t)) is not None:
            yield from val_xobj.xml_out(self.elem_gen(t), depth + 1, val)
        else:
            assert False, "Must be in the variants"

        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> Any:
        # TODO: Make this nicer, dont recompute the dict every time?
        named = {self.elem_gen(t): xobj for t, xobj in self.xobjects.items()}
        variants = list(children(obj))

        if len(variants) != 1:
            assert False, "Must only be 1"

        variant = variants[0]
        if (xobj := named.get(variant.tag)) is not None:
            return xobj.xml_in(variant)
        else:
            assert False, "Not a present variant"


class NoneObj(XObject):
    """
    An object representing the python 'None' type
    - Unions of form `int | None` are used for optionals
    """

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}"{stringify_mods(mods)}/>{xcomment("None Type")}'

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{name}/>{xcomment("This is None")}'

    def xml_out(
        self, name: str, depth: int, val: None
    ) -> Generator[str, None, None]:
        if val != None:
            assert False, "Must be none!"

        yield f'{indent(depth)}<{name}/>{xcomment("This is None")}'

    def xml_in(self, obj: ObjectifiedElement) -> Any:
        return None


def is_xmlified(cls):
    return hasattr(cls, "xmlified")


def gen_xobject(data_type: type, forward_dec: set[type]) -> XObject:
    basic_types = {
        int: (f"{GNS_POST}integer", str),
        str: (f"{GNS_POST}string", str),
        float: (f"{GNS_POST}decimal", str),
        bool: (f"{GNS_POST}boolean", lambda b: "true" if b else "false"),
    }

    if (basic_entry := basic_types.get(data_type)) is not None:
        type_str, convert_fn = basic_entry
        return BasicObj(type_str, convert_fn, data_type)
    elif isinstance(data_type, NoneType) or data_type == NoneType:
        # NOTE: Pythong typing cringe: None can be both a type and a value
        #       (even when within a type hint!)
        # a: list[None] -> None is an instance of NoneType
        # a: int | None -> Union of int and NoneType
        return NoneObj()
    elif isinstance(data_type, UnionType):
        return UnionObj(
            {t: gen_xobject(t, forward_dec) for t in get_args(data_type)}
        )
    elif typename(data_type) == "list":
        (item_type,) = get_args(data_type)
        return ListObj(gen_xobject(item_type, forward_dec))
    elif typename(data_type) == "dict":
        key_type, val_type = get_args(data_type)
        return DictObj(
            gen_xobject(key_type, forward_dec),
            gen_xobject(val_type, forward_dec),
        )
    elif typename(data_type) == "tuple":
        return TupleObj(
            tuple(gen_xobject(t, forward_dec) for t in get_args(data_type))
        )
    elif typename(data_type) == "set":
        (item_type,) = get_args(data_type)
        return SetOBj(gen_xobject(item_type, forward_dec))
    else:
        if is_xmlified(data_type):
            forward_dec.add(data_type)
            return data_type.get_xobject()
        else:
            assert False, "Bad, type is not avail"
