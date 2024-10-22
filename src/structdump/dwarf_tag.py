from elftools.dwarf.die import DIE
from elftools.construct.lib import ListContainer
from enum import StrEnum, IntEnum
import logging


class DW_AT(StrEnum):
    byte_size = "DW_AT_byte_size"
    name = "DW_AT_name"
    type = "DW_AT_type"
    data_member_location = "DW_AT_data_member_location"
    upper_bound = "DW_AT_upper_bound"
    encoding = "DW_AT_encoding"


class DW_TAG(StrEnum):
    typedef = "DW_TAG_typedef"
    array_type = "DW_TAG_array_type"
    subrange_type = "DW_TAG_subrange_type"
    structure_type = "DW_TAG_structure_type"
    member = "DW_TAG_member"
    base_type = "DW_TAG_base_type"
    enumeration_type = "DW_TAG_enumeration_type"
    variable = "DW_TAG_variable"
    pointer_type = "DW_TAG_pointer_type"


class DW_ATE(IntEnum):
    address = 1
    boolean = 2
    complex_float = 3
    float = 4
    signed = 5
    signed_char = 6
    unsigned = 7
    unsigned_char = 8
    imaginary_float = 9
    packed_decimal = 10
    numeric_string = 11
    edited = 12
    signed_fixed = 13


def get_DW_AT_byte_size(die: DIE) -> int:
    return die.attributes[DW_AT.byte_size].value


def get_DW_AT_name(die: DIE) -> str:
    return str(die.attributes[DW_AT.name].value, "ascii")


def get_DW_AT_type(die: DIE) -> DIE:
    # https://github.com/eliben/pyelftools/issues/381
    return die.get_DIE_from_attribute(DW_AT.type)


def get_DW_AT_encoding(die: DIE) -> DW_ATE:
    return DW_ATE(die.attributes[DW_AT.encoding].value)


def resolve_typedef(die: DIE) -> DIE:
    while die.tag == DW_TAG.typedef:
        die = get_DW_AT_type(die)
    return die


class Array:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.array_type
        self.die = die

    def element_type(self) -> DIE:
        return get_DW_AT_type(self.die)

    def length(self) -> int:
        for child in self.die.iter_children():
            match child.tag:
                case DW_TAG.subrange_type:  # gcc uses this
                    return child.attributes[DW_AT.upper_bound].value + 1
                case DW_TAG.enumeration_type:
                    raise NotImplementedError(
                        "Array child has enum tag, which is not supported yet"
                    )
                case _:
                    pass
        raise ValueError("Array children have no known tag for length")


class Struct:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.structure_type
        self.die = die

    def tag_name(self) -> str | None:
        name = self.die.attributes.get(DW_AT.name)
        return name.value if name else None

    def byte_size(self) -> int:
        return get_DW_AT_byte_size(self.die)

    def __iter__(self):
        return self.die.iter_children()


from elftools.common.construct_utils import ULEB128
from io import BytesIO


class Member:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.member
        self.die = die

    def name(self) -> str:  # TODO maybe unnamed
        return get_DW_AT_name(self.die)

    def type(self) -> DIE:
        return get_DW_AT_type(self.die)

    def member_offset(self) -> int | None:
        # bitfield is not supported
        # member that has offset=0 may have no data_member_location
        data_member_location = self.die.attributes.get(DW_AT.data_member_location)
        if data_member_location is not None:
            value = data_member_location.value
            if type(value) == int:
                # elf produced by linux-x64-gcc falls in this
                return value
            # pyelftools shows the value is DW_FORM_block1 and is a ListContainer
            # for the elf of interest, it only uses DW_OP_plus_uconst, so just implement that
            if type(value) == ListContainer:
                DW_OP_plus_uconst = 35
                if len(value) < 2 or value[0] != DW_OP_plus_uconst:
                    logging.warning(f"Not implemented, value={value}")
                    return None
                b = BytesIO(bytes(value[1:]))
                offset = ULEB128("")._parse(b, None)
                return offset
        logging.warning(
            f"member offset other than data_member_location is not supported {self.die}"
        )
        return None


class Typedef:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.typedef
        self.die = die

    def type(self) -> DIE:
        return get_DW_AT_type(self.die)

    def resolved_type(self) -> DIE:
        die = get_DW_AT_type(self.die)
        return resolve_typedef(die)

    def name(self) -> str:
        return get_DW_AT_name(self.die)


class BaseType:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.base_type
        self.die = die

    def name(self) -> str:
        return get_DW_AT_name(self.die)

    def byte_size(self) -> int:
        return get_DW_AT_byte_size(self.die)

    # type_traits
    def is_floating_point(self) -> bool:
        # complex_float, imaginary_float, decimal_float is ignored by now
        return get_DW_AT_encoding(self.die) == DW_ATE.float

    def is_signed_integral(self) -> bool:
        # signed_fixed is ignored
        e = get_DW_AT_encoding(self.die)
        return e == DW_ATE.signed or e == DW_ATE.signed_char

    def is_unsigned_integral(self) -> bool:
        e = get_DW_AT_encoding(self.die)
        return e == DW_ATE.unsigned or e == DW_ATE.unsigned_char


class EnumType:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.enumeration_type
        self.die = die

    def tag_name(self) -> str | None:
        name = self.die.attributes.get(DW_AT.name)
        return name.value if name else None

    # may be invalid
    def underlying_type(self) -> DIE | None:
        # for some reasons some enum doesn't underlying_type in debug info
        try:
            return get_DW_AT_type(self.die)
        except KeyError:
            return None

    def byte_size(self) -> int:
        return get_DW_AT_byte_size(self.die)


class PointerType:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.pointer_type
        self.die = die

    def byte_size(self) -> int:
        return get_DW_AT_byte_size(self.die)

    def remove_pointer_type(self) -> DIE:  # std::remove_pointer<T>::type
        return get_DW_AT_type(self.die)