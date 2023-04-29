from dataclasses import dataclass, fields, is_dataclass
from abc import ABC, abstractmethod
import sys
from typing import (
    Any,
    Callable,
    Generator,
    TypeVar,
    dataclass_transform,
    get_args,
)
from types import UnionType, NoneType
from lxml.objectify import ObjectifiedElement

# Constants
GNS_POST = "xsd:"
GNS_PRE = ":xsd"

# Utilities
T = TypeVar("T")


def some_or(data: T | None, alt: T):
    return data if data is not None else alt


N = TypeVar("N")
M = TypeVar("M")


def some_or_apply(data: N, fn: Callable[[N], M], alt: M):
    return fn(data) if data is not None else alt


def get(obj: Any, attr: str) -> Any:
    return obj.__getattribute__(attr)


def typename(t: type) -> str:
    return t.__name__


def indent(depth: int) -> str:
    return " " * 2 * depth


# Object wrapping
def stringify_mods(mods: dict[str, Any]) -> str:
    return "".join(f' {key}="{val}"' for key, val in mods.items())


def xcomment(txt: str) -> str:
    return f"<!-- {txt} -->"


class XObject(ABC):
    """Any XObject wraps the xsd generation,
    We can map types to XObjects to get the xsd, template xml, etc
    """

    @abstractmethod
    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def xml_out(
        self, name: str, depth: int, val: Any | None
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def xml_in(self, obj: ObjectifiedElement) -> Any:
        pass


@dataclass
class BasicObj(XObject):
    type_str: str
    convert_fn: Callable[[Any], str]
    parse_fn: Callable[[ObjectifiedElement], Any]

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}" type="{self.type_str}"{stringify_mods(mods)}/>'

    def xml_out(
        self, name: str, depth: int, val: Any | None
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{name}>{some_or_apply(val, self.convert_fn, f" !!Fill with a {self.type_str}!! ")}</{name}>'

    def xml_in(self, obj: ObjectifiedElement) -> Any:
        return self.parse_fn(obj)


@dataclass
class ListObj(XObject):
    item_xobject: XObject
    list_elem_name: str = "listitem"

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

    def xml_out(
        self, name: str, depth: int, val: list[Any] | None
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        if val is not None and len(val) > 0:
            for item_val in val:
                yield from self.item_xobject.xml_out(
                    self.list_elem_name, depth + 1, item_val
                )
        else:
            yield from self.item_xobject.xml_out(
                self.list_elem_name, depth + 1, None
            )
        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> list[Any]:
        parsed = []
        for child in obj.getchildren():
            if child.tag != self.list_elem_name:
                assert False, "This should be here!"
            else:
                parsed.append(self.item_xobject.xml_in(child))
        return parsed


@dataclass
class StructObj(XObject):
    objects: list[tuple[str, XObject]]

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}element name="{name}"{stringify_mods(mods)}>'
        yield f"{indent(depth + 2)}<{GNS_POST}sequence>"
        for member, xobj in self.objects:
            yield from xobj.xsd_out(member, depth + 3)
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_out(
        self, name: str, depth: int, val: tuple[Any, ...] | None
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        if val is None:
            for member, xobj in self.objects:
                yield from xobj.xml_out(member, depth + 1, None)
        elif len(val) != len(self.objects):
            assert False, "must be same"
        else:
            for (member, xobj), v in zip(self.objects, val):
                yield from xobj.xml_out(member, depth + 1, v)
        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> list[tuple[str, Any]]:
        parsed = []
        for child, (name, xobj) in zip(obj.getchildren(), self.objects):
            if child.tag != name:
                assert False, "Must be name"
            parsed.append((name, xobj.xml_in(child)))
        return parsed


class TupleObj(XObject):
    def __init__(
        self,
        objects: tuple[XObject, ...],
        elem_gen: Callable[[int], str] = lambda i: f"tupleitem{i}",
    ):
        self.elem_gen = elem_gen
        self.struct: StructObj = StructObj(
            [(self.elem_gen(i), xobj) for i, xobj in enumerate(objects)]
        )

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield from self.struct.xsd_out(name, depth, mods)

    def xml_out(
        self, name: str, depth: int, val: tuple[Any, ...] | None
    ) -> Generator[str, None, None]:
        yield from self.struct.xml_out(name, depth, val)

    def xml_in(self, obj: ObjectifiedElement) -> tuple[Any, ...]:
        # Assumes the objects are in the correct order
        return list(zip(*self.struct.xml_in(obj)))[1]


class SetOBj(XObject):
    def __init__(self, inner: XObject, elem_name: str = "setitem"):
        self.list = ListObj(inner, elem_name)

    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield from self.list.xsd_out(name, depth, mods)

    def xml_out(
        self, name: str, depth: int, val: set[Any] | None
    ) -> Generator[str, None, None]:
        yield from self.list.xml_out(
            name, depth, some_or_apply(val, list, None)
        )

    def xml_in(self, obj: ObjectifiedElement) -> set[Any]:
        parsed: set[Any] = {}
        for item in self.list.xml_in(obj):
            if item in parsed:
                assert False, "cannot already be present"
            parsed.add(item)
        return parsed


@dataclass
class DictObj(XObject):
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
        yield f"{indent(depth + 4)}<{GNS_POST}sequence>"
        yield from self.key_xobject.xsd_out(self.key_name, depth + 5)
        yield from self.val_xobject.xsd_out(self.val_name, depth + 5)
        yield f"{indent(depth + 4)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 3)}</{GNS_POST}element>"
        yield f"{indent(depth + 2)}</{GNS_POST}sequence>"
        yield f"{indent(depth + 1)}</{GNS_POST}complexType>"
        yield f"{indent(depth)}</{GNS_POST}element>"

    def xml_out(
        self, name: str, depth: int, val: dict[Any, Any] | None
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        if val is not None and len(val) > 0:
            for k, v in val.items():
                yield f"{indent(depth + 1)}<{self.item_name}>"
                yield from self.key_xobject.xml_out(self.key_name, depth + 2, k)
                yield from self.val_xobject.xml_out(self.val_name, depth + 2, v)
                yield f"{indent(depth + 1)}</{self.item_name}>"
        else:
            yield f"{indent(depth + 1)}<{self.item_name}>"
            yield from self.key_xobject.xml_out(self.key_name, depth + 2, None)
            yield from self.val_xobject.xml_out(self.val_name, depth + 2, None)
            yield f"{indent(depth + 1)}</{self.item_name}>"

        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> dict[Any, Any]:
        parsed = {}
        for child in obj.getchildren():
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

    def xml_out(
        self, name: str, depth: int, val: Any | None
    ) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{name}>"
        t = type(val)

        # even if None is a variant, ignore it - no point in displaying
        if t != NoneType and (val_xobj := self.xobjects.get(t)) is not None:
            yield from val_xobj.xml_out(self.elem_gen(t), depth + 1, val)

        yield f"{indent(depth)}<!-- This is a union, the following variants are possible"

        for t, xobj in self.xobjects.items():
            yield from xobj.xml_out(self.elem_gen(t), depth + 1, None)

        yield f"{indent(depth)}-->"
        yield f"{indent(depth)}</{name}>"

    def xml_in(self, obj: ObjectifiedElement) -> Any:
        for t, xobj in self.xobjects.items():
            if (obj := get(self.elem_gen(t))) is not None:
                return xobj.xml_in(obj)
        else:
            assert False, "Must have been part of the union"


class NoneObj(XObject):
    def xsd_out(
        self, name: str, depth: int, mods: dict[str, Any] = {}
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}{xcomment("None type")}'

    def xml_out(
        self, name: str, depth: int, val: Any | None
    ) -> Generator[str, None, None]:
        yield f'{indent(depth)}{xcomment("None type")}'

    def xml_in(self, obj: ObjectifiedElement) -> Any:
        return None


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
    elif data_type == NoneType:
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


def is_xmlified(cls):
    return hasattr(cls, "xmlified")


@dataclass_transform()
def xmlify(cls: type) -> type:
    if not is_dataclass(cls):
        assert False, "must be a dataclass"

    cls_name = cls.__name__
    forward_decs = {cls}
    meta_xobjects = [
        (f, gen_xobject(f.type, forward_decs)) for f in fields(cls)
    ]

    class UserXObject(XObject):
        def xsd_out(
            self, name: str, depth: int, mods: dict[str, Any] = {}
        ) -> Generator[str, None, None]:
            yield f'{indent(depth)}<{GNS_POST}element name="{name}" type="{cls_name}"{stringify_mods(mods)} />'

        def xml_out(
            self, name: str, depth: int, val: Any | None
        ) -> Generator[str, None, None]:
            yield f"{indent(depth)}<{name}>"
            if val is not None:
                for m, xobj in meta_xobjects:
                    yield from xobj.xml_out(m.name, depth + 1, get(val, m.name))
            else:
                for m, xobj in meta_xobjects:
                    yield from xobj.xml_out(m.name, depth + 1, None)
            yield f"{indent(depth)}</{name}>"

        def xml_in(self, obj: ObjectifiedElement) -> Any:
            parsed: dict[str, Any] = {}
            for m, xobj in meta_xobjects:
                if (m_obj := get(obj, m.name)) is not None:
                    parsed[m.name] = xobj.xml_in(m_obj)
                else:
                    assert False, "member is not present!"
            return cls(**parsed)

    cls_xobject = UserXObject()

    def xsd_forward(depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<{GNS_POST}complexType name="{cls_name}">'
        yield f"{indent(depth+1)}<{GNS_POST}sequence>"
        for m, xobj in meta_xobjects:
            yield from xobj.xsd_out(m.name, depth + 2, {})
        yield f"{indent(depth+1)}</{GNS_POST}sequence>"
        yield f"{indent(depth)}</{GNS_POST}complexType>"

    def xsd_dependencies() -> set[type]:
        return forward_decs

    def get_xobject():
        return cls_xobject

    def xsd_conf(
        schema_name: str,
        xmlns: str = "http://www.w3.org/2001/XMLSchema",
        options: dict[str, str] = {},
        imports: dict[str, str] = {},
    ) -> Generator[str, None, None]:
        # yield '<?xml version="1.0" encoding="utf-8"?>'
        options_str = "".join(f' {k}="{v}"' for k, v in options.items())
        yield f'<{GNS_POST}schema xmlns{GNS_PRE}="{xmlns}"{options_str}>'
        for ns, schloc in imports.items():
            yield f'{indent(1)}<import namespace="{ns}" schemaLocation="{schloc}"/>'
        yield f""

        visited: set[type] = set()
        dec_order: list[type] = []

        def toposort(curr: type, visited: set[type], dec_order: list[type]):
            visited.add(curr)
            deps = curr.xsd_dependencies()
            for d in deps:
                if d not in visited:
                    toposort(d, visited, dec_order)
            dec_order.append(curr)

        toposort(cls, visited, dec_order)

        for dec in dec_order:
            yield from dec.xsd_forward(1)
            yield f""

        yield from cls_xobject.xsd_out(schema_name, 1)
        yield f"</{GNS_POST}schema>"

    def xml_template(
        schema_name: str, xmlns: str, val: Any | None = None
    ) -> Generator[str, None, None]:
        # yield f'<?xml version="1.0" encoding="utf-8"?>'
        yield from cls_xobject.xml_out(schema_name, 0, val)

    def xml_template_values(
        self, schema_name: str, xmlns: str
    ) -> Generator[str, None, None]:
        return xml_template(schema_name, xmlns, self)

    cls.xsd_forward = xsd_forward
    cls.xsd_dependencies = xsd_dependencies
    cls.get_xobject = get_xobject
    cls.xsd_conf = xsd_conf
    cls.xml_template = xml_template
    cls.xmlified = True
    setattr(
        cls, "xml_template_values", xml_template_values
    )  # needs to use self to get values
    return cls
