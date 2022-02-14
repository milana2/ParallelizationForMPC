from typing import Any, NoReturn


# https://github.com/python/mypy/issues/5818#issue-372451340
def assert_never(x: Any) -> NoReturn:
    assert False, "Unhandled type: {}".format(type(x).__name__)
