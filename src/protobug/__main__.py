from __future__ import annotations

import protobug


@protobug.message
class TestMessage:
    a: protobug.String | None = protobug.field(1, default=None)
    b: list[protobug.String] = protobug.field(2, default_factory=list)
    c: dict[protobug.UInt32, protobug.String] = protobug.field(5, default_factory=dict)


def main() -> None:
    print(f"{protobug.__name__} v{protobug.__version__}\n")
    for payload in [
        b"",
        b"\x0a\x00",
        b"\x12\x05hello\x12\x05world",
        b"\x0a\x0bhello world",
        b"\x0a\x09this is a\x12\x09this is b",
        b"\x2a\x0b\x08\x00\x12\x07value 0\x2a\x0b\x08\x01\x12\x07value 1",
    ]:
        print(repr(payload))
        print(protobug.loads(payload, TestMessage))
        print()


if __name__ == "__main__":
    main()
