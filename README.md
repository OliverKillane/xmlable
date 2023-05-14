# XMLable

## What is this?

An easy xml/xsd config generator and parser for python dataclasses!

```python
@xmlify
@dataclass
class Config:
    date: str
    number_of_cores: int
    codes: list[int]
    show_logs: bool


write_xsd(Config, "config.xsd")
write_xml(Config, "config_xml_template.xml")
write_xml_value(
    Config(
        date="31/02/2023",  # no validation yet :(
        number_of_cores=48,
        codes=[101, 345, 42, 67],
        show_logs=False,
    ),
    "config_xml_example.xml",
)
config: Config = parse_file(Config, "config_xml_example.xml")
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

#### Custom Classes

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

-

### Limitations

#### Unions of Generic Types

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

## To Improve

### Better Namespaces

Lxml qualifies namespaces for element names, but not for other attributes.
As xsd types need to be qualified, and lxml will not, there are several options:

1. Always use no prefix as the xmlSchema, and add as an invariant to all code. [problematic as user may want to change prefix]
2. Create our own namespace resolution algo to traverse tree, determine what prefixes to use for what namespaces [complex and decide when to overwrite a custom xmlified object's chosen prefixes - an author may hardcode]
3. Use string for type, but add to element's namespace map so lxml can resolve properly. But if the user overwrites with their own prefix, both will be present for this element. [On balance best approach]

I chose option [3.] on balance, for example:

```python
Element('{http://www.w3.org/2001/XMLSchema}element', type="xs:integer", nsmap={'xs' : 'http://www.w3.org/2001/XMLSchema'})
```

Hence if we use a schema using `xsd`, it will declare the `xs` namespace at this interface (hence type string is valid), but continue to use `xsd` for everything else.
