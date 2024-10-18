from enum import Enum, auto
from dataclasses import dataclass


class Kind(Enum):
    struct = "struct"
    base = "base"
    enum = "enum"

    def __repr__(self):
        return self.value


@dataclass
class Member:
    type: str  # array type is like int[3]
    name: str
    offset: int


@dataclass
class StructField:
    members: list[Member]


# type BaseField = None # py 3.12 needed
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

    def __repr__(self):
        match self.kind:
            case Kind.struct:
                return f"struct {self.name} size {self.size} members {self.variant.members}"
            case Kind.base:
                return f"base {self.name} size {self.size}"
            case Kind.enum:
                return f"enum {self.name} size {self.size} underlying_type {self.variant.underlying_type}"


def BaseMeta(name: str, size: int) -> Meta:
    return Meta(Kind.base, name, size, BaseField)


def StructMeta(name: str, size: int, members: list[Member]) -> Meta:
    return Meta(Kind.struct, name, size, StructField(members))


class TypeDict(dict[str, Meta]):
    pass


typedict = TypeDict()


def print_member(m: Member):
    print(f"{m.type} {m.name} offset {m.offset}")


def print_struct(s: Meta):
    print(f"{s.name} size {s.size} members {{")
    for m in s.variant.members:
        print_member(m)
    print("}")


def example():
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
