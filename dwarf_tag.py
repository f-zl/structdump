from elftools.dwarf.die import DIE
from enum import StrEnum


class DW_AT(StrEnum):
    byte_size = "DW_AT_byte_size"
    name = "DW_AT_name"
    type = "DW_AT_type"
    data_member_location = "DW_AT_data_member_location"
    upper_bound = "DW_AT_upper_bound"


class DW_TAG(StrEnum):
    typedef = "DW_TAG_typedef"
    array_type = "DW_TAG_array_type"
    subrange_type = "DW_TAG_subrange_type"
    structure_type = "DW_TAG_structure_type"
    member = "DW_TAG_member"
    base_type = "DW_TAG_base_type"
    enumeration_type = "DW_TAG_enumeration_type"
    variable = "DW_TAG_variable"


def get_DW_AT_byte_size(die: DIE) -> int:
    return die.attributes[DW_AT.byte_size].value


def get_DW_AT_name(die: DIE) -> str:
    return str(die.attributes[DW_AT.name].value, "ascii")


def get_DW_AT_type(die: DIE) -> DIE:
    return die.dwarfinfo.get_DIE_from_refaddr(die.attributes[DW_AT.type].value)


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
                    pass  # print("Array child enum not supported yet")
                case _:
                    pass  # print("Not supported")
        raise AssertionError


class Struct:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.structure_type
        self.die = die

    def tag_name(self) -> str:  # maybe return str | None
        name = self.die.attributes.get(DW_AT.name)
        return name.value if name else "(anonymous)"

    def byte_size(self: DIE) -> int:
        return get_DW_AT_byte_size(self.die)


class Member:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.member
        self.die = die

    def name(self) -> str:
        return get_DW_AT_name(self.die)

    def type(self) -> DIE:
        return get_DW_AT_type(self.die)

    def member_offset(self) -> int:
        # bitfield is not supported
        # member that has offset=0 may have no data_member_location
        form = self.die.attributes[DW_AT.data_member_location].value
        if type(form) == int:
            return form
        # form may be a location description
        print("TODO member offset")
        return -1


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


class EnumType:
    def __init__(self, die: DIE):
        assert die.tag == DW_TAG.enumeration_type
        self.die = die

    def tag_name(self) -> str:
        name = self.die.attributes.get(DW_AT.name)
        return name.value if name else "(anonymous)"

    # may be invalid
    def underlying_type(self) -> DIE:
        return get_DW_AT_type(self.die)

    def byte_size(self) -> int:
        return get_DW_AT_byte_size(self.die)
