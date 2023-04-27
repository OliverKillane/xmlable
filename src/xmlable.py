from dataclasses import dataclass
from abc import ABC, abstractmethod
import sys
from typing import Any, Callable, Generator, TypeVar, get_args
from types import FunctionType
from inspect import getmembers, getmodule, isclass, cleandoc, stack
from lxml.objectify import ObjectifiedElement
from lxml.etree import tostring

# Utilities
T = TypeVar("T")


def some_or(data: T | None, alt: T):
    return data if data is not None else alt


N = TypeVar("N")
M = TypeVar("M")


def some_or_apply(data: N, fn: Callable[[N], M], alt: M):
    return fn(data) if data is not None else alt


# Exceptions


class NotAClassError(Exception):
    def __init__(self, attempted: object):
        message = (
            f"{attempted} is not a class, so cannot have xmlconfig derived"
        )
        super(NotAClassError, self).__init__(message)


class MemberNoType(Exception):
    def __init__(self, classname: str, member: str, value: Any):
        message = f"{classname}.{member} has value {value}, but no type from which to derive xml config. In class {classname}, use {member}: <type> = {value}"
        super(MemberNoType, self).__init__(message)


class CannotFindMember(Exception):
    def __init__(
        self, parent: ObjectifiedElement, membername: str, suggestion: str
    ):
        message = f"Could not find {membername} in {parent.tag}:\n{tostring(parent, pretty_print=True)!r}\n Should contain an element like: {suggestion}"
        super(CannotFindMember, self).__init__(message)


class SpuriousTag(Exception):
    def __init__(
        self, parent_name: str, collectionkind: str, tag: str, expected_tag: str
    ):
        message = f"Found tag {tag} in map {parent_name}, but all items in the {collectionkind} should be in elements with name {expected_tag}"
        super(SpuriousTag, self).__init__(message)


class UnsupportedType(Exception):
    def __init__(self, type_name):
        message = (
            f"There is no XMLify implementation for {stringify_type(type_name)}"
        )
        super(UnsupportedType, self).__init__(message)


def stringify_type(t: type) -> str:
    args = get_args(t)
    if len(args) == 0:
        return t.__name__
    else:
        arg_str: str = ", ".join([stringify_type(arg) for arg in args])
        return f"{t.__name__}[{arg_str}]"


class GenericMemberUnsupported(Exception):
    def __init__(self, classname: str, member_name: str, member_type: type):
        message = f"Generic User Classes such are not supported yet, hence {classname} cannot have member {member_name}: {stringify_type(member_type)}"
        super(GenericMemberUnsupported, self).__init__(message)


class GenericClassUnsupported(Exception):
    def __init__(self, classname: str, class_type: type):
        message = f"Generic user classes are not supported yet, hence class {classname} cannot have type {stringify_type(class_type)}"
        super(GenericClassUnsupported, self).__init__(message)


# XSD/XML object wrappers
def indent(depth: int) -> str:
    return " " * 2 * depth


class XSDObject(ABC):
    @abstractmethod
    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        """
        returns the set of type dependencies (other required complextypes
        from classes), and a generator to yield lines of xsd
        """
        pass

    @abstractmethod
    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        """
        Yields lines for generated xml (template)
        """
        pass

    @abstractmethod
    def parse_xml(self, parent: ObjectifiedElement) -> Any:
        """
        Parses xml to return the data type contained
        """
        pass


@dataclass
class BasicElement(XSDObject):
    """
    A basic element for included integer, float, string types
    """

    name: str
    data_type: str
    parse_fn: Callable[[str], Any]
    default_value: str | None = None

    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<element name="{self.name}" type="{self.data_type}"/>'

    def _xml_suggestion(self) -> str:
        value_text: str = some_or(self.default_value, "!FILL ME!")
        return f"<{self.name}> {value_text} <{self.name}/>"

    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        yield indent(depth) + self._xml_suggestion()

    def parse_xml(self, parent: ObjectifiedElement) -> Any:
        obj = parent.find(self.name)
        if obj is None:
            raise CannotFindMember(parent, self.name, self._xml_suggestion())
        else:
            return self.parse_fn(obj)


