# XMLable

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

## XSD

Using the [w3 schema spec](https://www.w3.org/TR/xmlschema11-1/).
