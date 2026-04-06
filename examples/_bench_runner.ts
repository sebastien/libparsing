#!/usr/bin/env bun
// ----------------------------------------------------------------------------
// JSON Parser Benchmark Runner (subprocess helper — TypeScript/Bun)
// ----------------------------------------------------------------------------
// Standalone script that benchmarks the libparsing TypeScript JSON parser on a
// given input file. Designed to be invoked by benchmark_json.py.
//
// Usage:
//     bun examples/_bench_runner.ts libparsing <file.json> <iterations>
//
// Output (stdout, machine-readable):
//     <avg_seconds> <total_seconds> <iterations> <bytes> [per-iteration-times...]
// ----------------------------------------------------------------------------

import { parse } from "./json_parser";

function main(): void {
    const args = process.argv.slice(2);
    if (args.length !== 3) {
        process.stderr.write(
            `Usage: ${process.argv[1]} <libparsing> <file.json> <iterations>\n`
        );
        process.exit(1);
    }

    const parserName = args[0];
    const filepath = args[1];
    const iterations = parseInt(args[2], 10);

    if (parserName !== "libparsing") {
        process.stderr.write(`Unknown parser: ${parserName}\n`);
        process.exit(1);
    }

    // Read input
    const data = require("fs").readFileSync(filepath, "utf-8") as string;
    const byteCount = Buffer.byteLength(data, "utf-8");

    // Warm up (JIT compilation, grammar preparation, etc.)
    parse('{"a": 1}');
    parse(data);

    // Timed iterations
    const times: number[] = [];
    for (let i = 0; i < iterations; i++) {
        const t0 = performance.now();
        parse(data);
        const t1 = performance.now();
        times.push((t1 - t0) / 1000); // convert ms to seconds
    }

    const totalTime = times.reduce((a, b) => a + b, 0);
    const avgTime = totalTime / iterations;

    // Machine-readable output matching _bench_runner.py format:
    // avg total iterations bytes [per-iteration times...]
    const parts: string[] = [
        avgTime.toFixed(9),
        totalTime.toFixed(9),
        String(iterations),
        String(byteCount),
    ];
    for (const t of times) {
        parts.push(t.toFixed(9));
    }
    console.log(parts.join(" "));
}

main();
