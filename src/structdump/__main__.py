from elftools.elf.elffile import ELFFile
from elftools.dwarf.die import DIE
from .dwarf import (
    Array,
    Struct,
    Typedef,
    BaseType,
    Member,
    EnumType,
    PointerType,
    resolve_typedef,
    get_DW_AT_name,
    get_DW_AT_byte_size,
    DW_AT,
    DW_TAG,
)
from .structdump import (
    TypeDict,
    BaseTypeEncoding,
    BaseTypeMeta,
    StructMeta,
    EnumMeta,
    MemberMeta,
)
import logging
import sys


# return addr, size tuple if found
def find_sym_addr_size(elffile: ELFFile, symbol_name: str) -> tuple[int, int] | None:
    symtab = elffile.get_section_by_name(".symtab")
    if symtab:
        for symbol in symtab.iter_symbols():
            if symbol.name == symbol_name:
                return symbol["st_value"], symbol["st_size"]
        else:
            print(f"Symbol '{symbol_name}' not found.")
            return None
    else:
        print("No .symtab section")
        return None


def find_variable(die: DIE, var_name: str):
    if die.tag == DW_TAG.variable:
        name = die.attributes.get(DW_AT.name)
        if name is not None and name.value == bytes(var_name, "ascii"):
            return die
    for c in die.iter_children():
        if find_variable(c, var_name):
            return c
    return None


def print_prefix(prefix: str, member: Member):
    if prefix:
        print(f"{prefix}.{member.name()}", end="")
    else:
        print(member.name(), end="")


def member_offset_str(base_offset: int, member_offset: int | None) -> str:
    if member_offset is None:
        return "unknown"  # or no offset
    if base_offset == 0:
        return str(member_offset)
    offset = base_offset + member_offset
    return f"{offset}({base_offset}+{member_offset})"


def get_type_size(die: DIE) -> int:
    match die.tag:
        case DW_TAG.base_type | DW_TAG.enumeration_type | DW_TAG.structure_type:
            return get_DW_AT_byte_size(die)
        case DW_TAG.typedef:
            return get_type_size(resolve_typedef(die))
        case DW_TAG.array_type:
            arr = Array(die)
            return get_type_size(resolve_typedef(arr.element_type())) * arr.length()
        case _:
            raise AssertionError(f"Unknown tag {die.tag}")


def member_type_size_str(die: DIE) -> str:
    match die.tag:
        case DW_TAG.base_type | DW_TAG.enumeration_type | DW_TAG.structure_type:
            return str(get_DW_AT_byte_size(die))
        case DW_TAG.typedef:
            return str(get_type_size(die))
        case DW_TAG.array_type:
            arr = Array(die)
            elem_size = get_type_size(resolve_typedef(arr.element_type()))
            arr_len = arr.length()
            return f"{elem_size * arr_len}({elem_size}*{arr_len})"
        case _:
            return f"Unknown tag {die.tag}"


def get_type_name(die: DIE) -> str:
    match die.tag:
        case DW_TAG.typedef:
            return Typedef(die).name()
        case DW_TAG.base_type:
            return BaseType(die).name()
        case DW_TAG.array_type:
            a = Array(die)
            return f"{get_DW_AT_name(a.element_type())}[{a.length()}]"
        case DW_TAG.structure_type:
            s = Struct(die)
            tag_name = s.tag_name()
            return "struct (anonymous)" if tag_name else f"struct {tag_name}"
        case DW_TAG.enumeration_type:
            e = EnumType(die)
            tag_name = e.tag_name()
            return "enum" if tag_name else f"enum {tag_name}"
        case DW_TAG.pointer_type:
            p = PointerType(die)
            return f"{get_type_name(p.remove_pointer_type())}*"
        case _:
            raise ValueError(f"Unknown tag {die.tag} for name")


