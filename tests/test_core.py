from __future__ import annotations

import typing

import pytest

import protobug


class Test1:
    a: int = protobug.field(1)


class Test2:
    a: list = protobug.field(1)


class Test3:
    a: dict = protobug.field(1)


class Test4:
    a: protobug.Int32 = protobug.field(1)
    b: protobug.Int32 = protobug.field(1)


class Test5:
    a: protobug.Int32 = protobug.field(-1)


class Test6:
    a: typing.Optional[list[protobug.Int32]] = protobug.field(1)


class Test7:
    a: typing.Optional[dict[protobug.Int32, protobug.Int32]] = protobug.field(1)


message_type_errors_tests = [
    (
        Test1,
        TypeError("invalid field type"),
        "do not allow plain int as type",
    ),
    (
        Test2,
        TypeError("missing specialization"),
        "do not allow unspecialized list type",
    ),
    (
        Test3,
        TypeError("missing specialization"),
        "do not allow unspecialized dict type",
    ),
    (
        Test4,
        ValueError("duplicate id: 1"),
        "do not allow duplicate proto id",
    ),
    (
        Test5,
        ValueError("negative id not allowed: -1"),
        "do not allow negative proto id",
    ),
    (
        Test6,
        TypeError("remove the optional annotation"),
        "do not allow optional list",
    ),
    (
        Test7,
        TypeError("remove the optional annotation"),
        "do not allow optional dict",
    ),
]


@pytest.mark.parametrize(
    "py_type,error",
    [test[:-1] for test in message_type_errors_tests],
    ids=[test[-1] for test in message_type_errors_tests],
)
def test_message_type_errors(py_type: type, error: Exception) -> None:
    with pytest.raises(type(error), match=error.args[0]):
        protobug.message(py_type)


zigzag_tests = [
    (0, 0),
    (-1, 1),
    (1, 2),
    (-2, 3),
    (2, 4),
    (0x7FFFFFFF, 0xFFFFFFFE),
    (-0x80000000, 0xFFFFFFFF),
]


@pytest.mark.parametrize(
    "input,output",
    zigzag_tests,
    ids=[f"{a} to {b}" for a, b in zigzag_tests],
)
def test_signed_to_zigzag(input: int, output: int) -> None:
    assert protobug.signed_to_zigzag(input) == output


@pytest.mark.parametrize(
    "input,output",
    [(b, a) for a, b in zigzag_tests],
    ids=[f"{b} to {a}" for a, b in zigzag_tests],
)
def test_zigzag_to_signed(input: int, output: int) -> None:
    assert protobug.zigzag_to_signed(input) == output
