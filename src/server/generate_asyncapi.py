"""Generate AsyncAPI schema for RotorHazard Socket.IO events."""

import argparse
import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate src/server/asyncapi.yaml")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).parent.parent.parent / "DronlyWork" / "asyncapi.yaml",
        help="Output YAML path. Defaults to src/server/asyncapi.yaml",
    )
    args = parser.parse_args()
    output_path = args.output.resolve()
    console_out = sys.__stdout__

    os.environ["RH_GENERATE_ASYNCAPI"] = "1"

    with tempfile.TemporaryDirectory(prefix="rotorhazard-asyncapi-") as temp_home:
        os.environ["HOME"] = temp_home

        import server

        yaml_doc = server.SOCKET_IO.asyncapi_doc.get_yaml()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_doc, encoding="utf-8")

    console_out.write("AsyncAPI schema generated: {}\n".format(output_path))
    console_out.flush()
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.__stdout__.flush()
    sys.__stderr__.flush()
    os._exit(exit_code)
