import inspect
import traceback
from typing import Optional

from .settings import app_settings


def _assert(condition: bool, message: str = "") -> Optional[bool]:
    """
    NORMAL: print traceback and return false if condition is false.
    DEBUG: Occur AssertionException if condition is false.

    return: True if condition is true, false otherwise. In debug mode, the AssertException is raised.
    """
    if not app_settings.LETSUR_DEBUG and not condition:
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        line_number = frame.f_lineno
        print(
            f"CRITICAL: Assertion error occur. {filename}:{line_number}\nmsg: {message}"
        )
        traceback.print_stack()
        return False

    assert condition, message
    return True
