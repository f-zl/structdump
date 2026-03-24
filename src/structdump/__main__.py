from structdump import get_type_dict, meta
import json

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="object or execuable file", required=True)
    parser.add_argument("--variable", help="struct object's name", required=True)
    parser.add_argument(
        "--srcsuffix",
        help="suffix of src file, e.g. 'a.c', providing a srcsuffix improves find performance",
    )
    args = parser.parse_args()
    r = get_type_dict(args.file, args.variable, args.srcsuffix)
    print(json.dumps(r, cls=meta.JSONEncoder))
