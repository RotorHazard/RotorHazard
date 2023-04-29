import argparse
import json


def mrkd2json(inp):
    lines = inp.split('\n')
    ret = []
    keys = []
    for i, l in enumerate(lines):
        if i == 0:
            keys = [_i.strip() for _i in l.split('|')]
        elif i == 1:
            continue
        else:
            ret.append(
                {keys[_i]: int(v.strip()) if v.strip().isdigit() else v.strip() for _i, v in enumerate(l.split('|'))
                 if 0 < _i < len(keys) - 1})
    return json.dumps(ret, indent=4)


def convert_file(infile, outfile):
    with open(infile, 'r') as i:
        markdown_table = i.read()

    json_dict = mrkd2json(markdown_table)

    with open(outfile, 'w') as o:
        o.write(json_dict)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='md_table_to_json',
                                     description='converts a file containing a markdown table into a json file',
                                     )
    parser.add_argument("markdown_input",
                        help="input file containing markdown table")
    parser.add_argument("json_output",
                        help="output file containing json data")
    args = parser.parse_args()

    convert_file(args.markdown_input, args.json_output)
