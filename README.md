# protobug
A pythonic protobuf library using dataclasses and enums

## Usage
First, define a `protobug.message`, which is similar to a dataclass,
except using `protobug.field` and protobug types.
```py
import protobug


@protobug.message
class Message:
    a: protobug.String | None = protobug.field(1, default=None)
    b: list[protobug.String] = protobug.field(2, default_factory=list)
    c: dict[protobug.UInt32, protobug.String] = protobug.field(3, default_factory=dict)
```

After defining the model, you can freely decode and encode,
using the familiar `load`/`loads` and `dump`/`dumps` api.
```py
>>> payload = b"\x0a\x0bhello world"
>>> protobug.loads(payload, Message)
Message(a='hello world', b=[], c={})

>>> payload = b"\x12\x05hello\x12\x05world"
>>> protobug.loads(payload, Message)
Message(a=None, b=['hello', 'world'], c={})

>>> payload = b"\x1a\x09\x08\x00\x12\x05val 0\x1a\x09\x08\x01\x12\x05val 1"
>>> protobug.loads(payload, Message)
Message(a=None, b=[], c={0: 'val 0', 1: 'val 1'})

>>> data = Message(a='val a', b=['val b'], c={0: 'val c'})
>>> protobug.dumps(data)
b'\n\x05val a\x12\x05val b\x1a\t\x08\x00\x12\x05val c'
```

## License
`protobug` is distributed under the terms of the [Unlicense](https://spdx.org/licenses/Unlicense.html) license.
