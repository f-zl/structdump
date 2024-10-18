# 需求
dump C结构体的成员、类型、size、offset信息

导出内容需要方便解析、阅读
	由于是树结构，考虑用json
	有些是公共节点，比如类型，可以有一张表来查，节点值只存key，key用字符串提高可读性


# 设计

例子
```c
typedef struct {
	int value[2];
} ArrayInt2;
typedef struct {
	int x; // offset 0
	float y[3]; // offset 4
	char c; // offset 16
	ArrayInt2 arr; // offset 20
} MyStruct;
```
输出1
```json
[{
	"kind": "struct",
	"name": "MyStruct",
	"size": 28,
	"member": [
		{
			"type": "int",
			"name": "x",
			"offset": 0
		},
		{
			"type": "float[]",
			"name": "y",
			"length": 3,
			"offset": 4
		},
		{
			"type": "char",
			"name": "c",
			"offset": 16
		},
		{
			"type": "ArrayInt2",
			"name": "arr",
			"offset": 20
		}
	]
},
{
	"kind": "base",
	"name": "int",
	"size": 4
},
{
	"kind": "base",
	"name": "float",
	"size": 4
},
{
	"kind": "base",
	"name": "char",
	"size": 1
},
{
	"kind": "struct",
	"name": "ArrayInt2",
	"size": 8,
	"member": [
		{
			"type": "int[]",
			"name": "value",
			"length": 2,
			"offset": 0
		}
	]
}
]
```

每个field的size由type和length暗含
有些padding应该可以显示出来(不必)

type的取值
- base_type，比如int, float，像uint8_t这些也可以归到base_type。应该只分int/float，int类型有signed/unsigned
- array_type，比如int[]
- struct_type
- typedef，有最终解析出来的一个underlying type
- enum_type
- atomic_type，因为_Atomic(T)可以和T有不用的bit representation

union, bitfield先不考虑

## 数据结构
C结构体是一个树结构，可以用类DWARF的格式
