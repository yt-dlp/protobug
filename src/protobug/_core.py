from __future__ import annotations

import dataclasses
import enum
import struct
import sys
import typing

import protobug

_METADATA_TAG_NAME = f"__{protobug.__name__}_metadata"
_PID_LOOKUP_NAME = f"__{protobug.__name__}_pid_lookup"
_NAME_LOOKUP_NAME = f"__{protobug.__name__}_name_lookup"

_SLOT_ARGS = {"slots": True} if sys.version_info >= (3, 10) else {}

_float_struct = struct.Struct(b"<f")
_double_struct = struct.Struct(b"<d")

MISSING = dataclasses.MISSING


class WireType(enum.IntEnum):
    VARINT = 0
    I64 = 1
    LEN = 2
    SGROUP = 3
    EGROUP = 4
    I32 = 5

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


class ProtoMode(enum.Enum):
    Single = enum.auto()
    Optional = enum.auto()
    Packed = enum.auto()
    Repeated = enum.auto()

    def is_multiple(self, /) -> bool:
        return self is self.Packed or self is self.Repeated


class ProtoType(enum.Enum):
    Int32 = enum.auto()
    Int64 = enum.auto()
    UInt32 = enum.auto()
    UInt64 = enum.auto()
    SInt32 = enum.auto()
    SInt64 = enum.auto()
    Enum = enum.auto()
    Bool = enum.auto()

    Fixed32 = enum.auto()
    SFixed32 = enum.auto()
    Float = enum.auto()

    Fixed64 = enum.auto()
    SFixed64 = enum.auto()
    Double = enum.auto()

    String = enum.auto()
    Bytes = enum.auto()
    Embed = enum.auto()

    def wire_type(self, /) -> WireType:
        return {
            typing.cast(ProtoType, self.Int32): WireType.VARINT,
            typing.cast(ProtoType, self.Int64): WireType.VARINT,
            typing.cast(ProtoType, self.UInt32): WireType.VARINT,
            typing.cast(ProtoType, self.UInt64): WireType.VARINT,
            typing.cast(ProtoType, self.SInt32): WireType.VARINT,
            typing.cast(ProtoType, self.SInt64): WireType.VARINT,
            typing.cast(ProtoType, self.Enum): WireType.VARINT,
            typing.cast(ProtoType, self.Bool): WireType.VARINT,
            typing.cast(ProtoType, self.Fixed32): WireType.I32,
            typing.cast(ProtoType, self.SFixed32): WireType.I32,
            typing.cast(ProtoType, self.Float): WireType.I32,
            typing.cast(ProtoType, self.Fixed64): WireType.I64,
            typing.cast(ProtoType, self.SFixed64): WireType.I64,
            typing.cast(ProtoType, self.Double): WireType.I64,
            typing.cast(ProtoType, self.Bytes): WireType.LEN,
            typing.cast(ProtoType, self.String): WireType.LEN,
            typing.cast(ProtoType, self.Embed): WireType.LEN,
        }[self]


# VARINT
Int32 = typing.Annotated[int, ProtoType.Int32]
Int64 = typing.Annotated[int, ProtoType.Int64]
UInt32 = typing.Annotated[int, ProtoType.UInt32]
UInt64 = typing.Annotated[int, ProtoType.UInt64]
SInt32 = typing.Annotated[int, ProtoType.SInt32]
SInt64 = typing.Annotated[int, ProtoType.SInt64]
Bool = typing.Annotated[bool, ProtoType.Bool]
# I64
Fixed64 = typing.Annotated[int, ProtoType.Fixed64]
SFixed64 = typing.Annotated[int, ProtoType.SFixed64]
Double = typing.Annotated[float, ProtoType.Double]
# LEN
String = typing.Annotated[str, ProtoType.String]
Bytes = typing.Annotated[bytes, ProtoType.Bytes]
# I32
Fixed32 = typing.Annotated[int, ProtoType.Fixed32]
SFixed32 = typing.Annotated[int, ProtoType.SFixed32]
Float = typing.Annotated[float, ProtoType.Float]

_ALLOWED_VALUES = [
    Int32,
    Int64,
    UInt32,
    UInt64,
    SInt32,
    SInt64,
    Bool,
    Fixed64,
    SFixed64,
    Double,
    String,
    Bytes,
    Fixed32,
    SFixed32,
    Float,
]


@dataclasses.dataclass(frozen=True, **_SLOT_ARGS)
class ProtoConversionInfo:
    pid: int
    name: str
    py_type: type
    proto_type: ProtoType
    proto_mode: ProtoMode


class _MapBase:
    key: typing.Any
    value: typing.Any


T = typing.TypeVar("T")


@typing.overload
def field(pid: int, /) -> typing.Any: ...


@typing.overload
def field(pid: int, /, *, default: None) -> typing.Any: ...


@typing.overload
def field(pid: int, /, *, default: T) -> T: ...


@typing.overload
def field(pid: int, /, *, default_factory: typing.Callable[[], T]) -> T: ...


