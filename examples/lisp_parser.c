/**
 * Simple Lisp Parser (C / libparsing)
 * ====================================
 *
 * A pure-C Lisp (S-expression) parser using the libparsing PEG library,
 * equivalent to examples/lisp_parser.py. Parses Lisp source code and
 * reconstructs formatted S-expressions to stdout (verifying the parse tree
 * is correct).
 *
 * Features:
 *   - Numbers (integers and floats, with optional sign)
 *   - Symbols (identifiers and operators like +, -, <=, string->number)
 *   - Strings (double-quoted with escape sequences)
 *   - Comments (; to end of line, automatically skipped)
 *   - Quote shorthand ('x emitted as (quote x))
 *   - Proper lists: (a b c)
 *   - Dotted pairs: (a . b), (a b . c)
 *
 * Usage:
 *   lisp_parser <file.lsp>            Parse and print reconstructed Lisp
 *   lisp_parser --test                Run built-in self-test
 */
#include "parsing.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -------------------------------------------------------------------------
 * Grammar Definition
 * ---------------------------------------------------------------------- */

static Grammar* createGrammar() {
	Grammar* g = Grammar_new();

	/* Tokens - WS includes line comments */
	SYMBOL(WS,      TOKEN("(\\s|;[^\\n]*)+"));
	SYMBOL(NUMBER,  TOKEN("[+\\-]?\\d+(\\.\\d+)?"));
	SYMBOL(STRING,  TOKEN("\"([^\"\\\\]|\\\\.)*\""));
	SYMBOL(SYMBOL,  TOKEN("[a-zA-Z!$%&*+\\-/:<=>?~_^][a-zA-Z0-9!$%&*+\\-/:<=>?~_^.]*|\\.\\.\\."));

	/* Words (literal delimiters) */
	SYMBOL(QUOTE,   WORD("'"));
	SYMBOL(DOT,     WORD("."));
	SYMBOL(LP,      WORD("("));
	SYMBOL(RP,      WORD(")"));

	/* Composite elements */
	SYMBOL(Atom,    GROUP(_S(NUMBER), _S(SYMBOL), _S(STRING)));

	/* Forward-declare Expr for recursion (empty group, filled later) */
	ParsingElement* s_Expr = ParsingElement_name(
		Group_new((Reference*[1]){NULL}), "Expr");

	SYMBOL(Quoted,     RULE(_S(QUOTE), _S(Expr)));
	SYMBOL(DottedTail, RULE(_S(DOT), _S(Expr)));
	SYMBOL(List,       RULE(_S(LP), _MO(Expr), _O(DottedTail), _S(RP)));

	/* Fill in Expr alternatives */
	ParsingElement_add(s_Expr, Reference_Ensure(s_Quoted));
	ParsingElement_add(s_Expr, Reference_Ensure(s_List));
	ParsingElement_add(s_Expr, Reference_Ensure(s_Atom));

	SYMBOL(Program, RULE(_MO(Expr)));

	g->axiom = s_Program;
	g->skip  = s_WS;

	return g;
}

/* -------------------------------------------------------------------------
 * Match Tree Walker - Reconstructs Lisp S-expressions
 *
 * Walks the libparsing match tree and writes reconstructed Lisp to `out`.
 * Quote shorthand 'x is emitted as (quote x).
 * ---------------------------------------------------------------------- */

/** Write a string to `out`, or do nothing if out is NULL. */
static inline void emit(FILE* out, const char* s) {
	if (out) fputs(s, out);
}

/**
 * Skip past Reference wrappers to get the actual match content.
 * References with ONE/OPTIONAL cardinality just wrap a single child.
 */
static Match* unwrap(Match* m) {
	if (m == NULL) return NULL;
	while (m->element && m->element->type == TYPE_REFERENCE) {
		Reference* ref = (Reference*)m->element;
		if (ref->cardinality == CARDINALITY_ONE ||
		    ref->cardinality == CARDINALITY_OPTIONAL ||
		    ref->cardinality == CARDINALITY_NOT_EMPTY) {
			if (m->children) {
				m = m->children;
			} else {
				return m;
			}
		} else {
			/* MANY / MANY_OPTIONAL - don't unwrap */
			return m;
		}
	}
	return m;
}

