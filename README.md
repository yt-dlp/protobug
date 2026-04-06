# protobug
A pythonic protobuf library using dataclasses and enums

## Usage

```py
import protobug


@protobug.message
class Message:
    a: protobug.String | None = protobug.field(1, default=None)
    b: list[protobug.String] = protobug.field(2, default_factory=list)
    c: dict[protobug.UInt32, protobug.String] = protobug.field(5, default_factory=dict)


payload = b"\x0a\x00"
print(protobug.loads(payload, Message))

payload = b"\x12\x05hello\x12\x05world"
print(protobug.loads(payload, Message))

payload = b"\x0a\x0bhello world"
print(protobug.loads(payload, Message))

payload = b"\x0a\x09this is a\x12\x09this is b"
print(protobug.loads(payload, Message))

payload = b"\x2a\x0b\x08\x00\x12\x07value 0\x2a\x0b\x08\x01\x12\x07value 1"
print(protobug.loads(payload, Message))
```

## License
`protobug` is distributed under the terms of the [Unlicense](https://spdx.org/licenses/Unlicense.html) license.
