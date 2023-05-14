from dataclasses import dataclass
from xmlable import xmlify


# Some examples that will error


# not a dataclass
@xmlify
class NotDataclass:
    a: int


# uses comment
@xmlify
@dataclass
class ContainsComment:
    comment: str


# using non-mxmlified class
class NotXmlified:
    pass


@xmlify
@dataclass
class InvalidType:
    member: NotXmlified