/**
 * Walk a match node and emit reconstructed Lisp.
 * Dispatches based on the element name.
 */
static void walk(Match* m, FILE* out, const char* input) {
	if (m == NULL || m->status != STATUS_MATCHED) return;
	m = unwrap(m);
	if (m == NULL) return;

	const char* name = Match_getElementName(m);
	char etype = Match_getElementType(m);

	/* Tokens: NUMBER, SYMBOL, STRING */
	if (etype == TYPE_TOKEN) {
		if (name == NULL) return;
		const char* val = TokenMatch_group(m, 0);
		if (val) emit(out, val);
		return;
	}

	/* Words: skip (they are structural delimiters handled by rules) */
	if (etype == TYPE_WORD) return;

	/* Groups: Atom, Expr - walk the matched child */
	if (etype == TYPE_GROUP) {
		if (m->children) {
			walk(m->children, out, input);
		}
		return;
	}

	/* Rules: Quoted, DottedTail, List, Program */
	if (etype == TYPE_RULE && name != NULL) {
		if (strcmp(name, "Quoted") == 0) {
			/* Children: QUOTE, Expr -> emit (quote <expr>) */
			emit(out, "(quote ");
			Match* child = m->children;
			if (child) child = child->next; /* skip QUOTE ref */
			walk(unwrap(child), out, input);
			emit(out, ")");
			return;
		}

		if (strcmp(name, "DottedTail") == 0) {
			/* Children: DOT, Expr -> emit . <expr> */
			emit(out, " . ");
			Match* child = m->children;
			if (child) child = child->next; /* skip DOT ref */
			walk(unwrap(child), out, input);
			return;
		}

		if (strcmp(name, "List") == 0) {
			/* Children: LP, Expr*, DottedTail?, RP */
			emit(out, "(");
			Match* child = m->children;
			if (child) child = child->next; /* skip LP ref */

			/* Expr* (zeroOrMore) */
			Match* items_ref = child;
			if (child) child = child->next;
			/* DottedTail? (optional) */
			Match* dotted_ref = child;
			if (child) child = child->next;
			/* RP - skip */

			/* Walk items */
			int first = 1;
			if (items_ref && items_ref->children) {
				Match* item = items_ref->children;
				while (item) {
					if (!first) emit(out, " ");
					walk(unwrap(item), out, input);
					first = 0;
					item = item->next;
				}
			}

			/* Walk dotted tail */
			Match* dt = unwrap(dotted_ref);
			if (dt && dt->status == STATUS_MATCHED &&
			    dt->element && Match_getElementType(dt) == TYPE_RULE) {
				walk(dt, out, input);
			}

			emit(out, ")");
			return;
		}

		if (strcmp(name, "Program") == 0) {
			/* Single child: Expr* (zeroOrMore) */
			Match* exprs_ref = m->children;
			int first = 1;
			if (exprs_ref && exprs_ref->children) {
				Match* expr = exprs_ref->children;
				while (expr) {
					if (!first) emit(out, "\n");
					walk(unwrap(expr), out, input);
					first = 0;
					expr = expr->next;
				}
			}
			return;
		}
	}

	/* Default: walk children */
	Match* child = m->children;
	while (child) {
		walk(child, out, input);
		child = child->next;
	}
}

/* -------------------------------------------------------------------------
 * Input Helpers
 * ---------------------------------------------------------------------- */

/** Read entire file into a malloc'd string. Returns NULL on failure. */
static char* readFile(const char* path) {
	FILE* f = fopen(path, "rb");
	if (!f) return NULL;
	fseek(f, 0, SEEK_END);
	long size = ftell(f);
	fseek(f, 0, SEEK_SET);
	char* buf = (char*)malloc((size_t)size + 1);
	if (!buf) { fclose(f); return NULL; }
	size_t nread = fread(buf, 1, (size_t)size, f);
	buf[nread] = '\0';
	fclose(f);
	return buf;
}

/* -------------------------------------------------------------------------
 * Self-test
 * ---------------------------------------------------------------------- */

/**
 * Walk a match tree into a malloc'd string using open_memstream.
 * Caller must free() the returned string.
 */
