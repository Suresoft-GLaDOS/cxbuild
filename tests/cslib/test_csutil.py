import pytest
import cslib


# TODO: add negative cases..
@pytest.mark.parametrize("command,expected", [
    ("gcc", True),
    ("gcc-10.1", True),
    ("llvm-g++", True),
    ("g++", True),
    ("c++", True),
    ("cc", True),
    ("cc1", False)
])
def test_is_interest_call(command, expected):
    assert cslib.csutil.is_interest_call(command) == expected
