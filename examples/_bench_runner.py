#!/usr/bin/env python3
# encoding: utf8
"""
JSON Parser Benchmark Runner (subprocess helper)
=================================================

A standalone script that benchmarks a single Python JSON parser on a given
input file. Designed to be invoked by benchmark_json.py under different
interpreters (CPython, PyPy).

Usage:
    python  examples/_bench_runner.py libparsing <file> <iterations>
    python  examples/_bench_runner.py lark       <file> <iterations>
    pypy3   examples/_bench_runner.py lark       <file> <iterations>

Output (stdout, machine-readable):
    <avg_seconds> <total_seconds> <iterations> <bytes>
"""

import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src", "python"))
sys.path.insert(0, os.path.join(_ROOT, "deps", "lark"))
sys.path.insert(0, _ROOT)


def main():
    if len(sys.argv) != 4:
        sys.stderr.write(
            "Usage: {} <libparsing|lark> <file.json> <iterations>\n".format(sys.argv[0])
        )
        sys.exit(1)

    parser_name = sys.argv[1]
    filepath = sys.argv[2]
    iterations = int(sys.argv[3])

    # Read input
    with open(filepath, "r") as f:
        data = f.read()
    byte_count = len(data)

    # Load parser
    if parser_name == "libparsing":
        from examples.json_parser import parse
    elif parser_name == "lark":
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "lark_json_parser",
            os.path.join(_ROOT, "deps", "lark", "examples", "json_parser.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        parse = mod.parse
    else:
        sys.stderr.write("Unknown parser: {}\n".format(parser_name))
        sys.exit(1)

    # Warm up (JIT compilation, grammar preparation, etc.)
    parse('{"a": 1}')
    parse(data)

    # Timed iterations
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        parse(data)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    total_time = sum(times)
    avg_time = total_time / iterations

    # Machine-readable output: one line per iteration, then summary
    # Format: avg total iterations bytes [per-iteration times...]
    parts = [
        "{:.9f}".format(avg_time),
        "{:.9f}".format(total_time),
        str(iterations),
        str(byte_count),
    ]
    for t in times:
        parts.append("{:.9f}".format(t))
    print(" ".join(parts))


if __name__ == "__main__":
    main()

# EOF
