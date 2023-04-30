from dataclasses import dataclass
from lxml.objectify import ObjectifiedElement
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


# TODO: Custom traceback to point to location in the file
class XError(Exception):
    def __init__(self, short: str, what: str, why: str, ctx: XErrorCtx | None):
        super().__init__(colored(short, "red", attrs=["blink"]))
        self.add_note(colored("What:  " + what, "blue"))
        self.add_note(colored("Why:   " + why, "yellow"))
        if ctx is not None:
            self.add_note(
                colored("Where: In XML: ", "magenta")
                + trace_note(ctx.trace, "light_magenta", "light_cyan")
            )