def get_base_type_kind(base_type: BaseType) -> BaseTypeEncoding:
    if base_type.is_floating_point():
        return BaseTypeEncoding.floating_point
    if base_type.is_signed_integral():
        return BaseTypeEncoding.signed_integral
    if base_type.is_unsigned_integral():
        return BaseTypeEncoding.unsigned_integral
    raise ValueError("base type has unknow kind")


def register_with_name(die: DIE, name: str, td: TypeDict) -> None:
    # in order for the json consumer to be able to build type dict in one go,
    # the dependent type is inserted first
    # e.g. typedef's resolved type is inserted before typedef
    # struct member's type is inserted before struct
    # the insertion order is kept in dict for python>=3.6
    if name not in td:
        match die.tag:
            case DW_TAG.typedef:
                register_with_name(resolve_typedef(die), name, td)
            case DW_TAG.base_type:
                base_type = BaseType(die)
                td[name] = BaseTypeMeta(
                    name, base_type.byte_size(), get_base_type_kind(base_type)
                )
            case DW_TAG.enumeration_type:
                e = EnumType(die)
                underlying_type = e.underlying_type()
                if underlying_type is None:
                    td[name] = EnumMeta(name, e.byte_size(), None)
                else:
                    # underlying_type should be registered too
                    underlying_type_name = get_DW_AT_name(underlying_type)
                    register_with_name(underlying_type, underlying_type_name, td)
                    td[name] = EnumMeta(name, e.byte_size(), underlying_type_name)
            case DW_TAG.structure_type:
                s = Struct(die)
                meta = StructMeta(name, s.byte_size(), [])
                # NOTE possible deep recursion
                for m in s:
                    member = Member(m)
                    member_type = member.type()
                    type_name = get_type_name(member_type)
                    meta.members.append(
                        MemberMeta(
                            type_name,
                            member.name(),
                            member.member_offset(),
                        )
                    )
                    register_with_name(member_type, type_name, td)
                td[name] = meta
            case DW_TAG.array_type:
                # array's element type is registered instead
                # NOTE typedef may resolve to an array type
                a = Array(die)
                element_type = a.element_type()
                register_with_name(element_type, get_type_name(element_type), td)
            case _:
                raise NotImplementedError(f"tag {die.tag} is not supported yet")


def process_top_type(original_type: DIE) -> TypeDict:
    resolved_type = resolve_typedef(original_type)
    if resolved_type.tag != DW_TAG.structure_type:
        logging.error("Top type is not a struct")
        sys.exit(1)
    struct = Struct(resolved_type)
    original_type_name = get_type_name(original_type)
    td = TypeDict()
    top_struct = StructMeta(original_type_name, struct.byte_size(), [])
    for child in struct:
        member = Member(child)
        member_type = member.type()
        member_type_name = get_type_name(member_type)
        register_with_name(member_type, member_type_name, td)

        top_struct.members.append(
            MemberMeta(member_type_name, member.name(), member.member_offset())
        )
    td[original_type_name] = top_struct
    return td


def main(var_name: str, filename: str):
    with open(filename, "rb") as file:
        elf = ELFFile(file)  # need to keep file open when elf is being used
        rst = find_sym_addr_size(elf, var_name)
        if rst is None:
            logging.error("Variable not found in .symtab")
            sys.exit(1)
        addr, size = rst
        logging.info(f"{var_name} is at addr {addr:#x}, has size {size}")
        if not elf.has_dwarf_info():
            logging.error("No DWARF info")
            sys.exit(1)
        d = elf.get_dwarf_info()
        for cu in d.iter_CUs():
            die = cu.get_top_DIE()
            var = find_variable(die, var_name)
            if var is not None:
                break
        if var is None:
            logging.error(f"Variable {var_name} not found in .debug_info")
            sys.exit(1)
        var_type = var.get_DIE_from_attribute(DW_AT.type)
        td = process_top_type(var_type)
    print(td.to_json())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="object or execuable file", required=True)
    parser.add_argument("--variable", help="the struct object's name", required=True)
    args = parser.parse_args()
    main(args.variable, args.file)
