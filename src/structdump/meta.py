from enum import StrEnum, auto
from dataclasses import dataclass, asdict, is_dataclass, field
import json

# classes to represent the dumped result, similar to DWARF, but easier to use

# TODO add CVR qualifiers in the type?


class Kind(StrEnum):
    # int (including char, bool, _BitInt), float (including complex, decimal)
    base = auto()
    enum = auto()
    array = auto()  # array will not be registered in the type dict though
    struct = auto()
    atomic = auto()  # because _Atomic(T) is different from T
    # union
    # poiner (object, function, nullptr)
    # function
    # void?


@dataclass
class MemberMeta:
    type: str  # the type in the struct declaration, array's type is like int[3]
    name: str | None  # maybe unnamed
    offset: int | None
    size: int  # maybe None
    # TODO support bit-fields


class BaseTypeEncoding(StrEnum):
    signed_integral = auto()
    unsigned_integral = auto()
    floating_point = auto()
    boolean = auto()


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
    underlying_type: str | None  # some compilers don't provide an underlying type
    enumerators: dict[str, int]


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, StrEnum):
            return o.value
        if is_dataclass(o):
            return asdict(o)
        return json.JSONEncoder.default(self, o)


# each executable should have one single type dict
# it is not supported that multuple types share the same name
class TypeDict(dict[str, Meta]):
    def to_json(self):
        # specify separator to remove whitespace
        return json.dumps(self, cls=JSONEncoder, separators=(",", ":"))

    @staticmethod
    def from_json(jsonstr: str) -> "TypeDict":
        raw_dict = json.loads(jsonstr)
        type_dict = TypeDict()
        for key, value in raw_dict.items():
            kind_str = value.get("kind")
            match kind_str:
                case Kind.base:
                    encoding = BaseTypeEncoding(value["encoding"])
                    meta = BaseTypeMeta(
                        name=value["name"], size=value["size"], encoding=encoding
                    )
                case Kind.enum:
                    meta = EnumMeta(
                        name=value["name"],
                        size=value["size"],
                        underlying_type=value.get("underlying_type"),
                        enumerators=value["enumerators"],
                    )
                case Kind.struct:
                    members = [MemberMeta(**m) for m in value["members"]]
                    meta = StructMeta(
                        name=value["name"], size=value["size"], members=members
                    )
                case Kind.array:
                    raise ValueError("array kind should not be present")
                case Kind.atomic:
                    raise NotImplementedError()
                case _:
                    raise NotImplementedError()
            type_dict[key] = meta
        return type_dict
