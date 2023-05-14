# XMLable

## An easy xml/xsd generator and parser for python dataclasses!

```python
@xmlify
@dataclass
class Config:
    date: str
    number_of_cores: int
    codes: list[int]
    show_logs: bool


write_file("config.xsd", Config.xsd())
write_file("config_xml_template.xml", Config.xml())

original = Config(
    date="31/02/2023",  # no validation yet :(
    number_of_cores=48,
    codes=[101, 345, 42, 67],
    show_logs=False,
)
write_file("config_xml_example.xml", original.xml_value())

read_config: Config = parse_file(Config, "config_xml_example.xml")

assert read_config == original
```

See more in [examples](examples/)

## Capabilities

### Types

Currently supports the types:

```python
int, float, str, dict, tuple, set, list, None
# as well as unions!
int | float | None
```

And dataclasses that have been `@xmlify`-ed.

These can be combined for types such as:

```python
@xmlify
@dataclass
class Complex:
    a: dict[tuple[int, str], list[tuple[dict[int, float | str], set[bool]]]]

c1 = Complex(
    a={(3, "hello"): [({3: 0.4}, {True, False}), ({2: "str"}, {False})]}
)
```

### Custom Classes

The xmlify interface can be implemented by adding methods described in [xmlify](src/xmlable/_xmlify.py)
Once the class `is_xmlified` it can be used just as if generated by `@xmlify`

```python
from xmlable._xobject import XObject
from xmlable._user import IXmlify
from xmlable._manual import manual_xmlify

@manual_xmlify
class MyClass(IXmlify):
    def get_xobject() -> XObject:
        class XMyClass(XObject):
            def xsd_out(self, name: str, attribs: dict[str, str] = {}, add_ns: dict[str, str] = {}) -> _Element:
                pass

            def xml_temp(self, name: str) -> _Element:
                pass

            def xml_out(self, name: str, val: Any, ctx: XErrorCtx) -> _Element:
                pass

            def xml_in(self, obj: ObjectifiedElement, ctx: XErrorCtx) -> Any:
                pass

        return XMyClass() # must be an instance of XMyClass, not the class

    def xsd_forward(add_ns: dict[str, str]) -> _Element:
        pass

    def xsd_dependencies() -> set[type]:
        return {MyClass}
```

See the [user define example](examples/userdefined) for implementation.

## Limitations

### Unions of Generic Types

Generating xsd works, parsing works, however generating an xml template can fail
if they type is not determinable at runtime.

- Values do not have type arguments carried with them
- Many types are indistinguishable in python

For example:

```python
@xmlify
@dataclass
class GenericUnion:
    u: dict[int, float] | dict[int, str]

GenericUnion(u={}) # which variant in the xml should {} have??
```

In this case an error is raised

## To Develop

```bash
git clone # this project

python3.11 -m venv ./.venv

source ./.venv/bin/activate # activate virtual environment

pip install .      # install this project in the venv
pip install .[dev] # install optional dev dependencies (mypy, black and pytest)

black . # to reformat
mypy    # type check
pytest  # to run tests
```

[Hatch](https://hatch.pypa.io/) is used for build.

## To Improve

### Fuzzing

(As a fun weekend project) generate arbitrary python data types with values, and dataclasses.
Then `@xmlify` all and validate as in the current tests

### Etree vs Objectify

Currently using objectify for parsing and etree for construction, I want to move parsing to use `etree`

- previously used objectify for quick prototype.
