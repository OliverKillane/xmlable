"""
Colourful & descriptive errors for xmlable 
- Clear messages
- Trace for parsing
"""
from dataclasses import dataclass
from typing import Iterable
from termcolor import colored


def trace_note(trace: list[str], arrow_c: str, node_c: str):
    return colored(" > ", arrow_c).join(
        map(lambda x: colored(x, node_c), trace)
    )


@dataclass
class XErrorCtx:
    trace: list[str]

    def next(self, node: str):
        return XErrorCtx(trace=self.trace + [node])


# TODO: Custom backtrace to point to location in the file
class XError(Exception):
    def __init__(
        self,
        short: str,
        what: str,
        why: str,
        ctx: XErrorCtx | None = None,
        notes: Iterable[str] = [],
    ):
        super().__init__(colored(short, "red", attrs=["blink"]))
        self.add_note(colored("What:  " + what, "blue"))
        self.add_note(colored("Why:   " + why, "yellow"))
        if ctx is not None:
            self.add_note(
                colored("Where: ", "magenta")
                + trace_note(ctx.trace, "light_magenta", "light_cyan")
            )
        for note in notes:
            self.add_note(note)
