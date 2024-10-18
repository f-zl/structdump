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
import sys

var_name = "g_param"
# file = "D:/workspace/Ecs/Ecm/Ecm.sdk/build/CcuCore0.elf"
file = "D:/workspace/cx/learn/llvm/objdump/example.o"


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


def find_variable(die: DIE):
    if die.tag == DW_TAG.variable and die.attributes[DW_AT.name].value == bytes(
        var_name, "ascii"
    ):
        return die
    for c in die.iter_children():
        if find_variable(c):
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
            return "(Unknown)"


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


f = open(file, "rb")
e = ELFFile(f)
rst = find_sym_addr_size(e, var_name)
if rst is None:
    print("Not find variable in .symtab")
    sys.exit(1)
addr, size = rst
print(f"addr {addr}, size {size}")
if not e.has_dwarf_info():
    print("No DWARF info")
    sys.exit(1)
d = e.get_dwarf_info()
for CU in d.iter_CUs():
    die = CU.get_top_DIE()
    v = find_variable(die)
if v is None:
    print("Not find variable in dwarf")
    sys.exit(1)
t = v.attributes[DW_AT.type]
var_type = d.get_DIE_from_refaddr(t.value)
var_type = resolve_typedef(var_type)
process_struct(var_type, 0, "")
