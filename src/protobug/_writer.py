from __future__ import annotations

import dataclasses
import io
import typing

from protobug._core import _NAME_LOOKUP_NAME
from protobug._core import ProtoMode
from protobug._core import ProtoType
from protobug._core import WireType
from protobug._core import _double_struct
from protobug._core import _float_struct
from protobug._core import signed_to_zigzag

if typing.TYPE_CHECKING:
    from protobug._core import ProtoConversionInfo


class Writer:
    def __init__(self, writer: io.BufferedIOBase, /):
        self._position = 0
        self._writer = writer

    def write(self, value: typing.Any, /) -> int:
        # TODO(Grub4K): add support to write plain dict using a `py_type`
        py_type = type(value)
        schema: dict[str, ProtoConversionInfo] | None = getattr(
            py_type, _NAME_LOOKUP_NAME, None
        )
        if not schema:
            msg = f"not a valid protobuf type: {py_type}"
            raise TypeError(msg)

        size = 0
        for field in dataclasses.fields(value):
            conversion_info = schema[field.name]
            # Check if this field is defaulted
            field_value = getattr(value, conversion_info.name)
            if conversion_info.proto_mode is ProtoMode.Optional and (
                field_value == field.default or field_value is None
            ):
                continue

            if isinstance(field_value, list):
                if (
                    conversion_info.proto_mode is ProtoMode.Packed
                    and len(field_value) > 2
                ):
                    # hahahahahahahahahahahahahahahahahahahahaha
                    with io.BytesIO() as buffer:
                        writer = Writer(buffer)
                        for item in field_value:
                            writer.write_type(item, conversion_info.proto_type)
                        data = buffer.getvalue()

                    size += self.write_tag(conversion_info.pid, WireType.LEN)
                    size += self.write_varint(len(data))
                    size += self._writer.write(data)
                    continue

                for item in field_value:
                    size += self.write_tag(
                        conversion_info.pid,
                        conversion_info.proto_type.wire_type(),
                    )
                    size += self.write_type(item, conversion_info.proto_type)
                continue

            if isinstance(field_value, dict):
                for k, v in field_value.items():
                    map_item = conversion_info.py_type(k, v)
                    size += self.write_tag(conversion_info.pid, WireType.LEN)
                    size += self.write_type(map_item, ProtoType.Embed)
                continue

            size += self.write_tag(
                conversion_info.pid,
                conversion_info.proto_type.wire_type(),
            )
            size += self.write_type(field_value, conversion_info.proto_type)

        return size

    def write_type(self, value: typing.Any, proto_type: ProtoType, /) -> int:
        if proto_type in (
            ProtoType.Int32,
            ProtoType.Int64,
            ProtoType.UInt32,
            ProtoType.UInt64,
            ProtoType.SInt32,
            ProtoType.SInt64,
            ProtoType.Enum,
        ):
            assert isinstance(value, int), f"{type(value)=}"
            if proto_type in (ProtoType.Int32, ProtoType.Enum, ProtoType.Int64):
                if value < 0:
                    value += 1
                    value += (
                        0xFFFFFFFF_FFFFFFFF
                        if proto_type is ProtoType.Int64
                        else 0xFFFFFFFF
                    )
            elif proto_type in (ProtoType.SInt32, ProtoType.SInt64):
                value = signed_to_zigzag(value)
            else:
                assert value >= 0
            return self.write_varint(value)

        if proto_type is ProtoType.Bool:
            assert isinstance(value, bool)
            value = b"\x01" if value else b"\x00"

        elif proto_type is ProtoType.Float:
            assert isinstance(value, float)
            value = _float_struct.pack(value)

        elif proto_type is ProtoType.Double:
            assert isinstance(value, float)
            value = _double_struct.pack(value)

        elif proto_type in (
            ProtoType.Fixed32,
            ProtoType.Fixed64,
            ProtoType.SFixed32,
            ProtoType.SFixed64,
        ):
            assert isinstance(value, int)
            if proto_type in (ProtoType.Fixed32, ProtoType.Fixed64):
                assert value >= 0
            length = 4 if proto_type in (ProtoType.Fixed32, ProtoType.SFixed32) else 8
            value = value.to_bytes(length, "little", signed=True)

        elif proto_type is ProtoType.String:
            assert isinstance(value, str)
            value = value.encode()

        elif proto_type is ProtoType.Embed:
            # TODO(Grub4K): """streaming""" writer, he says
            value = dumps(value)

        assert isinstance(value, bytes)
        size = 0
        if proto_type.wire_type() is WireType.LEN:
            size += self.write_varint(len(value))
        size += self._writer.write(value)
        return size

    def write_tag(self, pid: int, wire_type: WireType, /) -> int:
        result = (pid << 3) | wire_type
        return self.write_varint(result)

    def write_varint(self, value: int, /) -> int:
        size = ((value.bit_length() - 1) // 7 + 1) or 1
        buffer = bytearray(size)

        for i in range(size - 1):
            buffer[i] = (value & 0b0111_1111) | 0b1000_0000
            value >>= 7

        buffer[-1] = value
        return self._writer.write(buffer)


def dump(data: typing.Any, file: io.BufferedIOBase, /) -> int:
    return Writer(file).write(data)


def dumps(data: typing.Any, /) -> bytes:
    with io.BytesIO() as buffer:
        Writer(buffer).write(data)
        return buffer.getvalue()
