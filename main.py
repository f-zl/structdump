from elftools.elf.elffile import ELFFile
from elftools.dwarf.die import DIE
from elftools.dwarf.dwarfinfo import DWARFInfo
from dwarf_tag import (
    Array,
    Struct,
    Typedef,
    BaseType,
    Member,
    EnumType,
    resolve_typedef,
    get_DW_AT_name,
    get_DW_AT_byte_size,
    DW_AT,
    DW_TAG,
)
import struct_dump as sd
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
    if die.tag == DW_TAG.variable and die.attributes[DW_AT.name].value == bytes(
        var_name, "ascii"
    ):
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


def member_offset_str(base_offset: int, member_offset: int) -> str:
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
            return get_type_size(die)
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
            return f"struct {s.tag_name()}"
        case DW_TAG.enumeration_type:
            e = EnumType(die)
            return f"enum {e.tag_name()}"
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


def register_with_name(die: DIE, name: str, d: sd.TypeDict) -> None:
    if name not in d:
        match die.tag:
            case DW_TAG.typedef:
                raise ValueError("typedef die should be resolved before calling")
            case DW_TAG.base_type:
                d[name] = sd.BaseMeta(name, BaseType(die).byte_size())
            # TODO other types like enum, struct


def register_in_typedict(die: DIE, d: sd.TypeDict) -> None:
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
        case DW_TAG.structure_type:
            s = Struct(die)
            name = f"struct {s.tag_name()}"
            register_with_name(die, name, d)
        case DW_TAG.enumeration_type:
            e = EnumType(die)
            name = f"enum {e.tag_name()}"
            register_with_name(die, name, d)
        case _:
            raise ValueError(f"Unknown tag {die.tag}")


import json


# class Encoder(json.JSONEncoder):
#     def default(self, obj):
#         try:
#             return super().default(obj)
#         except TypeError:
#             return obj.__dict__


def to_json(m: sd.Meta) -> str:
    match m.kind:
        case sd.Kind.base:
            return f'{{"kind":"base","name":"{m.name}","size":{m.size}}}'
        case sd.Kind.enum:
            return f'{{"kind":"enum","name":"{m.name}","size":{m.size},"underlying_type":"{m.variant.underlying_type}"}}'
        case sd.Kind.struct:
            if len(m.variant.members) == 0:
                member_str = "[]"
            else:
                member_str = "["
                for mb in m.variant.members:
                    member_str += f'{{"type":"{mb.type}","name":"{mb.name}","offset":{mb.offset}}},'
                member_str = member_str[:-1]
                member_str += "]"
            return f'{{"kind":"struct","name":"{m.name}","size":{m.size},"members":{member_str}}}'


def dict_to_json(top_type_name: str, d: sd.TypeDict) -> str:
    if len(d) == 0:
        return "[]"
    s = "["
    for k in d:
        s += to_json(d[k]) + ","
    s = s[:-1]  # remove last ','
    s += "]"
    return s


def process_top_type(original_type: DIE):
    resolved_type = resolve_typedef(original_type)
    if resolved_type.tag != DW_TAG.structure_type:
        print("top type is not a struct")
        return
    struct = Struct(resolved_type)
    if original_type.tag == DW_TAG.typedef:
        original_type_name = Typedef(original_type).name()
    else:
        original_type_name = f"struct {struct.tag_name()}"
    top_struct = sd.StructMeta(original_type_name, struct.byte_size(), [])
    td = sd.TypeDict()
    for child in resolved_type.iter_children():
        member = Member(child)
        member_type = member.type()
        register_in_typedict(member_type, td)

        top_struct.variant.members.append(
            sd.Member(get_type_name(member_type), member.name(), member.member_offset())
        )
    td[original_type_name] = top_struct

    # sd.print_struct(top_struct)
    # print("In the global type dict:")
    # for key in sd.typedict:
    #     print(key, sd.typedict[key])
    s = dict_to_json(original_type_name, td)
    d = json.loads(s)
    print("d=")
    print(d)
    print("dumps=")
    print(json.dumps(d))


def main(var_name: str, file: str):
    with open(file, "rb") as f:
        e = ELFFile(f)  # need to keep f open when e is being used
        rst = find_sym_addr_size(e, var_name)
        if rst is None:
            print("Not find variable in .symtab")
            sys.exit(1)
        addr, size = rst
        print(f"{var_name} is at addr {addr}, has size {size}")
        if not e.has_dwarf_info():
            print("No DWARF info")
            sys.exit(1)
        d = e.get_dwarf_info()
        for CU in d.iter_CUs():
            die = CU.get_top_DIE()
            v = find_variable(die, var_name)
        if v is None:
            print("Not find variable in dwarf")
            sys.exit(1)
        t = v.attributes[DW_AT.type]
        var_type = d.get_DIE_from_refaddr(t.value)
        # process_struct(resolve_typedef(var_type), 0, "")
        process_top_type(var_type)


main("g_param", "D:/workspace/cx/learn/llvm/objdump/example.o")
# "D:/workspace/Ecs/Ecm/Ecm.sdk/build/CcuCore0.elf"
