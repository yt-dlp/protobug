from __future__ import annotations

import typing

import protobug


@protobug.message
class Message1:
    a: typing.Union[protobug.Int32, None] = protobug.field(1, default=None)


@protobug.message
class Message2:
    b: protobug.String = protobug.field(2)


@protobug.message
class Message3:
    c: Message1 = protobug.field(3)


@protobug.message
class Message4:
    d: typing.Union[protobug.String, None] = protobug.field(4, default=None)
    e: list[protobug.Int32] = protobug.field(5, default_factory=list)


@protobug.message
class Message5:
    f: list[protobug.Int32] = protobug.field(6)


class MessageEnum(protobug.Enum):
    A = 0
    B = 1
    C = 2


@protobug.message
class Message6:
    g: dict[protobug.String, protobug.UInt32] = protobug.field(7)


@protobug.message
class Message7:
    h: list[MessageEnum] = protobug.field(8)


@protobug.message
class Message8:
    i: protobug.Float = protobug.field(9)
