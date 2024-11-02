from __future__ import annotations

import io
import typing

import pytest

import protobug
import tests.model

T = typing.TypeVar("T")

test_data = [
    (
        tests.model.Message1(a=150),
        b"\x08\x96\x01",
        "single int should encode correctly",
    ),
    (
        tests.model.Message2(b="testing"),
        b"\x12\x07testing",
        "single string should encode correctly",
    ),
    (
        tests.model.Message3(c=tests.model.Message1(a=150)),
        b"\x1a\x03\x08\x96\x01",
        "embed message should encode correctly",
    ),
    (
        tests.model.Message5(f=[3, 270, 86942]),
        b"\x32\x06\x03\x8e\x02\x9e\xa7\x05",
        "list of int should encode correctly",
    ),
    (
        tests.model.Message5(f=[3, 270]),
        b"\x30\x03\x30\x8e\x02",
        "list of int should encode as repeated if <= 2",
    ),
    (
        tests.model.Message5(f=[3]),
        b"\x30\x03",
        "list of int should encode as repeated if <= 2",
    ),
    (
        tests.model.Message5(f=[]),
        b"",
        "list of int should encode as repeated if <= 2",
    ),
    (
        tests.model.Message4(d="hello", e=[1, 2, 3]),
        b"\x22\x05hello\x2a\x03\x01\x02\x03",
        "string and packed int should encode correctly",
    ),
    (
        tests.model.Message6(g={"a": 1, "b": 2, "c": 3}),
        b"\x3a\x05\x0a\x01a\x10\x01\x3a\x05\x0a\x01b\x10\x02\x3a\x05\x0a\x01c\x10\x03",
        "map should encode correctly",
    ),
    (
        tests.model.Message7(h=[tests.model.MessageEnum.B]),
        b"\x40\x01",
        "list of enum should encode correctly",
    ),
    (
        tests.model.Message8(i=1.0),
        b"\x4d\x00\x00\x80\x3f",
        "floats should encode correctly",
    ),
]


@pytest.mark.parametrize(
    "data,expected,msg",
    test_data,
    ids=[test[-1] for test in test_data],
)
def test_dump(
    data: typing.Any,
    expected: bytes | Exception,
    msg: str,
) -> None:
    py_type = type(data)
    msg = f"encoding from {py_type}"
    if isinstance(expected, Exception):
        with pytest.raises(type(expected), match=expected.args[0]):
            protobug.dumps(data)

    else:
        assert protobug.dumps(data) == expected, msg


def test_writer_behavior() -> None:
    with io.BytesIO() as buffer:
        protobug.dump(tests.model.Message1(), buffer)
        assert not buffer.closed, "buffer should not be closed after a dump"
