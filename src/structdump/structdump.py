from enum import StrEnum, auto
from dataclasses import dataclass, asdict, is_dataclass, field
import json

# classes to represent the dumped result, similar to DWARF, but easier to use


class Kind(StrEnum):
    struct = auto()
    base = auto()  # int, float, pointer
    enum = auto()
    array = auto()  # array will not be registered in the type dict though
    atomic = auto()  # because _Atomic(T) is different from T
    # union is not supported yet


@dataclass
class MemberMeta:
    type: str  # the type in the struct declaration, array's type is like int[3]
    name: str
    offset: int | None
    size: int  # maybe None
    # TODO add consider CVR qualifiers in the type?


class BaseTypeEncoding(StrEnum):
    signed_integral = auto()
    unsigned_integral = auto()
    floating_point = auto()


# pointer in struct is not supported, because it's often meaning less
# if the pointer points to an element in the struct's array memeber, maybe use an index instead


@dataclass
class Meta:  # inherited by each kind in Kind
    kind: Kind  # so that the output will contain "kind" field
    name: str
    size: int

    def __init__(self):
        raise TypeError("Meta class is abstract")


@dataclass
class BaseTypeMeta(Meta):  # Meta for base type like int, not a base class
    kind: Kind = field(init=False, default=Kind.base)
    encoding: BaseTypeEncoding


@dataclass
class StructMeta(Meta):
    kind: Kind = field(init=False, default=Kind.struct)
    members: list[MemberMeta]


@dataclass
class EnumMeta(Meta):
    kind: Kind = field(init=False, default=Kind.enum)
    underlying_type: str | None  # some compiler doesn't provide an underlying type


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
