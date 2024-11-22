# structdump

structdump is a tool and library to dump C struct in an object or executable file. The dumped result includes each member's type, name, offset, size.

## Usage

```c
// a.c
typedef struct {
	char char_member;
	int int_member;
} S;
S g_var;
```

```sh
gcc -g -c a.c # build the elf a.o with debugging information

# dump the struct variable as json to stdout in cmd line
python -m structdump --file a.o --variable g_var
```

Output the following json (formatted by VSCode):

```json
{
	"char": {
		"kind": "base",
		"name": "char",
		"size": 1,
		"encoding": "signed_integral"
	},
	"int": {
		"kind": "base",
		"name": "int",
		"size": 4,
		"encoding": "signed_integral"
	},
	"S": {
		"kind": "struct",
		"name": "S",
		"size": 8,
		"members": [
			{
				"type": "char",
				"name": "char_member",
				"offset": 0,
				"size": 1
			},
			{
				"type": "int",
				"name": "int_member",
				"offset": 4,
				"size": 4
			}
		]
	}
}
```

```py
# get the object equvalent of the dumped json in python
import structdump as sd
file = "a.o"
variable = "g_var"
typename, td = sd.get_type_dict(file, variable)
# td contains type information about the C struct and the types the struct members depend on
print(f"{variable} has type {typename}")
print(td.to_json())
```

## Install

```sh
git clone <this_repo>
pip install ./structdump
```

## TODO

add examples

- read variables from .data, .rodata
- generate functions to deserialize a struct
