from typing import Callable
from functools import wraps
from textual.widgets.data_table import RowDoesNotExist, CellDoesNotExist


def fetch_guard(func: Callable) -> Callable:
    """
    Decorator to prevent multiple fetch request at the same time and
    avoid executing certain actions while a fetch is in progress.
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if self.is_fetching:
            self.notify(
                "a data refresh is in progress... please wait until it finishes",
                severity="warning",
            )
            return

        return await func(self, *args, **kwargs)

    return wrapper


def rollback_session(
    error_message: str = "",
    severity: str = "error",
    callback: Callable | None = None,
) -> Callable:
    """
    Decorator to handle exceptions and perform a rollback if needed. It also
    notifies the user with an error message and, if specified, executes a callback
    function at the end.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except (RowDoesNotExist, CellDoesNotExist):
                pass
            except Exception as e:
                self.session.rollback()
                message = (
                    f"{error_message}: {e}"
                    if error_message
                    else f"something went wrong: {e}"
                )
                self.notify(message, severity=severity)
            finally:
                if callback:
                    callback(self)

        return wrapper

    return decorator
