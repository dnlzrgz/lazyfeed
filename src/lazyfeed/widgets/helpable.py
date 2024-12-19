from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class HelpData:
    title: str = field(default="")
    description: str = field(default="")


@runtime_checkable
class Helpable(Protocol):
    help: HelpData
