from structdump import get_type_dict


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="object or execuable file", required=True)
    parser.add_argument("--variable", help="the struct object's name", required=True)
    args = parser.parse_args()
    typename, td, le = get_type_dict(args.file, args.variable)
    print(f"{args.variable} has type {typename} {'little' if le else 'big'} endian")
    print(td.to_json())
