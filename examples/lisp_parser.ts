#!/usr/bin/env bun
// ----------------------------------------------------------------------------
// Simple Lisp Parser (TypeScript / libparsing)
// ----------------------------------------------------------------------------
// A Lisp (S-expression) parser implemented with libparsing, equivalent to the
// Python version at examples/lisp_parser.py. Parses Lisp source code and
// transforms the parse tree into native JavaScript values.
//
// Features:
//   - Numbers (integers and floats, with optional sign)
//   - Symbols (identifiers and operators like +, -, <=, string->number)
//   - Strings (double-quoted with escape sequences)
//   - Comments (; to end of line, automatically skipped)
//   - Quote shorthand ('x desugars to ["quote", x])
//   - Proper lists: (a b c)
//   - Dotted pairs: (a . b), (a b . c)
//
// Usage:
//     bun examples/lisp_parser.ts <file.lsp>
//     bun examples/lisp_parser.ts --test
// ----------------------------------------------------------------------------

import {
    Grammar,
    Processor,
    Match,
    UNMATCHED,
} from "../src/ts/libparsing";

// ==========================================================================
//
// Dotted Pair Representation
//
// ==========================================================================

/**
 * Represents a Lisp dotted pair, distinguished from proper lists (Array).
 * For (a . b)     -> DottedPair [a, b]
 * For (a b . c)   -> DottedPair [a, b, c]  (last element is the cdr)
 */
class DottedPair extends Array<unknown> {
    readonly isDottedPair = true;

    constructor(...items: unknown[]) {
        super(...items);
        Object.setPrototypeOf(this, DottedPair.prototype);
    }
}

// ==========================================================================
//
// Grammar Definition
//
// ==========================================================================

function grammar(isVerbose = false): Grammar {
    const g = new Grammar({ isVerbose });
    const s = g.symbols;

    // -- Tokens
    // WS includes line comments (;...\n), consumed together with whitespace
    g.token("WS", "(\\s|;[^\\n]*)+");
    // Numbers: optional sign, integer or decimal
    g.token("NUMBER", "[+\\-]?\\d+(\\.\\d+)?");
    // Strings: double-quoted with backslash escape sequences
    g.token("STRING", '"([^"\\\\]|\\\\.)*"');
    // Symbols: identifiers and operators
    g.token(
        "SYMBOL",
        "[a-zA-Z!$%&*+\\-/:<=>?~_^][a-zA-Z0-9!$%&*+\\-/:<=>?~_^.]*|\\.\\.\\."
    );

    // -- Words (literal delimiters)
    g.word("QUOTE", "'");
    g.word("DOT", ".");
    g.word("LP", "(");
    g.word("RP", ")");

    // -- Grammar rules
    g.group("Atom", s.NUMBER, s.SYMBOL, s.STRING);

    // Forward-declare Expr for recursion (lists contain exprs)
    g.group("Expr");

    g.rule("Quoted", s.QUOTE, s.Expr._as("expr"));
    g.rule("DottedTail", s.DOT, s.Expr._as("expr"));
    g.rule(
        "List",
        s.LP,
        s.Expr.zeroOrMore()._as("items"),
        s.DottedTail.optional()._as("dotted"),
        s.RP
    );

    // Fill in Expr alternatives (order matters: Quoted first for ' prefix)
    s.Expr.set(s.Quoted, s.List, s.Atom);

    g.rule("Program", s.Expr.zeroOrMore()._as("expressions"));

    g.axiom = s.Program;
    g.skip = s.WS;
    return g;
}

// ==========================================================================
//
// Lisp String Escape Handling
//
// ==========================================================================

