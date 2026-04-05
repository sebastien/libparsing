#!/usr/bin/env python3
# encoding: utf8
"""
JSON Parser Benchmark
=====================

Compares parsing performance of JSON parsers across implementations:
  - json.loads      (Python stdlib C extension - baseline)
  - libparsing/C    (examples/json_parser.c  - pure C with libparsing)
  - libparsing/py   (examples/json_parser.py - CPython with libparsing)
  - lark/py         (deps/lark/examples/json_parser.py - CPython)
  - libparsing/pypy (examples/json_parser.py - PyPy with libparsing)
  - lark/pypy       (deps/lark/examples/json_parser.py - PyPy)

Generates synthetic JSON datasets of ~1KB, ~100KB, and ~1MB, then runs each
parser multiple times and reports timing statistics.

Usage:
    python examples/benchmark_json.py
    python examples/benchmark_json.py --iterations 20
    python examples/benchmark_json.py --no-pypy       # skip PyPy benchmarks
"""

import sys
import os
import json
import time
import random
import string
import shutil
import argparse
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src", "python"))
sys.path.insert(0, os.path.join(_ROOT, "deps", "lark"))

# C binary path
_C_BINARY = os.path.join(_ROOT, "dist", "json_parser")
# Bench runner script (for subprocess-based benchmarks)
_BENCH_RUNNER = os.path.join(_HERE, "_bench_runner.py")


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
        n = random.randint(0, 6)
        return [random_value(depth + 1, max_depth) for _ in range(n)]
    else:
        n = random.randint(0, 6)
        return {
            random_string(3, 12): random_value(depth + 1, max_depth) for _ in range(n)
        }


def generate_json(target_bytes):
    """Generate a JSON string of approximately `target_bytes` size."""
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
# C binary helpers
# ---------------------------------------------------------------------------


