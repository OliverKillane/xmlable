from typing import Any
from xmlable._xobject import is_xmlified, typename
from xmlable._errors import XError
from termcolor import colored
from lxml.objectify import parse as objectify_parse


def write_xsd(cls: type, file_path: str, schema_name: str | None = None):
    cls_name: str = typename(cls)
    if schema_name is None:
        schema_name = cls_name

    if not is_xmlified(cls):
        raise XError(
            short="Not Xmlified",
            what=f"{cls_name} is not xmlified, and hence cannot have an xsd written",
            why=f"the .xsd(...) method is required to write_xsd",
        ).add_note(f"To fix, try:\n@xmlify\n@dataclass\nclass {cls_name}: ...")

    print(
        colored(
            f"Overwriting {file_path} with xsd for {cls_name}...",
            "red",
            attrs=["blink"],
        )
    )
    with open(file=file_path, mode="w") as f:
        f.writelines(map(lambda s: s + "\n", cls.xsd(schema_name)))
    print(colored(f"Complete!", "green", attrs=["blink"]))


def write_xml(cls: type, file_path: str, schema_name: str | None = None):
    cls_name: str = typename(cls)
    if schema_name is None:
        schema_name = cls_name
    if not is_xmlified(cls):
        raise XError(
            short="Not Xmlified",
            what=f"{cls_name} is not xmlified, and hence cannot have an xml written",
            why=f"the .xml(...) method is required to write_xml",
        ).add_note(f"To fix, try:\n@xmlify\n@dataclass\nclass {cls_name}: ...")

    print(
        colored(
            f"Overwriting {file_path} with xml template for {cls_name}...",
            "red",
            attrs=["blink"],
        )
    )
    with open(file=file_path, mode="w") as f:
        f.writelines(map(lambda s: s + "\n", cls.xml(schema_name)))
    print(colored(f"Complete!", "green", attrs=["blink"]))


def write_xml_value(obj: Any, file_path: str, schema_name: str | None = None):
    cls = type(obj)
    cls_name: str = typename(cls)
    if schema_name is None:
        schema_name = cls_name
    if not is_xmlified(cls):
        raise XError(
            short="Not Xmlified",
            what=f"{cls_name} is not xmlified, and hence cannot have an xml value written",
            why=f"the .xml_value(...) method is required to write_xml_value",
        ).add_note(f"To fix, try:\n@xmlify\n@dataclass\nclass {cls_name}: ...")

    print(
        colored(
            f"Overwriting {file_path} with xml based on...\n{obj}",
            "red",
            attrs=["blink"],
        )
    )
    with open(file=file_path, mode="w") as f:
        f.writelines(map(lambda s: s + "\n", obj.xml_value(schema_name)))
    print(colored(f"Complete!", "green", attrs=["blink"]))


def parse_xml(cls: type, file_path: str) -> Any:
    with open(file=file_path, mode="r") as f:
        return cls.parse(objectify_parse(f).getroot())
