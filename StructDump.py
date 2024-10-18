from pydantic import BaseModel
from enum import Enum, auto
from dataclasses import dataclass


class Kind(Enum):
    struct = (auto(),)
    base = (auto(),)
    enum = auto()


@dataclass
class Member:
    type: str
    name: str
    offset: int
    length: int | None = None  # has value if type is array


@dataclass
class StructField:
    members: list[Member]


# type BaseField = None py 3.12 needed
@dataclass
class BaseField:
    pass


@dataclass
class EnumField:
    underlying_type: str  # should be an int type


@dataclass
class Meta:
    kind: Kind
    name: str
    size: int
    variant: StructField | BaseField | EnumField


def BaseMeta(name: str, size: int) -> Meta:
    return Meta(Kind.base, name, size, BaseField)


def StructMeta(name: str, size: int, members: list[Member]) -> Meta:
    return Meta(Kind.struct, name, size, StructField(members))


def print_member(m: Member):
    print(f"{m.type} {m.name} offset {m.offset}", end="")
    if m.length is None:
        print()
    else:
        print(f" length {m.length}")


def print_struct(s: Meta):
    print(f"{s.name} size {s.size} members {{")
    for m in s.variant.members:
        print_member(m)
    print("}")


int_ = BaseMeta("int", 4)
float_ = BaseMeta("float", 4)
char = BaseMeta("char", 1)
ArrayInt2 = StructMeta("ArrayInt2", 8, [Member("int[]", "value", 0, 2)])
MyStruct = StructMeta(
    "MyStruct",
    28,
    [
        Member("int", "x", 0),
        Member("float[]", "y", 4, 2),
        Member("char", "c", 16),
        Member("ArrayInt2", "arr", 20),
    ],
)

print_struct(MyStruct)