def ensure_c_binary():
    """Compile the C JSON parser if the binary doesn't exist or is outdated."""
    c_source = os.path.join(_ROOT, "examples", "json_parser.c")
    parsing_c = os.path.join(_ROOT, "src", "c", "parsing.c")

    if os.path.exists(_C_BINARY):
        bin_mtime = os.path.getmtime(_C_BINARY)
        src_mtime = max(os.path.getmtime(c_source), os.path.getmtime(parsing_c))
        if bin_mtime > src_mtime:
            return True

    print("  Compiling C JSON parser ...")
    try:
        pcre_cflags = subprocess.check_output(
            ["pkg-config", "--cflags", "libpcre"], text=True
        ).strip()
        pcre_libs = subprocess.check_output(
            ["pkg-config", "--libs", "libpcre"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pcre_cflags = ""
        pcre_libs = "-lpcre"

    cmd = (
        "gcc -O3 -DNDEBUG -I {includes} {pcre_cflags} -DWITH_PCRE "
        "{source} {parsing_c} {pcre_libs} -o {output}"
    ).format(
        includes=os.path.join(_ROOT, "src", "h"),
        pcre_cflags=pcre_cflags,
        source=c_source,
        parsing_c=parsing_c,
        pcre_libs=pcre_libs,
        output=_C_BINARY,
    )

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("  WARNING: Failed to compile C parser:")
        print("  " + result.stderr.strip())
        return False

    print("  Compiled: {}".format(_C_BINARY))
    return True


# ---------------------------------------------------------------------------
# Subprocess benchmark runners
# ---------------------------------------------------------------------------


def _parse_runner_output(stdout):
    """Parse output from _bench_runner.py or json_parser --benchmark.

    Returns list of per-iteration times.
    """
    parts = stdout.strip().split()
    avg_time = float(parts[0])
    n = int(parts[2])
    # If per-iteration times are provided (parts[4:]), use them
    if len(parts) > 4:
        return [float(t) for t in parts[4:]]
    # Otherwise replicate the average
    return [avg_time] * n


def bench_c_binary(filepath, iterations):
    """Run the C binary in --benchmark mode."""
    env = os.environ.copy()
    ld_path = os.path.join(_ROOT, "dist")
    env["LD_LIBRARY_PATH"] = ld_path + ":" + env.get("LD_LIBRARY_PATH", "")

    result = subprocess.run(
        [_C_BINARY, "--benchmark", str(iterations), filepath],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError("C parser failed: {}".format(result.stderr.strip()))
    return _parse_runner_output(result.stdout)


def bench_subprocess(interpreter, parser_name, filepath, iterations):
    """Run _bench_runner.py under the given interpreter."""
    env = os.environ.copy()
    ld_path = os.path.join(_ROOT, "dist")
    env["LD_LIBRARY_PATH"] = ld_path + ":" + env.get("LD_LIBRARY_PATH", "")

    result = subprocess.run(
        [interpreter, _BENCH_RUNNER, parser_name, filepath, str(iterations)],
        capture_output=True,
        text=True,
        env=env,
        cwd=_ROOT,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "{} {} failed: {}".format(
                interpreter, parser_name, result.stderr.strip()[:200]
            )
        )
    return _parse_runner_output(result.stdout)


# ---------------------------------------------------------------------------
# In-process benchmarking
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


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def median(values):
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def format_time(seconds):
    if seconds < 0.001:
        return "{:8.1f} us".format(seconds * 1_000_000)
    elif seconds < 1.0:
        return "{:8.2f} ms".format(seconds * 1000)
    else:
        return "{:8.3f} s ".format(seconds)


def format_throughput(byte_count, seconds):
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
    ap.add_argument(
        "--no-pypy",
        action="store_true",
        help="Skip PyPy benchmarks",
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

    # -- Prepare parsers
    print("Preparing parsers ...")
    has_c_parser = ensure_c_binary()

    # Detect PyPy
    pypy_bin = None
    if not args.no_pypy:
        for name in ("pypy3", "pypy3.11", "pypy3.10"):
            path = shutil.which(name)
            if path:
                pypy_bin = path
                break
        if pypy_bin:
            # Verify it works with our runner
            try:
                r = subprocess.run(
                    [pypy_bin, "-c", "import cffi; print('ok')"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if r.returncode != 0:
                    print(
                        "  WARNING: PyPy3 found but cffi unavailable, skipping PyPy benchmarks"
                    )
                    pypy_bin = None
                else:
                    pypy_ver = (
                        subprocess.check_output(
                            [pypy_bin, "--version"], text=True, stderr=subprocess.STDOUT
                        )
                        .strip()
                        .split("\n")[0]
                    )
                    print("  PyPy detected: {} ({})".format(pypy_bin, pypy_ver))
            except Exception as e:
                print("  WARNING: PyPy3 check failed ({}), skipping".format(e))
                pypy_bin = None
        else:
            print("  PyPy3 not found, skipping PyPy benchmarks")

    # -- Import CPython parsers (in-process)
    sys.path.insert(0, _ROOT)

    import examples.json_parser as lp_mod

    lp_parse = lp_mod.parse
    lp_parse('{"a":1}')  # warm up

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

    # -- Correctness checks
    print("\nVerifying parsers ...")
    for label, data in datasets:
        expected = stdlib_parse(data)
        assert lp_parse(data) == expected, "libparsing/py mismatch on {}".format(label)
        assert lark_parse(data) == expected, "lark mismatch on {}".format(label)
    print("  CPython parsers: OK")

    if has_c_parser:
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = (
            os.path.join(_ROOT, "dist") + ":" + env.get("LD_LIBRARY_PATH", "")
        )
        cr = subprocess.run(
            [_C_BINARY, "--test"], capture_output=True, text=True, env=env
        )
        if cr.returncode == 0:
            print("  C parser self-test: OK")
        else:
            print("  C parser self-test: FAILED")
            has_c_parser = False

    if pypy_bin:
        # Quick correctness check via runner on small dataset
        try:
            r = subprocess.run(
                [pypy_bin, _BENCH_RUNNER, "libparsing", "/dev/stdin", "1"],
                input='{"test":true}',
                capture_output=True,
                text=True,
                cwd=_ROOT,
                timeout=30,
            )
            if r.returncode == 0:
                print("  PyPy parsers: OK")
            else:
                print(
                    "  WARNING: PyPy runner failed, skipping: " + r.stderr.strip()[:120]
                )
                pypy_bin = None
        except Exception as e:
            print("  WARNING: PyPy check failed ({}), skipping".format(e))
            pypy_bin = None

    print()

    # -- Write datasets to temp files (needed for subprocess-based parsers)
    temp_files = []
    for label, data in datasets:
        tf = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="bench_"
        )
        tf.write(data)
        tf.close()
        temp_files.append(tf.name)

    # -- PyPy warm-up: run once on the largest dataset to trigger JIT compilation
    if pypy_bin:
        print("Warming up PyPy JIT (one pass on largest dataset) ...")
        for parser_name in ("libparsing", "lark"):
            try:
                bench_subprocess(pypy_bin, parser_name, temp_files[-1], 1)
            except Exception:
                pass  # non-fatal
        print()

    # -- Benchmark
    SEP = "-" * 90
    print("Benchmark: {} iterations per parser per dataset".format(iterations))
    print(SEP)
    print(
        "{:<10s} {:<16s} {:>12s} {:>12s} {:>12s} {:>12s}".format(
            "Dataset",
            "Parser",
            "Median",
            "Mean",
            "Throughput",
            "vs stdlib",
        )
    )
    print(SEP)

    for di, (label, data) in enumerate(datasets):
        byte_count = len(data)
        baseline_median = None

        # Collect results: list of (name, times)
        results = []

        # 1) json.loads (CPython, in-process)
        times = bench(stdlib_parse, data, iterations)
        results.append(("json.loads", times))

        # 2) libparsing/C
        if has_c_parser:
            try:
                results.append(
                    ("libparsing/C", bench_c_binary(temp_files[di], iterations))
                )
            except Exception as e:
                print("  WARNING: C benchmark failed: {}".format(e))

        # 3) libparsing/py (CPython, in-process)
        results.append(("libparsing/py", bench(lp_parse, data, iterations)))

        # 4) lark (CPython, in-process)
        results.append(("lark/py", bench(lark_parse, data, iterations)))

        # 5) libparsing/pypy (subprocess)
        if pypy_bin:
            try:
                results.append(
                    (
                        "libparsing/pypy",
                        bench_subprocess(
                            pypy_bin, "libparsing", temp_files[di], iterations
                        ),
                    )
                )
            except Exception as e:
                print("  WARNING: PyPy libparsing failed: {}".format(e))

        # 6) lark/pypy (subprocess)
        if pypy_bin:
            try:
                results.append(
                    (
                        "lark/pypy",
                        bench_subprocess(pypy_bin, "lark", temp_files[di], iterations),
                    )
                )
            except Exception as e:
                print("  WARNING: PyPy lark failed: {}".format(e))

        # Print results
        for ri, (pname, ptimes) in enumerate(results):
            med = median(ptimes)
            avg = sum(ptimes) / len(ptimes)
            tp = format_throughput(byte_count, med)

            if pname == "json.loads":
                baseline_median = med
                ratio_str = "     1.00x"
            else:
                if baseline_median and baseline_median > 0:
                    ratio = med / baseline_median
                    ratio_str = "{:9.1f}x".format(ratio)
                else:
                    ratio_str = "       N/A"

            print(
                "{:<10s} {:<16s} {:>12s} {:>12s} {:>12s} {:>12s}".format(
                    label if ri == 0 else "",
                    pname,
                    format_time(med),
                    format_time(avg),
                    tp,
                    ratio_str,
                )
            )
        print(SEP)

    # -- Cleanup
    for tf in temp_files:
        try:
            os.unlink(tf)
        except OSError:
            pass

    print()
    print("Notes:")
    print("  'vs stdlib' = times slower than json.loads (lower is better)")
    print("  json.loads is a C extension and serves as baseline reference")
    if has_c_parser:
        print(
            "  libparsing/C uses subprocess; overhead is negligible for large datasets"
        )
    if pypy_bin:
        print("  PyPy benchmarks use subprocess with pre-warmed JIT")
        print(
            "  '/py' = CPython {}.{}, '/pypy' = PyPy".format(
                sys.version_info.major, sys.version_info.minor
            )
        )


if __name__ == "__main__":
    main()

# EOF
