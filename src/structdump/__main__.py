from structdump import get_type_dict, structdump
import json

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="object or execuable file", required=True)
    parser.add_argument("--variable", help="struct object's name", required=True)
    parser.add_argument("--srcsuffix", help="suffix of src file")
    args = parser.parse_args()
    r = get_type_dict(args.file, args.variable, args.srcsuffix)
    print(json.dumps(r, cls=structdump.JSONEncoder))
