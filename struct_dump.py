from enum import StrEnum, Enum, auto
from dataclasses import dataclass

# classes to represent the dumped result, similar to DWARF, but easier to use


class Kind(StrEnum):
    struct = "struct"
    base = "base"  # int, float, etc
    enum = "enum"
    array = "array"
    atomic = "atomic"  # because _Atomic(T) is different from T
    # union is not supported yet

    def __repr__(self):
        return f"Kind({self.value})"


@dataclass
class Member:
    type: str  # the type in the struct declaration, array's type is like int[3]
    name: str
    offset: int


@dataclass
class StructField:
    members: list[Member]


class BaseFieldKind(Enum):
    signed_integral = auto()
    unsigned_interal = auto()
    floating = auto()
    other = auto()


@dataclass
class BaseField:
    kind: BaseFieldKind


@dataclass
class EnumField:
    underlying_type: str  # should be an int type


@dataclass
class ArrayField:
    element_type: str


@dataclass
class AtomicField:
    base_type: str


@dataclass
class Meta:
    kind: Kind
    name: str
    size: int
    variant: StructField | BaseField | EnumField | ArrayField | AtomicField

    def __repr__(self):
        match self.kind:
            case Kind.struct:
                return f"struct {self.name} size {self.size} members {self.variant.members}"
            case Kind.base:
                return f"base {self.name} size {self.size}"
            case Kind.enum:
                return f"enum {self.name} size {self.size} underlying_type {self.variant.underlying_type}"
            case Kind.array:
                return f"array {self.name} size {self.size} element_type {self.variant.element_type}"
            case Kind.atomic:
                return f"atomic {self.name} size {self.size} base_type {self.base_type}"


def BaseMeta(name: str, size: int) -> Meta:
    return Meta(Kind.base, name, size, BaseField)


def StructMeta(name: str, size: int, members: list[Member]) -> Meta:
    return Meta(Kind.struct, name, size, StructField(members))


# each executable should have one single type dict
# it is not supported that multuple types share the same name
class TypeDict(dict[str, Meta]):
    pass


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
