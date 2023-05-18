""" 
The @manual_xmlify decorator used to add the .xsd, .xml, .xml_value and .parse 
methods to a class that already has .xsd_dependencies, .xsd_forward and 
.get_xobject
"""

from typing import Any
from lxml.etree import _Element, Element, _ElementTree, ElementTree
from lxml.objectify import ObjectifiedElement

from xmlable._utils import typename
from xmlable._lxml_helpers import with_children, XMLSchema
from xmlable._errors import XError, XErrorCtx


def validate_manual_class(cls: type):
    cls_name = typename(cls)
    attrs = {"get_xobject", "xsd_forward", "xsd_dependencies"}
    for attr in attrs:
        if not hasattr(cls, attr):
            all_attrs = ", ".join(attrs)
            raise XError(
                short="Missing Attribute",
                what=f"The attribute {attr} is missing from {cls_name}",
                why=f"To be manual_xmlified the attributes: {all_attrs} are required. Try using help(IXmlify)",
                ctx=XErrorCtx([cls_name]),
            )


def manual_xmlify(cls: type) -> type:
    """
    Generate the following methods:
    ```
    def xsd(
            id: str = cls_name,
            namespaces: dict[str, str] = {},
            imports: dict[str, str] = {},
        ) -> _ElementTree:
        # ...

    def xml(schema_name: str = cls_name) -> _ElementTree:
        # ...

    def xml_value(self, id: str = cls_name) -> _ElementTree:
        # ...

    def parse(obj: ObjectifiedElement) -> Any:
        # ...
    ```
    """
    try:
        validate_manual_class(cls)
        cls_name = typename(cls)

        cls_xobject = cls.get_xobject()  # type: ignore[attr-defined]

        def xsd(
            id: str = cls_name,
            namespaces: dict[str, str] = {},
            imports: dict[str, str] = {},
        ) -> _ElementTree:
            # Get dependencies (user classes that need to be declared before)
            visited: set[type] = set()
            dec_order: list[type] = []

            def toposort(curr: type, visited: set[type], dec_order: list[type]):
                visited.add(curr)
                deps = curr.xsd_dependencies()  # type: ignore[attr-defined]
                for d in deps:
                    if d not in visited:
                        toposort(d, visited, dec_order)
                dec_order.append(curr)

            toposort(cls, visited, dec_order)

            # Create forward declarations, potentially adding to namespaces
            decs: list[_Element] = [dec.xsd_forward(namespaces) for dec in dec_order]  # type: ignore[attr-defined]

            # generate main element (can add to namespaces)
            main_element = cls_xobject.xsd_out(id, add_ns=namespaces)

            return ElementTree(
                with_children(
                    Element(
                        f"{XMLSchema}schema",
                        id=id,
                        elementFormDefault="qualified",
                        nsmap=namespaces,
                    ),
                    [
                        Element(
                            f"{XMLSchema}import",
                            namespace=ns,
                            schemaLocation=sloc,
                        )
                        for ns, sloc in imports.items()
                    ]
                    + decs
                    + [main_element],
                )
            )

        def xml(schema_name: str = cls_name) -> _ElementTree:
            return ElementTree(cls_xobject.xml_temp(schema_name))

        def xml_value(self, id: str = cls_name) -> _ElementTree:
            return ElementTree(cls_xobject.xml_out(id, self, XErrorCtx([id])))

        def parse(obj: ObjectifiedElement) -> Any:
            return cls_xobject.xml_in(obj, XErrorCtx([obj.tag]))

        cls.xsd = xsd  # type: ignore[attr-defined]
        cls.xml = xml  # type: ignore[attr-defined]
        setattr(cls, "xml_value", xml_value)  # needs to use self to get values
        cls.parse = parse  # type: ignore[attr-defined]

        return cls
    except XError as e:
        # NOTE: Trick to remove dirty 'internal' traceback, and raise from
        #       xmlify (makes more sense to user than seeing internals)
        e.__traceback__ = None
        raise e