static char* walkToString(Match* match, const char* input) {
	char* buf = NULL;
	size_t buf_len = 0;
	FILE* mem = open_memstream(&buf, &buf_len);
	if (!mem) return NULL;
	walk(match, mem, input);
	fclose(mem);
	return buf;
}

static int runTest(Grammar* g) {
	typedef struct { const char* input; const char* expected; } TestCase;
	TestCase cases[] = {
		/* Atoms */
		{"42",                 "42"},
		{"-17",                "-17"},
		{"3.14",               "3.14"},
		{"\"hello\"",          "\"hello\""},
		{"foo",                "foo"},
		{"+",                  "+"},
		{"-",                  "-"},
		{"<=",                 "<="},
		{"string->number",     "string->number"},
		{"...",                "..."},
		/* Simple lists */
		{"(+ 1 2)",            "(+ 1 2)"},
		{"()",                 "()"},
		{"(define x 42)",      "(define x 42)"},
		/* Nested */
		{"(define (square x) (* x x))", "(define (square x) (* x x))"},
		/* Quote */
		{"'x",                 "(quote x)"},
		{"'(1 2 3)",           "(quote (1 2 3))"},
		/* Dotted pairs */
		{"(1 . 2)",            "(1 . 2)"},
		{"(a b . c)",          "(a b . c)"},
		/* Multiple top-level */
		{"1 2 3",              "1\n2\n3"},
		/* Comments */
		{"; comment\n42",      "42"},
		{"; line 1\n; line 2\n(+ 1 2)", "(+ 1 2)"},
	};

	int n = sizeof(cases) / sizeof(cases[0]);
	int passed = 0;
	int failed = 0;

	for (int i = 0; i < n; i++) {
		ParsingResult* result = Grammar_parseString(g, cases[i].input);
		if (ParsingResult_isFailure(result)) {
			fprintf(stderr, "FAIL (parse): %s\n", cases[i].input);
			ParsingResult_free(result);
			failed++;
			continue;
		}

		char* actual = walkToString(result->match, cases[i].input);
		ParsingResult_free(result);

		if (actual == NULL) {
			fprintf(stderr, "FAIL (walk): %s\n", cases[i].input);
			failed++;
			continue;
		}

		if (strcmp(actual, cases[i].expected) != 0) {
			fprintf(stderr, "FAIL: parse(\"%s\")\n  got:      \"%s\"\n  expected: \"%s\"\n",
				cases[i].input, actual, cases[i].expected);
			free(actual);
			failed++;
			continue;
		}

		free(actual);
		passed++;
	}

	if (failed == 0) {
		printf("OK - all %d test cases passed\n", passed);
	} else {
		printf("FAILED - %d/%d test cases failed\n", failed, n);
	}

	return failed > 0 ? 1 : 0;
}

/* -------------------------------------------------------------------------
 * Main
 * ---------------------------------------------------------------------- */

int main(int argc, char** argv) {
	Grammar* g = createGrammar();
	Grammar_prepare(g);

	if (argc < 2) {
		fprintf(stderr,
			"Usage: %s <file.lsp>       Parse and print reconstructed Lisp\n"
			"       %s --test           Run self-test\n",
			argv[0], argv[0]);
		Grammar_free(g);
		return 1;
	}

	/* --test */
	if (strcmp(argv[1], "--test") == 0) {
		int rc = runTest(g);
		Grammar_free(g);
		return rc;
	}

	/* Default: parse file and print */
	char* input = readFile(argv[1]);
	if (!input) {
		fprintf(stderr, "ERROR: could not read '%s'\n", argv[1]);
		Grammar_free(g);
		return 1;
	}

	ParsingResult* result = Grammar_parseString(g, input);
	if (ParsingResult_isFailure(result)) {
		fprintf(stderr, "FAILED: could not parse '%s'\n", argv[1]);
		ParsingResult_free(result);
		free(input);
		Grammar_free(g);
		return 1;
	}

	walk(result->match, stdout, input);
	printf("\n");

	ParsingResult_free(result);
	free(input);
	Grammar_free(g);
	return 0;
}

/* EOF */
