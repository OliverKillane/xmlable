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
config: Config = parse_xml(Config, "config_xml_example.xml")
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

### Limitations

#### Unions of generic types cannot be created from objects

Generating xsd works, parsing works, however generating an xml template does not.

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

#### Error Messages

While many errors are caught and wrapped with helpful messages, type errors are not.

- Be careful with types, use mypy
- Type errors can propagate deep inside xmlable

#### Extensions and Imports

Easy to add, I made this over 3 days and didn't have time

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
