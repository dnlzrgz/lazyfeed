from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class HelpData:
    """
    Data related to a widget to be displayed in the help modal.
    """

    # Title of the widget.
    title: str = field(default="")

    # Description in markdown format.
    description: str = field(default="")


@runtime_checkable
class Helpable(Protocol):
    """
    Protocol for widgets that contain information required by the
    help modal.
    """

    help: HelpData