def field(
    pid: int, /, *, default: typing.Any = MISSING, default_factory: typing.Any = MISSING
) -> typing.Any:
    metadata = {_METADATA_TAG_NAME: pid}
    if default is not MISSING:
        return dataclasses.field(default=default, metadata=metadata)
    if default_factory is not MISSING:
        return dataclasses.field(default_factory=default_factory, metadata=metadata)
    return dataclasses.field(metadata=metadata)


def zigzag_to_signed(value: int) -> int:
    result = value >> 1
    if value & 1:
        result = -result - 1
    return result


def signed_to_zigzag(value: int) -> int:
    if value >= 0:
        return value << 1
    return (-value - 1) << 1 | 1


if not typing.TYPE_CHECKING and sys.version_info < (3, 11):
    # evil python type hackery
    typing.dataclass_transform = lambda *_, **__: lambda x: x


@typing.dataclass_transform(field_specifiers=(field,))
def message(source: type) -> typing.Any:
    pid_lookup: dict[int, ProtoConversionInfo] = {}
    name_lookup: dict[str, ProtoConversionInfo] = {}
    setattr(source, _PID_LOOKUP_NAME, pid_lookup)
    setattr(source, _NAME_LOOKUP_NAME, name_lookup)

    datacls: type = dataclasses.dataclass()(source)
    hints = typing.get_type_hints(datacls, include_extras=True)
    for field in dataclasses.fields(datacls):
        pid = field.metadata.get(_METADATA_TAG_NAME)
        if pid is None:
            msg = f"{source.__qualname__}.{field.name}: not annotated as protobuf field"
            raise ValueError(msg)

        if pid < 0:
            msg = f"{source.__qualname__}.{field.name}: negative id not allowed: {pid}"
            raise ValueError(msg)

        if pid in pid_lookup:
            msg = f"{source.__qualname__}.{field.name}: duplicate id: {pid}"
            raise ValueError(msg)

        try:
            py_type, proto_type, proto_mode = _resolve_type(hints[field.name])  # type: ignore
        except (TypeError, ValueError) as error:
            msg = f"{source.__qualname__}.{field.name}: {error}"
            raise type(error)(msg) from None

        if proto_mode is ProtoMode.Single and (
            field.default is not dataclasses.MISSING
            or field.default_factory is not dataclasses.MISSING
        ):
            proto_mode = ProtoMode.Optional

        conversion_info = ProtoConversionInfo(
            pid, field.name, py_type, proto_type, proto_mode
        )
        pid_lookup[pid] = conversion_info
        name_lookup[field.name] = conversion_info

    return datacls


_NON_PACKABLE_TYPES = (ProtoType.Bytes, ProtoType.String, ProtoType.Embed)


def _resolve_type(py_type: type) -> tuple[type, ProtoType, ProtoMode]:
    origin = typing.get_origin(py_type)

    # Resolve optionals like `str | None`
    if origin is typing.Union:
        args = typing.get_args(py_type)
        if type(None) in args:
            if len(args) != 2:
                types = ", ".join(map(repr, args))
                msg = f"need exactly 2 types, got {types}"
                raise TypeError(msg)

            py_type = args[args[0] is type(None)]
            origin = typing.get_origin(py_type)
            if origin in (list, dict):
                msg = (
                    f"found optional {origin.__name__}, "
                    "remove the optional annotation"
                )
                raise TypeError(msg)
        else:
            types = ", ".join(map(repr, args))
            msg = f"cannot handle non optional union type annotation: {types}"
            raise NotImplementedError(msg)

    # resolved subscribed types `list[T]` and `dict[T, U]`
    if origin in (list, dict):
        args = typing.get_args(py_type)
        if origin is list:
            py_type, proto_type, _ = _resolve_type(args[0])
            if proto_type in _NON_PACKABLE_TYPES:
                mode = ProtoMode.Repeated
            else:
                mode = ProtoMode.Packed
            return py_type, proto_type, mode

        class _Map(_MapBase):
            key: None = field(1, default=None)  # type: ignore
            value: None = field(2, default=None)  # type: ignore

        # resolve `from __future__ import annotations`
        _Map.__annotations__["key"] = typing.Union[args[0], None]
        _Map.__annotations__["value"] = typing.Union[args[1], None]
        Map = message(_Map)

        return Map, ProtoType.Embed, ProtoMode.Repeated

    # only single types left
    mode = ProtoMode.Single
    if py_type in _ALLOWED_VALUES:
        py_type, proto_type = typing.get_args(py_type)

    elif issubclass(py_type, enum.IntEnum):
        proto_type = ProtoType.Enum

    elif dataclasses.is_dataclass(py_type):
        proto_type = ProtoType.Embed

    elif py_type in (list, dict):
        msg = f"missing specialization for {py_type}"
        raise TypeError(msg)

    else:
        msg = f"invalid field type: {py_type}"
        raise TypeError(msg)

    return py_type, proto_type, mode
