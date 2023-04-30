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
from xmlable._errors import XErrorCtx, XError

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
        self, name: str, depth: int, val: Any, ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
        pass


@dataclass
class BasicObj(XObject):
    """
    An xobject for a simple type (e.g string, int)
    """

    type_str: str
    convert_fn: Callable[[Any], str]
    validate_fn: Callable[[Any], bool]
    parse_fn: Callable[[ObjectifiedElement], Any]

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}" type="{self.type_str}"{stringify_mods(mods)}/>'

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}> Fill me with an {self.type_str} </{name}>"

    def xml_out(
        self, name: str, depth: int, val: Any, ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        if not self.validate_fn(val):
            raise XError(
                short="Invalid Data",
                what=f"Could not validate {val} as a valid {self.type_str}",
                why=f"Produced xml must be valid",
                ctx=ctx,
            )
        yield f"{indent(depth)}<{name}>{self.convert_fn(val)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
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
        self, name: str, depth: int, val: list[Any], ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        if len(val) > 0:
            yield f"{indent(depth)}<{name}>"
            for i, item_val in enumerate(val):
                yield from self.item_xobject.xml_out(
                    self.list_elem_name,
                    depth + 1,
                    item_val,
                    ctx.next(f"{self.list_elem_name}[{i}]"),
                )
            yield f"{indent(depth)}</{name}>"
        else:
            yield f'{indent(depth)}<{name}/>{xcomment("Empty List!")}'

    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> list[Any]:
        parsed = []
        for i, child in enumerate(children(obj)):
            if child.tag != self.list_elem_name:
                raise XError(
                    short="Unexpected Tag",
                    what=f"Found {self.list_elem_name} but found {child.tag}",
                    why=f"This is a {self.struct_name} that contains 0..n elements of {self.list_elem_name} and no other elements",
                    ctx=ctx,
                )
            else:
                parsed.append(
                    self.item_xobject.xml_in(
                        child, ctx.next(f"{self.list_elem_name}[{i}]")
                    )
                )
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
        yield f"{indent(depth+ 1)}<{GNS_POST}complexType>"
        yield f"{indent(depth + 2)}<{GNS_POST}sequence>"
        for member, xobj in self.objects:
            yield from xobj.xsd_out(member, depth + 3)
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 1)}</{GNS_POST}complexType>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_temp(self, name: str, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{name}>{xcomment(f"This is a {self.struct_name}")}'
        for member, xobj in self.objects:
            yield from xobj.xml_temp(member, depth + 1)
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: tuple[Any, ...], ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        if len(val) != len(self.objects):
            raise XError(
                short="Incorrect Type",
                what=f"You have provided the values {len(val)} values {val} for {name}, but {name} is a {self.struct_name} that takes only {len(self.objects)} values",
                why=f"In order to generate xml, the values provided need to be the correct types",
                ctx=ctx,
            )

        yield f"{indent(depth)}<{name}>"
        for (member, xobj), v in zip(self.objects, val):
            yield from xobj.xml_out(member, depth + 1, v, ctx.next(member))
        yield f"{indent(depth)}</{name}>"

    def xml_in(
        self, obj: ObjectifiedElement, ctx: XErrorCtx
    ) -> list[tuple[str, Any]]:
        parsed = []
        for i, (child, (name, xobj)) in enumerate(
            zip(children(obj), self.objects)
        ):
            if child.tag != name:
                raise XError(
                    short="Incorrect Element Tag",
                    what=f"While parsing {self.struct_name} {obj.tag} we expected element {i} to be {name}, but found {child.tag}",
                    why=f"The xml representation for {self.struct_name} requires the correct names in the correct order",
                    ctx=ctx,
                )
            parsed.append((name, xobj.xml_in(child, ctx.next(name))))
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
        self, name: str, depth: int, val: tuple[Any, ...], ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        yield from self.struct.xml_out(name, depth, val, ctx)

    def xml_in(
        self, obj: ObjectifiedElement, ctx: XErrorCtx
    ) -> tuple[Any, ...]:
        # Assumes the objects are in the correct order
        return list(zip(*self.struct.xml_in(obj, ctx)))[1]


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
        self, name: str, depth: int, val: set[Any], ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        yield from self.list.xml_out(name, depth, list(val), ctx)

    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> set[Any]:
        parsed: set[Any] = set()
        for item in self.list.xml_in(obj, ctx):
            if item in parsed:
                raise XError(
                    short="Duplicate item in Set",
                    what=f"In {obj.tag} the item {item} is present more than once",
                    why=f"A set can only contain unique items",
                    ctx=ctx,
                )
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
        yield from self.key_xobject.xml_temp(self.key_name, depth + 2)
        yield from self.val_xobject.xml_temp(self.val_name, depth + 2)
        yield f"{indent(depth + 1)}</{self.item_name}>"
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: dict[Any, Any], ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        item_ctx = ctx.next(self.item_name)
        for k, v in val.items():
            yield f"{indent(depth + 1)}<{self.item_name}>"
            yield from self.key_xobject.xml_out(
                self.key_name, depth + 2, k, item_ctx.next(name)
            )
            yield from self.val_xobject.xml_out(
                self.val_name, depth + 2, v, item_ctx.next(name)
            )
            yield f"{indent(depth + 1)}</{self.item_name}>"
        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> dict[Any, Any]:
        parsed = {}
        for child in children(obj):
            if child.tag != self.item_name:
                raise XError(
                    short="Invalid item in dictionary",
                    what=f"An unexpected item with {child.tag} is in dictionary {obj.tag}",
                    why=f"Each item must have tag {self.item_name} with children {self.key_name} and {self.val_name}",
                    ctx=ctx,
                )
            else:
                child_ctx = ctx.next(self.item_name)
                k = self.key_xobject.xml_in(
                    get(child, self.key_name), child_ctx.next(self.key_name)
                )
                v = self.val_xobject.xml_in(
                    get(child, self.val_name), child_ctx.next(self.val_name)
                )

                if k in parsed:
                    raise XError(
                        short="Duplicate key in dictionary",
                        what=f"In dictionary {obj.tag} the key {k} is present more than once",
                        why=f"Dictionaries must have unique keys",
                        cts=ctx,
                    )

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
            yield from xobj.xml_temp(self.elem_gen(t), depth + 1)

        yield f"{indent(depth)}-->"
        yield f"{indent(depth)}</{name}>"

    def xml_out(
        self, name: str, depth: int, val: Any, ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        t = type(val)

        if (val_xobj := self.xobjects.get(t)) is not None:
            variant_name = self.elem_gen(t)
            yield from val_xobj.xml_out(
                variant_name, depth + 1, val, ctx.next(variant_name)
            )
        else:
            types = " | ".join(str(t) for t in self.xobjects.keys())
            raise XError(
                short=f"Datatype not in Union",
                what=f"{name} is a union of {types}, which does not contain {t} (you provided: {val})",
                why=f"... uuuh, its a union?",
                ctx=ctx,
            )

        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
        named = {self.elem_gen(t): xobj for t, xobj in self.xobjects.items()}
        variants = list(children(obj))

        if len(variants) != 1:
            variant_names = ", ".join(v.tag for v in variants)
            raise XError(
                short="Multiple union variants present",
                what=f"variants {variant_names} are present",
                why=f"A union can only be one variant at a time",
                ctx=ctx,
            )

        variant = variants[0]
        if (xobj := named.get(variant.tag)) is not None:
            return xobj.xml_in(variant, ctx.next(variant.tag))
        else:
            named_vars = ", ".join(named.keys())
            raise XError(
                short="Invalid Variant",
                what=f"The union {obj.tag} can contain variants {named_vars}, but you have used {variant}",
                why=f"Only valid variants can be parsed",
                ctx=ctx,
            )


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
        self, name: str, depth: int, val: None, ctx: XErrorCtx
    ) -> Generator[str, None, None]:
        if val != None:
            raise XError(
                short="None object is not None",
                what=f"{name} contains value {val} which is not None",
                why="A None type object can only contain none",
                ctx=ctx,
            )

        yield f'{indent(depth)}<{name}/>{xcomment("This is None")}'

    def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
        return None


def is_xmlified(cls):
    return hasattr(cls, "xmlified")


def gen_xobject(data_type: type, forward_dec: set[type]) -> XObject:
    basic_types = {
        int: (f"{GNS_POST}integer", str, lambda d: type(d) == int),
        str: (f"{GNS_POST}string", str, lambda d: type(d) == str),
        float: (f"{GNS_POST}decimal", str, lambda d: type(d) == float),
        bool: (
            f"{GNS_POST}boolean",
            lambda b: "true" if b else "false",
            lambda d: type(d) == bool,
        ),
    }

    if (basic_entry := basic_types.get(data_type)) is not None:
        type_str, convert_fn, validate_fn = basic_entry
        return BasicObj(type_str, convert_fn, validate_fn, data_type)
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
