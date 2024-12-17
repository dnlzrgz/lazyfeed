from typing import Callable
from functools import wraps


def rollback_session(
    error_message: str = "",
    severity: str = "error",
    callback: Callable | None = None,
):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
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
