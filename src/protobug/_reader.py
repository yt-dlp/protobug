from __future__ import annotations

import io
import typing

from protobug._core import _PID_LOOKUP_NAME
from protobug._core import ProtoType
from protobug._core import WireType
from protobug._core import _double_struct
from protobug._core import _float_struct
from protobug._core import _MapBase
from protobug._core import zigzag_to_signed

if typing.TYPE_CHECKING:
    from protobug._core import ProtoConversionInfo

    T = typing.TypeVar("T")


class Reader:
    def __init__(self, reader: io.BufferedIOBase, /):
        self._position = 0
        self._reader = reader

    @typing.overload
    def read(self, py_type: T, /, *, length: int | None = None) -> T: ...

    @typing.overload
    def read(self, /, *, length: int | None = None) -> dict[int, list]: ...

    def read(  # type: ignore
        self, py_type: type | None = None, /, *, length: int | None = None
    ) -> typing.Any:
        schema: dict[int, ProtoConversionInfo] | None = None
        if py_type is not None:
            schema = getattr(py_type, _PID_LOOKUP_NAME, None)
            if not schema:
                msg = f"not a valid protobuf type: {py_type}"
                raise TypeError(msg)

        begin = self._position
        expected_position = begin + (length or 0)

        result: dict[int, list] = {}
        named_result: dict[str, typing.Any] = {}
        while length is None or self._position < expected_position:
            try:
                key, value = self.read_record(schema)
                conversion_info = schema.get(key) if schema is not None else None
                if conversion_info is None:
                    # We could guess here if we have type info from other sources?
                    if key not in result:
                        result[key] = []
                    if isinstance(value, list):
                        result[key].extend(value)
                    else:
                        result[key].append(value)

                else:
                    name = conversion_info.name
                    if isinstance(value, list):
                        if not value:
                            continue
                        if isinstance(value[0], _MapBase):
                            target = named_result.setdefault(name, {})
                            for item in value:
                                if not isinstance(item, _MapBase):
                                    msg = f"inconsistent value types: expected Map, got {type(item)}"
                                    raise TypeError(msg)
                                target[item.key] = item.value
                        else:
                            named_result.setdefault(name, []).extend(value)

                    elif isinstance(value, _MapBase):
                        named_result.setdefault(name, {})[value.key] = value.value

                    else:
                        named_result[name] = value

            except EOFError:
                break

        if length is not None and self._position != expected_position:
            msg = f"non matching data length: expected {length}, got {self._position - begin}"
            raise ValueError(msg)

        if py_type is None:
            return result
        result_type = py_type(**named_result)
        result_type._unknown = result
        return result_type

    def read_record(
        self, schema: dict[int, ProtoConversionInfo] | None = None, /
    ) -> tuple[int, typing.Any]:
        key, wire_type = self.read_tag()
        info = schema.get(key) if schema is not None else None
        if info is None:
            # We have no info on this key, read the raw value
            return key, self.read_value(wire_type)

        expected_wire_type = info.proto_type.wire_type()
        if not info.proto_mode.is_multiple():
            # Single item, read and decode type
            if wire_type is not expected_wire_type:
                msg = (
                    f"unexpected value type for {info.name}: "
                    f"expected {expected_wire_type}, got {wire_type}"
                )
                raise ValueError(msg)
            return key, self.read_type(info.proto_type, info.py_type)

        if wire_type is expected_wire_type:
            # single, repeated, non-packed value, wrap in list
            return key, [self.read_type(info.proto_type, info.py_type)]

        if wire_type is not WireType.LEN:
            expected_type_msg = (
                str(WireType.LEN)
                if expected_wire_type is WireType.LEN
                else f"{expected_wire_type} or {WireType.LEN}"
            )
            msg = f"unexpected value type for {info.name}: expected {expected_type_msg}, got {wire_type}"
            raise ValueError(msg)

        # iteratively decode until we reach length
        length: int = self.read_value(WireType.VARINT)  # type: ignore
        begin = self._position
        expected_position = begin + length

        results = []
        while self._position < expected_position:
            results.append(self.read_type(info.proto_type, info.py_type))

        if self._position != expected_position:
            msg = f"non-matching packed length: expected {length}, got {self._position - begin}"
            raise ValueError(msg)

        return key, results

    def read_type(
        self, proto_type: ProtoType, py_type: type | None = None, /
    ) -> typing.Any:
        if proto_type is ProtoType.Embed:
            assert py_type is not None, "py_type is required when passing _PType.Embed"
            length: int = self.read_value(WireType.VARINT)  # type: ignore
            return self.read(py_type, length=length)

        value = self.read_value(proto_type.wire_type())
        if proto_type is ProtoType.Enum:
            return value if py_type is None else py_type(value)

        if proto_type in (
            ProtoType.Bytes,
            ProtoType.Int32,
            ProtoType.Int64,
            ProtoType.UInt32,
            ProtoType.UInt64,
        ):
            return value

        if proto_type is ProtoType.Bool:
            assert isinstance(value, int)
            return bool(value)

        if proto_type is ProtoType.String:
            assert isinstance(value, bytes)
            return value.decode()

        if proto_type is ProtoType.Float:
            assert isinstance(value, bytes)
            return _float_struct.unpack(value)[0]

        if proto_type is ProtoType.Double:
            assert isinstance(value, bytes)
            return _double_struct.unpack(value)[0]

        if proto_type in (
            ProtoType.SInt32,
            ProtoType.SInt64,
            ProtoType.SFixed32,
            ProtoType.SFixed64,
        ):
            if proto_type in (ProtoType.SFixed32, ProtoType.SFixed64):
                assert isinstance(value, bytes)
                value = int.from_bytes(value, "little")
            assert isinstance(value, int)
            return zigzag_to_signed(value)

        if proto_type in (ProtoType.Fixed32, ProtoType.Fixed64):
            assert isinstance(value, bytes)
            return int.from_bytes(value, "little", signed=True)

        raise ValueError(f"invalid protobuf value: {value!r}")

    def read_value(self, wire_type: WireType, /) -> int | bytes:
        if wire_type in (WireType.SGROUP, WireType.EGROUP):
            # SGROUP and EGROUP are deprecated
            msg = f"{wire_type.name} is deprecated and not implemented"
            raise NotImplementedError(msg)

        if wire_type == WireType.VARINT:
            return self.read_varint()

        if wire_type == WireType.I64:
            size = 8
        elif wire_type == WireType.I32:
            size = 4
        else:
            size = self.read_varint()

        data = self._reader.read(size)
        length = len(data)
        self._position += length
        if length < size:
            msg = f"not enough data: expected {size}, got {length}"
            raise ValueError(msg)
        return data

    def read_tag(self, /) -> tuple[int, WireType]:
        value = self.read_varint()
        return value >> 3, WireType(value & 0b111)

    def read_varint(self, /) -> int:
        data = self._reader.read(1)
        if not data:
            raise EOFError
        self._position += 1

        byte = data[0]
        result = byte & 0b0111_1111
        shift = 7
        while byte & 0b1000_0000:
            data = self._reader.read(1)
            if not data:
                msg = "expected another byte but reached EOF"
                raise ValueError(msg)

            self._position += 1
            byte = data[0]
            result |= (byte & 0b0111_1111) << shift
            shift += 7

        return result


@typing.overload
def load(file: io.BufferedIOBase, py_type: type[T], /) -> T: ...


@typing.overload
def load(file: io.BufferedIOBase, py_type: None = None, /) -> dict: ...


def load(file: io.BufferedIOBase, py_type=None, /):  # type: ignore
    return Reader(file).read(py_type)


@typing.overload
def loads(data: bytes | bytearray | memoryview, py_type: type[T], /) -> T: ...


@typing.overload
def loads(data: bytes | bytearray | memoryview, py_type: None = None, /) -> dict: ...


def loads(data: bytes | bytearray | memoryview, py_type=None, /):  # type: ignore
    with io.BytesIO(data) as buffer:
        return Reader(buffer).read(py_type)