class Sequence(XSDObject):
    """
    Wrapper for an xsd sequence
    - takes variable args (a tuple)
    - returns a tuple of objects parsed
    """

    def __init__(self, *args: XSDObject):
        self.children: tuple[XSDObject, ...] = args

    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<sequence>"
        for child in self.children:
            for line in child.generate_xsd(depth + 1):
                yield line
        yield f"{indent(depth)}</sequence>"

    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        """Yields lines for generated xml (template)"""
        for child in self.children:
            for line in child.generate_xml(depth):
                yield line

    def parse_xml(self, parent: ObjectifiedElement) -> tuple[Any, ...]:
        return (*(child.parse_xml(parent) for child in self.children),)


@dataclass
class Comment(XSDObject):
    comment: str

    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<!-- {self.comment} -->"

    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<!-- (From XSD) {self.comment} -->"

    def parse_xml(self, _: ObjectifiedElement) -> None:
        return None


@dataclass
class Map(XSDObject):
    """
    An xml/xsd representation of a map with unique keys
    - Order does not matter
    - A single key and value are used for the inner type.
    - Additional keys and values are used only in xml output
    """

    name: str
    key: XSDObject
    value: XSDObject
    additional_items: tuple[tuple[XSDObject, XSDObject], ...] = ()
    element_name: str = "entry"

    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<element name="{self.name}">'
        yield f"{indent(depth + 1)}<complexType>"
        yield f"{indent(depth + 2)}<sequence>"
        yield f'{indent(depth + 3)}<element name="{self.element_name}" minOccurs="0" maxOccurs="unbounded">'
        yield f"{indent(depth + 4)}<complexType>"
        for line in self.key.generate_xsd(depth + 5):
            yield line
        for line in self.value.generate_xsd(depth + 5):
            yield line
        yield f"{indent(depth + 4)}</complexType>"
        yield f"{indent(depth + 3)}</element>"
        yield f"{indent(depth + 2)}</sequence>"
        yield f"{indent(depth + 1)}</complexType>"
        yield f"{indent(depth)}</element>"

    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{self.name}>"

        # NOTE: Side rant about how many languages use '(' for expressions AND tuples
        #       A single element tuple is (e,) an expression is (e)
        #       When using * to expand the tuple below:
        #       ((a,b), t := *((1,2)))  = ((a,b), 1, 2)
        #       ((a,b), t := *((1,2),)) = ((a, b), (1, 2))
        #       Because the 'length' of t is determined at runtime, I must be
        #       careful to add an extra comma to prevent brackets being for
        #       expression
        #
        #       Haskell has this, Rust has this (with cringe (T,) type syntax)
        #       Especially cringe for rust as block are already expressions
        #       '{ exp }', so why the need to overload '(' ')'  SILLY!
        for k, v in (self.key, self.value), *self.additional_items:
            yield f"{indent(depth+1)}<{self.element_name}>"
            for line in k.generate_xml(depth + 2):
                yield line
            for line in v.generate_xml(depth + 2):
                yield line
            yield f"{indent(depth+1)}</{self.element_name}>"
        yield f"{indent(depth)}</{self.name}>"

    def parse_xml(self, parent: ObjectifiedElement) -> dict[Any, Any]:
        obj = parent.find(self.name)
        if obj is None:
            suggestion: str = "\n" + "\n".join(self.generate_xml(0))
            raise CannotFindMember(parent, self.name, suggestion)

        items: dict[Any, Any] = {}
        for child in obj.iterchildren():
            if child.tag != self.element_name:
                raise SpuriousTag(
                    parent_name=self.name,
                    collectionkind="dictionary",
                    tag=child.tag,
                    expected_tag=self.element_name,
                )
            else:
                key = self.key.parse_xml(child)
                value = self.value.parse_xml(child)
                items[key] = value

        return items


