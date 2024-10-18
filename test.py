A = "A"
B = "B"
a = input()
match a:
    case A:
        pass
    case B:
        pass

from enum import StrEnum


class E(StrEnum):
    A = "A"
    B = "B"


match a:
    case E.A:
        pass
    case E.B:
        pass
