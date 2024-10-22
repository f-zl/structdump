from elftools.elf.elffile import ELFFile
from elftools.dwarf.die import DIE
from .dwarf_tag import (
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
            arr = Array(die)
            # TODO getShortName()
            return f"{get_DW_AT_name(arr.element_type())}[{arr.length()}]"
        case DW_TAG.structure_type:
            s = Struct(die)
            tag_name = s.tag_name()
            return "struct" if tag_name else f"struct {tag_name}"
        case DW_TAG.enumeration_type:
            e = EnumType(die)
            tag_name = e.tag_name()
            return "enum" if tag_name else f"enum {tag_name}"
        case DW_TAG.pointer_type:
            p = PointerType(die)
            return f"{get_type_name(p.remove_pointer_type())}*"
        case _:
            raise ValueError(f"Unknown tag {die.tag} for name")


def process_member(die: DIE, base_offset: int, prefix: str):
    member = Member(die)
    print_prefix(prefix, member)
    member_type = member.type()
    print(
        f" {get_type_name(member_type)} offset {member_offset_str(base_offset,member.member_offset())} size {member_type_size_str(member_type)}"
    )


def process_struct(die: DIE, base_offset: int, prefix: str):
    s = Struct(die)
    print(f"struct {s.tag_name()} size {s.byte_size()}")
    for child in die.iter_children():
        process_member(child, base_offset, prefix)


def get_base_type_kind(base_type: BaseType) -> BaseTypeEncoding:
    if base_type.is_floating_point():
        return BaseTypeEncoding.floating_point
    if base_type.is_signed_integral():
        return BaseTypeEncoding.signed_integral
    if base_type.is_unsigned_integral():
        return BaseTypeEncoding.unsigned_integral
    raise ValueError("base type has unknow kind")


def register_with_name(die: DIE, name: str, td: TypeDict) -> None:
    if name not in td:
        match die.tag:
            case DW_TAG.typedef:
                # raise ValueError("typedef die should be resolved before calling")
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
                    underlying_type_name = get_DW_AT_name(underlying_type)
                    td[name] = EnumMeta(name, e.byte_size(), underlying_type_name)
                    # underlying_type should be registered too
                    register_with_name(underlying_type, underlying_type_name, td)
            case DW_TAG.structure_type:
                s = Struct(die)
                meta = StructMeta(name, s.byte_size(), [])
                td[name] = meta
                # NOTE possible deep recursive
                for m in s:
                    member = Member(m)
                    member_type = member.type()
                    type_name = get_type_name(member_type)
                    register_with_name(member_type, type_name, td)
                    meta.members.append(
                        MemberMeta(
                            type_name,
                            member.name(),
                            member.member_offset(),
                        )
                    )
            case DW_TAG.array_type:
                # array do not need to be registered
                # NOTE maybe typedef will resolve to an array type
                pass
            case _:
                raise NotImplementedError(f"tag {die.tag} is not supported yet")


# TODO remove this function
def register_in_typedict(die: DIE, d: TypeDict) -> None:
    match die.tag:
        case DW_TAG.typedef:
            name = Typedef(die).name()
            register_with_name(resolve_typedef(die), name, d)
        case DW_TAG.base_type:
            name = BaseType(die).name()
            register_with_name(die, name, d)
        case DW_TAG.array_type:
            # array need not to be registered
            pass
        case (
            DW_TAG.structure_type
        ):  # FIXME warning about different anonymous struct/enums (can not tell type is different based on name)
            s = Struct(die)
            name = f"struct {s.tag_name()}"
            register_with_name(die, name, d)
        case DW_TAG.enumeration_type:
            e = EnumType(die)
            name = f"enum {e.tag_name()}"
            register_with_name(die, name, d)
        case DW_TAG.pointer_type:
            pass
        case _:
            print(f"Unknown tag {die.tag}, skipping")


# g_var = None


def process_top_type(original_type: DIE) -> TypeDict:
    # breakpoint()
    resolved_type = resolve_typedef(original_type)
    # print(original_type)
    # i = 0
    # while i < 5000:
    #     try:
    #         d = original_type.dwarfinfo.get_DIE_from_refaddr(i)
    #         if d.tag == DW_TAG.structure_type:
    #             print(f"i={i},{i:#x}, d={d}")
    #             # break
    #     except:
    #         pass
    #     i += 1
    # sys.exit(1)
    # global g_var  # i=1223(0x4c7), 1287(0x507), 1305(0x519)
    # g_var = d
    # print("original_type", original_type)
    # print("resolved_type", resolved_type)
    if resolved_type.tag != DW_TAG.structure_type:
        print("top type is not a struct")
        sys.exit(1)
    struct = Struct(resolved_type)
    if original_type.tag == DW_TAG.typedef:
        original_type_name = Typedef(original_type).name()
    else:
        original_type_name = f"struct {struct.tag_name()}"
    td = TypeDict()
    top_struct = StructMeta(original_type_name, struct.byte_size(), [])
    for child in struct:  # resolved_type.iter_children():
        member = Member(child)
        member_type = member.type()
        register_in_typedict(member_type, td)

        top_struct.members.append(
            MemberMeta(
                get_type_name(member_type), member.name(), member.member_offset()
            )
        )
    td[original_type_name] = top_struct
    return td


def main(var_name: str, file: str):
    with open(file, "rb") as f:
        e = ELFFile(f)  # need to keep f open when e is being used
        rst = find_sym_addr_size(e, var_name)
        if rst is None:
            print("Not find variable in .symtab")
            sys.exit(1)
        addr, size = rst
        print(f"{var_name} is at addr {addr:#x}, has size {size}")
        if not e.has_dwarf_info():
            print("No DWARF info")
            sys.exit(1)
        d = e.get_dwarf_info()
        for cu in d.iter_CUs():
            die = cu.get_top_DIE()
            var = find_variable(die, var_name)
            if var is not None:
                break
        if var is None:
            print(f"Variable {var_name} not found")
            sys.exit(1)
        var_type = var.get_DIE_from_attribute(DW_AT.type)
        # process_struct(resolve_typedef(var_type), 0, "")
        return process_top_type(var_type)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="object or execuable file", required=True)
    parser.add_argument("--variable", help="the struct object's name", required=True)
    args = parser.parse_args()
    td = main(args.variable, args.file)
    print(td.to_json())