@dataclass
class List(XSDObject):
    """
    A list representation in xml
    - Each item has 'element_name', internally they will wrap with the same name again
      This is awkward, but because the children parse based on parent, and parents have identical
      names, we must wrap twice (let item parser see from inner)
    - Like with Map, additional defaults can be provided
    """

    name: str
    item: XSDObject
    element_name: str = "item_wrapper"
    additional_items: tuple[XSDObject, ...] = ()

    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<element name="{self.name}">'
        yield f"{indent(depth + 1)}<complexType>"
        yield f"{indent(depth + 2)}<sequence>"
        yield f'{indent(depth + 3)}<element name="{self.element_name}" minOccurs="0" maxOccurs="unbounded">'
        yield f"{indent(depth + 4)}<complexType>"
        for line in self.item.generate_xsd(depth + 5):
            yield line
        yield f"{indent(depth + 4)}</complexType>"
        yield f"{indent(depth + 3)}</element>"
        yield f"{indent(depth + 2)}</sequence>"
        yield f"{indent(depth + 1)}</complexType>"
        yield f"{indent(depth)}</element>"

    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        yield f"{indent(depth)}<{self.name}>"
        yield f"{indent(depth+1)}<{self.element_name}>"
        for item in self.item, *self.additional_items:
            for line in item.generate_xml(depth + 2):
                yield line
        yield f"{indent(depth+1)}</{self.element_name}>"
        yield f"{indent(depth)}</{self.name}>"

    def parse_xml(self, parent: ObjectifiedElement) -> list[Any]:
        obj = parent.find(self.name)
        if obj is None:
            suggestion: str = "\n" + "\n".join(self.generate_xml(0))
            raise CannotFindMember(parent, self.name, suggestion)

        items: list[Any] = []
        for child in obj.iterchildren():
            if child.tag != self.element_name:
                raise SpuriousTag(
                    parent_name=self.name,
                    collectionkind="list",
                    tag=child.tag,
                    expected_tag=self.element_name,
                )
            else:
                items.append(self.item.parse_xml(child))

        return items


@dataclass
class ComplexTypeDecl(XSDObject):
    name: str
    members: Sequence

    def generate_xsd(self, depth: int) -> Generator[str, None, None]:
        yield f'{indent(depth)}<complexType name="{self.name}">'
        for line in self.members.generate_xsd(depth + 1):
            yield line
        yield f"{indent(depth)}</complexType>"

    def generate_xml(self, depth: int) -> Generator[str, None, None]:
        for line in self.members.generate_xml(depth):
            yield line

    def parse_xml(self, parent: ObjectifiedElement) -> Any:
        assert False, "Not Implemented yet"


# Class metadata handling


@dataclass
class MemberMeta:
    """
    An easy wrapper of metadata for a class member (as used by ClassMeta)

    Attributes:
        doc: any comment associated with the member

    """

    name: str
    type: type
    default_value: Any | None

    def __str__(self) -> str:
        dval: str = some_or_apply(
            self.default_value, lambda x: " = " + str(x), ""
        )
        return f"{self.name}: {self.type.__name__}{dval}"


@dataclass
class ClassMeta:
    """
    An easy wrapper of metadata for a class.

    Attributes:
        cls:     The class object/type
        name:    String name of the class
        supers:  The cuper classes (not including itself or object), in the order of inheritance/MRO
        members: All type annotated attributes, in the order of declaration
    """

    cls: type
    doc: str | None
    name: str
    supers: list[type]
    members: list[MemberMeta]

    def __str__(self) -> str:
        members: str = "\n".join([f"\t{member}" for member in self.members])
        supers: str = (
            "(" + ", ".join([cls.__name__ for cls in self.supers]) + ")"
            if len(self.supers) > 0
            else ""
        )
        doc = f'\t"""{self.doc}"""\n' if self.doc is not None else ""
        return f"class {self.name}{supers}:\n{doc}{members}"