const _ESCAPE_RE = /\\(["\\nrt])/g;
const _ESCAPE_MAP: Record<string, string> = {
    '"': '"',
    "\\": "\\",
    n: "\n",
    r: "\r",
    t: "\t",
};

function decodeLispString(s: string): string {
    // Remove surrounding quotes
    const inner = s.slice(1, -1);
    // Fast path: most strings have no escapes
    if (inner.indexOf("\\") === -1) return inner;
    return inner.replace(_ESCAPE_RE, (_: string, seq: string) => {
        return _ESCAPE_MAP[seq] ?? seq;
    });
}

// ==========================================================================
//
// Tree-to-Native Processor
//
// ==========================================================================

class TreeToLisp extends Processor {
    onNUMBER(match: Match): number {
        const text = match.group()[0];
        return text.includes(".") ? parseFloat(text) : parseInt(text, 10);
    }

    onSTRING(match: Match): string {
        return decodeLispString(match.group()[0]);
    }

    onSYMBOL(match: Match): string {
        return match.group()[0];
    }

    onAtom(match: Match): unknown {
        const child = match.get(0) as Match;
        return this.process(child);
    }

    onQuoted(match: Match, expr: Match): unknown[] {
        return ["quote", this.process(expr)];
    }

    onDottedTail(match: Match, expr: Match): unknown {
        return this.process(expr);
    }

    onList(
        match: Match,
        items: Match,
        dotted: Match | typeof UNMATCHED
    ): unknown {
        const raw = this.process(items);
        const elements: unknown[] =
            raw && Array.isArray(raw) ? [...raw] : [];
        if (dotted !== UNMATCHED) {
            const tail = this.process(dotted as Match);
            return new DottedPair(...elements, tail);
        }
        return elements;
    }

    onExpr(match: Match): unknown {
        const child = match.get(0) as Match;
        return this.process(child);
    }

    onProgram(match: Match, expressions: Match): unknown[] {
        const raw = this.process(expressions);
        return raw && Array.isArray(raw) ? raw : [];
    }
}

// ==========================================================================
//
// Public API
//
// ==========================================================================

let _grammar: Grammar | null = null;
let _processor: TreeToLisp | null = null;

function init(): void {
    if (_grammar === null) {
        _grammar = grammar();
        _grammar.prepare();
        _processor = new TreeToLisp(_grammar);
    }
}

export function parse(text: string): unknown[] {
    init();
    const result = _grammar!.parseString(text);
    if (result.isFailure()) {
        throw new Error("Lisp parse error: " + result.describe());
    }
    return _processor!.process(result.match!) as unknown[];
}

// ==========================================================================
//
// Test
//
// ==========================================================================

/** Canonical string representation for test comparison. */
function repr(v: unknown): string {
    if (v === null) return "null";
    if (v === undefined) return "undefined";
    if (typeof v === "number") return String(v);
    if (typeof v === "string") return JSON.stringify(v);
    if (v instanceof DottedPair) {
        return `DottedPair(${Array.from(v).map(repr).join(", ")})`;
    }
    if (Array.isArray(v)) {
        return `[${v.map(repr).join(", ")}]`;
    }
    return String(v);
}

async function test(): Promise<void> {
    const cases: [string, string][] = [
        // Atoms
        ["42", "[42]"],
        ["-17", "[-17]"],
        ["3.14", "[3.14]"],
        ['"hello"', '["hello"]'],
        ["foo", '["foo"]'],
        ["+", '["+"]'],
        ["-", '["-"]'],
        ["<=", '["<="]'],
        ["string->number", '["string->number"]'],
        ["...", '["..."]'],
        // Simple lists
        ["(+ 1 2)", '[["+", 1, 2]]'],
        ["()", "[[]]"],
        ["(define x 42)", '[["define", "x", 42]]'],
        // Nested
        [
            "(define (square x) (* x x))",
            '[["define", ["square", "x"], ["*", "x", "x"]]]',
        ],
        // Quote
        ["'x", '[["quote", "x"]]'],
        ["'(1 2 3)", '[["quote", [1, 2, 3]]]'],
        // Dotted pairs
        ["(1 . 2)", "[DottedPair(1, 2)]"],
        ["(a b . c)", '[DottedPair("a", "b", "c")]'],
        // Multiple top-level
        ["1 2 3", "[1, 2, 3]"],
        // Comments
        ["; comment\n42", "[42]"],
        ["; line 1\n; line 2\n(+ 1 2)", '[["+", 1, 2]]'],
        // Strings with escapes
        ['"hello \\"world\\""', '["hello \\"world\\""]'],
        ['"line1\\nline2"', '["line1\\nline2"]'],
    ];

    let passed = 0;
    let failed = 0;

    for (const [input, expectedRepr] of cases) {
        try {
            const result = parse(input);
            const actualRepr = repr(result);
            if (actualRepr !== expectedRepr) {
                console.error(`FAIL: parse(${JSON.stringify(input)})`);
                console.error(`  got:      ${actualRepr}`);
                console.error(`  expected: ${expectedRepr}`);
                failed++;
            } else {
                passed++;
            }
        } catch (e) {
            console.error(
                `FAIL (error): parse(${JSON.stringify(input)}): ${e}`
            );
            failed++;
        }
    }

    if (failed > 0) {
        console.error(`FAILED - ${failed}/${cases.length} test cases failed`);
        process.exit(1);
    }

    console.log(`OK - all ${passed} test cases passed`);

    // Also parse the example file if available
    const exampleFile = new URL("lisp_parser.lsp", import.meta.url).pathname;
    try {
        const text = await Bun.file(exampleFile).text();
        const result = parse(text);
        console.log(
            `OK - parsed ${exampleFile} (${result.length} expressions)`
        );
        for (const expr of result) {
            console.log(`  ${repr(expr)}`);
        }
    } catch {
        // Example file not found, skip
    }
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
        const result = parse(text);
        for (const expr of result) {
            console.log(repr(expr));
        }
    } else {
        test();
    }
}
