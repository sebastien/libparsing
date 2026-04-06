#!/usr/bin/env bun
// ----------------------------------------------------------------------------
// Simple JSON Parser (TypeScript / libparsing)
// ----------------------------------------------------------------------------
// A JSON parser implemented with libparsing, equivalent to the Python version
// at examples/json_parser.py. Parses JSON text and transforms the parse tree
// into native JavaScript objects.
//
// Usage:
//     bun examples/json_parser.ts <file.json>
//     bun examples/json_parser.ts --test
// ----------------------------------------------------------------------------

import {
    Grammar,
    Processor,
    Match,
    Token,
    Recognizers,
    UNMATCHED,
} from "../src/ts/libparsing";

// ==========================================================================
//
// Grammar Definition
//
// ==========================================================================

function grammar(isVerbose = false): Grammar {
    const g = new Grammar({ isVerbose });
    g.setNoMemo();           // JSON grammar doesn't benefit from memoisation
    g.setSkipWhitespace();   // Use fast hand-coded whitespace skip
    const s = g.symbols;

    // -- Tokens
    g.token("WS", "\\s+");
    // JSON numbers: optional sign, integer or decimal, optional exponent
    g.token("NUMBER", "[+\\-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+\\-]?\\d+)?")
        .setCustomRecognize(Recognizers.jsonNumber);
    // JSON strings: double-quoted with backslash escapes
    g.token("STRING", '"([^"\\\\]|\\\\.)*"')
        .setCustomRecognize(Recognizers.jsonString);
    g.token("TRUE", "true");
    g.token("FALSE", "false");
    g.token("NULL", "null");

    // -- Words (literal delimiters)
    g.word("LBRACE", "{");
    g.word("RBRACE", "}");
    g.word("LBRACKET", "[");
    g.word("RBRACKET", "]");
    g.word("COMMA", ",");
    g.word("COLON", ":");

    // -- Grammar rules
    // Forward-declare Value (needed for recursion in Object/Array)
    g.group("Value");

    // Object: { pair (, pair)* }
    g.rule("Pair", s.STRING._as("key"), s.COLON, s.Value._as("value"));
    g.rule("PairSuffix", s.COMMA, s.Pair._as("pair"));
    g.rule(
        "Object",
        s.LBRACE,
        s.Pair.optional()._as("first"),
        s.PairSuffix.zeroOrMore()._as("rest"),
        s.RBRACE
    );

    // Array: [ value (, value)* ]
    g.rule("ValueSuffix", s.COMMA, s.Value._as("value"));
    g.rule(
        "Array",
        s.LBRACKET,
        s.Value.optional()._as("first"),
        s.ValueSuffix.zeroOrMore()._as("rest"),
        s.RBRACKET
    );

    // Value alternatives (set after Object/Array are defined)
    s.Value.set(s.Object, s.Array, s.STRING, s.NUMBER, s.TRUE, s.FALSE, s.NULL);

    g.axiom = s.Value;
    g.skip = s.WS;
    return g;
}

// ==========================================================================
//
// JSON String Escape Handling
//
// ==========================================================================

const _ESCAPE_RE = /\\(["\\\/bfnrt]|u[0-9a-fA-F]{4})/g;
const _ESCAPE_MAP: Record<string, string> = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    b: "\b",
    f: "\f",
    n: "\n",
    r: "\r",
    t: "\t",
};

function decodeJsonString(s: string): string {
    // Remove surrounding quotes
    const inner = s.slice(1, -1);
    // Fast path: most JSON strings have no escapes
    if (inner.indexOf("\\") === -1) return inner;
    return inner.replace(_ESCAPE_RE, (_: string, seq: string) => {
        if (seq[0] === "u") return String.fromCharCode(parseInt(seq.slice(1), 16));
        return _ESCAPE_MAP[seq];
    });
}

// ==========================================================================
//
// Tree-to-JSON Processor
//
// ==========================================================================

class TreeToJson extends Processor {
    onSTRING(match: Match): string {
        return decodeJsonString(match.group()[0]);
    }

    onNUMBER(match: Match): number {
        return parseFloat(match.group()[0]);
    }

    onTRUE(_match: Match): boolean {
        return true;
    }

    onFALSE(_match: Match): boolean {
        return false;
    }

    onNULL(_match: Match): null {
        return null;
    }

    onPair(match: Match, key: Match, value: Match): [string, unknown] {
        const k = this.process(key) as string;
        const v = this.process(value);
        return [k, v];
    }

    onPairSuffix(match: Match, pair: Match): unknown {
        return this.process(pair);
    }

    onObject(match: Match, first: Match | typeof UNMATCHED, rest: Match | typeof UNMATCHED): Record<string, unknown> {
        const pairs: [string, unknown][] = [];
        if (first !== UNMATCHED) {
            const f = this.process(first as Match) as [string, unknown] | null;
            if (f !== null) pairs.push(f);
        }
        if (rest !== UNMATCHED) {
            const r = this.process(rest as Match) as [string, unknown][] | null;
            if (r && Array.isArray(r)) pairs.push(...r);
        }
        return Object.fromEntries(pairs);
    }

    onValueSuffix(match: Match, value: Match): unknown {
        return this.process(value);
    }

    onArray(match: Match, first: Match | typeof UNMATCHED, rest: Match | typeof UNMATCHED): unknown[] {
        const items: unknown[] = [];
        if (first !== UNMATCHED) {
            items.push(this.process(first as Match));
        }
        if (rest !== UNMATCHED) {
            const r = this.process(rest as Match) as unknown[] | null;
            if (r && Array.isArray(r)) items.push(...r);
        }
        return items;
    }

    onValue(match: Match): unknown {
        const child = match.get(0) as Match | null;
        if (!child) return null;
        return this.process(child);
    }
}

// ==========================================================================
//
// Public API
//
// ==========================================================================

let _grammar: Grammar | null = null;
let _processor: TreeToJson | null = null;

function init(): void {
    if (_grammar === null) {
        _grammar = grammar();
        _grammar.prepare();
        _processor = new TreeToJson(_grammar);
    }
}

export function parse(text: string): unknown {
    init();
    const result = _grammar!.parseString(text);
    if (result.isFailure()) {
        throw new Error("JSON parse error: " + result.describe());
    }
    return _processor!.process(result.match!);
}

// ==========================================================================
//
// Test
//
// ==========================================================================

function test(): void {
    const testJson = `
        {
            "empty_object" : {},
            "empty_array"  : [],
            "booleans"     : { "YES" : true, "NO" : false },
            "numbers"      : [ 0, 1, -2, 3.3, 4.4e5, 6.6e-7 ],
            "strings"      : [ "This", [ "And" , "That", "And a \\"b" ] ],
            "nothing"      : null
        }
    `;

    const j = parse(testJson);
    const expected = JSON.parse(testJson);

    // Deep comparison
    const jStr = JSON.stringify(j, null, 2);
    const eStr = JSON.stringify(expected, null, 2);
    if (jStr !== eStr) {
        console.error("MISMATCH:");
        console.error("  got:     ", jStr);
        console.error("  expected:", eStr);
        process.exit(1);
    }
    console.log("OK - parsed JSON matches JSON.parse output");
    console.log(j);
}

// ==========================================================================
//
// CLI
//
// ==========================================================================

if (import.meta.main) {
    const args = process.argv.slice(2);
    if (args.length > 0 && args[0] !== "--test") {
        const file = args[0];
        const text = await Bun.file(file).text();
        console.log(JSON.stringify(parse(text), null, 2));
    } else {
        test();
    }
}
