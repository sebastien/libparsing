#!/usr/bin/env python3
# encoding: utf8
"""
JSON Parser Benchmark
=====================

Compares parsing performance of three JSON parsers:
  1. libparsing  (examples/json_parser.py)
  2. lark        (deps/lark/examples/json_parser.py)
  3. json.loads  (Python stdlib baseline)

Generates synthetic JSON datasets of ~1KB, ~100KB, and ~1MB, then runs each
parser multiple times and reports timing statistics.

Usage:
    python examples/benchmark_json.py
    python examples/benchmark_json.py --iterations 20
"""

import sys
import os
import json
import time
import random
import string
import argparse

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src", "python"))
sys.path.insert(0, os.path.join(_ROOT, "deps", "lark"))


# ---------------------------------------------------------------------------
# Synthetic JSON data generation
# ---------------------------------------------------------------------------


def random_string(min_len=1, max_len=20):
    """Generate a random JSON-safe string."""
    length = random.randint(min_len, max_len)
    chars = string.ascii_letters + string.digits + " _-.,!?;:()"
    return "".join(random.choice(chars) for _ in range(length))


def random_value(depth=0, max_depth=4):
    """Generate a random JSON value, limiting nesting depth."""
    if depth >= max_depth:
        # At max depth, only produce scalars
        choice = random.randint(0, 4)
    else:
        choice = random.randint(0, 6)

    if choice == 0:
        return random.randint(-1000, 1000)
    elif choice == 1:
        return round(random.uniform(-1000, 1000), 4)
    elif choice == 2:
        return random_string()
    elif choice == 3:
        return random.choice([True, False])
    elif choice == 4:
        return None
    elif choice == 5:
        # Generate array
        n = random.randint(0, 6)
        return [random_value(depth + 1, max_depth) for _ in range(n)]
    else:
        # Generate object
        n = random.randint(0, 6)
        return {
            random_string(3, 12): random_value(depth + 1, max_depth) for _ in range(n)
        }


def generate_json(target_bytes):
    """Generate a JSON string of approximately `target_bytes` size.

    Builds an array of random objects until the target size is reached.
    """
    items = []
    current = "[]"
    while len(current) < target_bytes:
        obj = {
            random_string(3, 10): random_value(depth=0, max_depth=3)
            for _ in range(random.randint(2, 8))
        }
        items.append(obj)
        current = json.dumps(items)
    return current


# ---------------------------------------------------------------------------
# Parser loading
# ---------------------------------------------------------------------------


def load_libparsing_parser():
    """Load the libparsing JSON parser."""
    from examples.json_parser import parse

    # Warm up (triggers grammar construction + preparation)
    parse('{"a": 1}')
    return parse


def load_lark_parser():
    """Load the lark JSON parser."""
    from examples.json_parser import parse

    # Warm up (triggers LALR table generation)
    parse('{"a": 1}')
    return parse


def load_stdlib_parser():
    """Return json.loads as a parser."""
    return json.loads


# ---------------------------------------------------------------------------
# Benchmarking
# ---------------------------------------------------------------------------


def bench(parser_fn, data, iterations):
    """Run `parser_fn(data)` for `iterations` times, return list of elapsed times."""
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        parser_fn(data)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return times


def median(values):
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def format_time(seconds):
    """Format seconds into a human-readable string."""
    if seconds < 0.001:
        return "{:8.1f} us".format(seconds * 1_000_000)
    elif seconds < 1.0:
        return "{:8.2f} ms".format(seconds * 1000)
    else:
        return "{:8.3f} s ".format(seconds)


def format_throughput(byte_count, seconds):
    """Format throughput as MB/s or KB/s."""
    if seconds == 0:
        return "       inf"
    bps = byte_count / seconds
    if bps >= 1_000_000:
        return "{:7.2f} MB/s".format(bps / 1_000_000)
    else:
        return "{:7.1f} KB/s".format(bps / 1_000)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Benchmark JSON parsers")
    ap.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=10,
        help="Number of iterations per parser per dataset (default: 10)",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible datasets (default: 42)",
    )
    args = ap.parse_args()

    random.seed(args.seed)
    iterations = args.iterations

    # -- Generate datasets
    SIZES = [
        ("1 KB", 1_000),
        ("100 KB", 100_000),
        ("1 MB", 1_000_000),
    ]

    print("Generating synthetic JSON datasets (seed={}) ...".format(args.seed))
    datasets = []
    for label, target in SIZES:
        data = generate_json(target)
        actual_kb = len(data) / 1024
        datasets.append((label, data))
        print(
            "  {:>6s}  ->  {:,.1f} KB ({:,d} bytes)".format(label, actual_kb, len(data))
        )
    print()

    # -- Correctness check
    print("Verifying all parsers produce identical output ...")
    sys.path.insert(0, _ROOT)

    # Import libparsing parser
    import examples.json_parser as lp_mod

    lp_parse = lp_mod.parse
    lp_parse('{"a":1}')  # warm up

    # Import lark parser - needs separate import since module names collide
    # We import lark's parser module directly
    import importlib.util

    lark_spec = importlib.util.spec_from_file_location(
        "lark_json_parser",
        os.path.join(_ROOT, "deps", "lark", "examples", "json_parser.py"),
    )
    lark_mod = importlib.util.module_from_spec(lark_spec)
    lark_spec.loader.exec_module(lark_mod)
    lark_parse = lark_mod.parse
    lark_parse('{"a":1}')  # warm up

    stdlib_parse = json.loads

    for label, data in datasets:
        expected = stdlib_parse(data)
        lp_result = lp_parse(data)
        lark_result = lark_parse(data)
        assert lp_result == expected, "libparsing mismatch on {}".format(label)
        assert lark_result == expected, "lark mismatch on {}".format(label)
    print("  All parsers agree.\n")

    # -- Benchmark
    parsers = [
        ("json.loads", stdlib_parse),
        ("libparsing", lp_parse),
        ("lark", lark_parse),
    ]

    SEP = "-" * 78
    print("Benchmark: {} iterations per parser per dataset".format(iterations))
    print(SEP)
    print(
        "{:<10s} {:<12s} {:>12s} {:>12s} {:>12s} {:>10s}".format(
            "Dataset",
            "Parser",
            "Median",
            "Mean",
            "Throughput",
            "vs stdlib",
        )
    )
    print(SEP)

    for label, data in datasets:
        byte_count = len(data)
        baseline_median = None
        for pname, pfn in parsers:
            times = bench(pfn, data, iterations)
            med = median(times)
            avg = sum(times) / len(times)
            tp = format_throughput(byte_count, med)

            if pname == "json.loads":
                baseline_median = med
                ratio_str = "   1.00x"
            else:
                if baseline_median and baseline_median > 0:
                    ratio = med / baseline_median
                    ratio_str = "{:7.1f}x".format(ratio)
                else:
                    ratio_str = "     N/A"

            print(
                "{:<10s} {:<12s} {:>12s} {:>12s} {:>12s} {:>10s}".format(
                    label if pname == parsers[0][0] else "",
                    pname,
                    format_time(med),
                    format_time(avg),
                    tp,
                    ratio_str,
                )
            )
        print(SEP)

    print()
    print(
        "Note: 'vs stdlib' shows how many times slower than json.loads (lower is better)."
    )
    print("      json.loads is a C extension and serves as baseline reference.")


if __name__ == "__main__":
    main()

# EOF
