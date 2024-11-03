from __future__ import annotations

import io
import typing

import pytest

import protobug
import tests.model

T = typing.TypeVar("T")

test_data = [
    (
        b"\x08\x96\x01",
        tests.model.Message1,
        {1: [150]},
        tests.model.Message1(a=150),
        "single int should decode correctly",
    ),
    (
        b"\x12\x07testing",
        tests.model.Message2,
        {2: [b"testing"]},
        tests.model.Message2(b="testing"),
        "single string should decode correctly",
    ),
    (
        b"\x1a\x03\x08\x96\x01",
        tests.model.Message3,
        {3: [b"\x08\x96\x01"]},
        tests.model.Message3(c=tests.model.Message1(a=150)),
        "embed message should decode correctly",
    ),
    (
        b"\x22\x05hello\x28\x01\x28\x02\x28\x03",
        tests.model.Message4,
        {4: [b"hello"], 5: [1, 2, 3]},
        tests.model.Message4(d="hello", e=[1, 2, 3]),
        "string and repeated int should decode correctly",
    ),
    (
        b"\x28\x01\x28\x02\x28\x03\x22\x05hello",
        tests.model.Message4,
        {4: [b"hello"], 5: [1, 2, 3]},
        tests.model.Message4(d="hello", e=[1, 2, 3]),
        "out of order fields should decode correctly",
    ),
    (
        b"\x22\x05hello\x2a\x03\x01\x02\x03",
        tests.model.Message4,
        {4: [b"hello"], 5: [b"\x01\x02\x03"]},
        tests.model.Message4(d="hello", e=[1, 2, 3]),
        "string and packed int should decode correctly",
    ),
    (
        b"\x32\x06\x03\x8e\x02\x9e\xa7\x05",
        tests.model.Message5,
        {6: [b"\x03\x8e\x02\x9e\xa7\x05"]},
        tests.model.Message5(f=[3, 270, 86942]),
        "packed int should decode correctly",
    ),
    (
        b"\x32\x03\x03\x8e\x02\x30\x9e\xa7\x05",
        tests.model.Message5,
        {6: [b"\x03\x8e\x02", 86942]},
        tests.model.Message5(f=[3, 270, 86942]),
        "mixed packed and repeated int should decode correctly",
    ),
    (
        b"\x3a\x05\x0a\x01a\x10\x01\x3a\x05\x0a\x01b\x10\x02\x3a\x05\x0a\x01c\x10\x03",
        tests.model.Message6,
        {7: [b"\n\x01a\x10\x01", b"\n\x01b\x10\x02", b"\n\x01c\x10\x03"]},
        tests.model.Message6(g={"a": 1, "b": 2, "c": 3}),
        "map should decode correctly",
    ),
    (
        b"\x40\x01",
        tests.model.Message7,
        {8: [1]},
        tests.model.Message7(h=[tests.model.MessageEnum.B]),
        "list of enum should decode correctly",
    ),
    (
        b"\x4d\x00\x00\x80\x3f",
        tests.model.Message8,
        {9: [b"\x00\x00\x80\x3f"]},
        tests.model.Message8(i=1.0),
        "floats should decode correctly",
    ),
    (
        b"\x00\xff",
        tests.model.Message1,
        ValueError("expected another byte but reached EOF"),
        ValueError("expected another byte but reached EOF"),
        "cut off varint should raise an error",
    ),
    (
        b"\x3a\x05\x0a",
        tests.model.Message6,
        ValueError("not enough data"),
        ValueError("non matching data length"),
        "cut of embed should raise an error",
    ),
    (
        b"\x3a\x05",
        tests.model.Message6,
        ValueError("not enough data"),
        ValueError("non matching data length"),
        "cut of embed should raise an error",
    ),
]


@pytest.mark.parametrize(
    "data,py_type,expected_plain,expected_decoded,msg",
    test_data,
    ids=[test[-1] for test in test_data],
)
def test_load(
    data: bytes,
    py_type: type[T],
    expected_plain: dict | Exception,
    expected_decoded: T | Exception,
    msg: str,
) -> None:
    for decode_type, expected in [(None, expected_plain), (py_type, expected_decoded)]:
        msg = f"decoding to {decode_type or 'plain dict'}"
        if isinstance(expected, Exception):
            with pytest.raises(type(expected), match=expected.args[0]):
                protobug.loads(data, decode_type)

        else:
            result = protobug.loads(data, decode_type)
            assert result == expected, msg


def test_unknown_read() -> None:
    result = protobug.loads(b"\x08\x96\x01", tests.model.Message1)
    assert getattr(result, "_unknown") == {}

    result = protobug.loads(b"\x00\x00\x08\x96\x01\x00\x00", tests.model.Message1)
    assert getattr(result, "_unknown") == {0: [0, 0]}


def test_reader_behavior() -> None:
    with io.BytesIO() as buffer:
        protobug.load(buffer)
        assert not buffer.closed, "buffer should not be closed after a load"

    assert protobug.loads(memoryview(b"\x00\x00")) == {0: [0]}
    assert protobug.loads(bytearray(b"\x00\x00")) == {0: [0]}

    with io.BytesIO(b"\x00\x00\x01") as buffer:
        reader = protobug.Reader(buffer)
        assert reader.read_record() == (0, 0)
        assert buffer.tell() == 2
