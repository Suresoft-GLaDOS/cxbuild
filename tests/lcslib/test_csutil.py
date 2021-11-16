import pytest
import cslib


# TODO: add negative cases..
@pytest.mark.parametrize("call_command", ["gcc", "gcc-10.1", "llvm-g++", "g++", "c++", "cc"])
def test_is_interest_call(call_command: str):
    assert cslib.csutil.is_interest_call(call_command)
