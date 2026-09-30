"""Small command-line interface for CSP token inspection."""

from __future__ import annotations

import argparse

from .core import CspCodec, DecodeError


def main() -> int:
    parser = argparse.ArgumentParser(description="Encode or decode one CSP-1 token")
    commands = parser.add_subparsers(dest="command", required=True)

    encode_parser = commands.add_parser("encode")
    encode_parser.add_argument("token", help="Token in CLASS.concept form")

    decode_parser = commands.add_parser("decode")
    decode_parser.add_argument("notes", nargs=5, help="Five note names")

    args = parser.parse_args()
    codec = CspCodec.from_default_spec()

    if args.command == "encode":
        result = codec.encode_token(args.token)
        print(" ".join(result.notes))
        return 0

    try:
        result = codec.decode_token(args.notes)
    except DecodeError as error:
        print(f"UNCERTAIN: {error}")
        return 2
    print(result.token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
