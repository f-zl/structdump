from enum import StrEnum, auto
from dataclasses import dataclass, asdict, is_dataclass
import json

# classes to represent the dumped result, similar to DWARF, but easier to use


class Kind(StrEnum):
    struct = auto()
    base = auto()  # int, float, pointer
    enum = auto()
    array = auto()
    atomic = auto()  # because _Atomic(T) is different from T
    # union is not supported yet


@dataclass
class Member:
    type: str  # the type in the struct declaration, array's type is like int[3]
    name: str
    offset: int
    # TODO add consider CVR qualifiers in the type?


class BaseTypeEncoding(StrEnum):
    signed_integral = auto()
    unsigned_integral = auto()
    floating_point = auto()


# pointer in struct is not supported, because it's often meaning less
# if the pointer points to an element in the struct's array memeber, maybe use an index instead


@dataclass
class ArrayField:
    element_type: str


@dataclass
class AtomicField:
    base_type: str


@dataclass
class Meta:  # inherited by each kind in Kind
    name: str
    size: int

    def __init__(self):
        raise TypeError("Meta class is abstract")


@dataclass
class BaseTypeMeta(Meta):  # Meta for base type like int, not a base class
    encoding: BaseTypeEncoding


@dataclass
class StructMeta(Meta):
    members: list[Member]


@dataclass
class EnumMeta(Meta):
    underlying_type: str


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, StrEnum):
            return obj.value
        if is_dataclass(obj):
            return asdict(obj)
        return json.JSONEncoder.default(self, obj)


# each executable should have one single type dict
# it is not supported that multuple types share the same name
class TypeDict(dict[str, Meta]):
    def to_json(self):
        return json.dumps(self, cls=JSONEncoder)


def print_member(m: Member):
    print(f"{m.type} {m.name} offset {m.offset}")


def print_struct(s: StructMeta):
    print(f"{s.name} size {s.size} members {{")
    for m in s.members:
        print_member(m)
    print("}")


MyStruct = StructMeta(
    "MyStruct",
    28,
    [
        Member("int", "x", 0),
        Member("float[2]", "y", 4),
        Member("char", "c", 16),
        Member("ArrayInt2", "arr", 20),
    ],
)
# print_struct(MyStruct)
# d = asdict(MyStruct)
# s = json.dumps(d, cls=JSONEncoder)
# print(s)
