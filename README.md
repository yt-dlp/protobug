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


protobug.loads(payload, Message)
```

## License
`protobug` is distributed under the terms of the [Unlicense](https://spdx.org/licenses/Unlicense.html) license.