def get_metadata(cls: type) -> ClassMeta:
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

    # check none without annotations
    for m, d in defined_members.items():
        if m not in member_annos:
            raise MemberNoType(classname=name, member=m, value=d)

    members = []
    for m, t in member_annos.items():
        members.append(
            MemberMeta(name=m, type=t, default_value=defined_members.get(m))
        )

    # using method resolution order to get supers
    supers: list[type] = [
        sc for sc in cls.__mro__ if sc != object and sc != cls
    ]

    doc: str | None = cls.__doc__
    if doc is not None:
        doc = cleandoc(doc)

    return ClassMeta(cls, doc, name, supers, members)


def is_xmlified_class(cls: type):
    # TODO: Hacky and I dislike, but works
    try:
        cls.get_xmlify()
        print(f"{cls.__name__} is xmlified!!!!!")
        return True
    except AttributeError:
        print(f"{cls} is not xmlified")
        return False


def get_xsd_member(m: MemberMeta) -> XSDObject:
    basic_types: dict[type, str] = {
        int: "xs:integer",
        str: "xs:string",
        float: "xs:decimal",
        bool: "xs:boolean",
    }

    if (type_name := basic_types.get(m.type)) is not None:
        return BasicElement(
            name=m.name,
            data_type=type_name,
            parse_fn=m.type,
            default_value=m.default_value,
        )
    elif m.type == dict:
        # Note: types are from __anotations__ and have not had args erased, so this pattern is irrefutable
        (key_type, value_type) = get_args(m.type)

        # default_value is of type dict so {} and has len
        if m.default_value is None or len(m.default_value) == 0:
            key_xsd: XSDObject = get_xsd_member(
                MemberMeta(name="key", type=key_type, default_value=None)
            )
            value_xsd: XSDObject = get_xsd_member(
                MemberMeta(name="value", type=value_type, default_value=None)
            )
            return Map(name=m.name, key=key_xsd, value=value_xsd)
        else:
            [(first_k, first_v), *kv_additions] = [
                (
                    get_xsd_member(
                        MemberMeta(
                            name="key", type=key_type, default_value=key_default
                        )
                    ),
                    get_xsd_member(
                        MemberMeta(
                            name="value",
                            type=value_type,
                            default_value=value_default,
                        )
                    ),
                )
                for key_default, value_default in m.default_value.items()
            ]

            return Map(
                name=m.name,
                key=first_k,
                value=first_v,
                additional_items=tuple(kv_additions),
            )
    elif m.type == list:
        (item_type,) = get_args(m.type)

        if m.default_value is None or len(m.default_value) == 0:
            item_xsd: XSDObject = get_xsd_member(
                MemberMeta(name="item", type=item_type, default_value=None)
            )
            return List(name=m.name, item=item_xsd)
        else:
            [first_item, *item_additions] = [
                get_xsd_member(
                    MemberMeta(name="item", type=item_type, default_value=d_val)
                )
                for d_val in m.default_value
            ]
            return List(
                name=m.name,
                item=first_item,
                additional_items=tuple(item_additions),
            )
    elif is_xmlified_class(m.type):
        if len(get_args(m.type)) > 0:
            # This case is not caught, but will eventually be using GenericMemberUnsupported
            assert False, "TODO: fix this!"
        # User class default values are unsupported
        return BasicElement(
            name=m.name,
            data_type=m.type.__name__,
            parse_fn=m.type.get_xmlify().parse_xml,  # type: ignore
            default_value=None,
        )
    else:
        raise UnsupportedType(m.type)


def xmlify(cls):
    cls_md = get_metadata(cls)

    def get_xmlify() -> XSDObject:
        return ComplexTypeDecl(
            name=cls_md.name,
            members=Sequence(*(get_xsd_member(m) for m in cls_md.members)),
        )

    cls.get_xmlify = get_xmlify

    return cls


def xmlify_main(file):
    def subfun(cls):
        frm = stack()[1]
        mod = getmodule(frm[0])
        print(__name__)
        for other_cls in getmembers(mod, predicate=isclass):
            if is_xmlified_class(other_cls):
                for x in other_cls.get_xmlify().generate_xsd(0):
                    print(x)

        print(get_metadata(cls))
        print(f"FILE: {file}")

        return cls

    return subfun
