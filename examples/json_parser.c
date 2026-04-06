/**
 * Simple JSON Parser (C / libparsing)
 * ====================================
 *
 * A pure-C JSON parser using the libparsing PEG library, equivalent to
 * examples/json_parser.py. Parses JSON text and reconstructs it to stdout
 * (verifying the parse tree is correct).
 *
 * Usage:
 *   json_parser <file.json>            Parse and print reconstructed JSON
 *   json_parser --benchmark N <file>   Parse N times, report timing only
 *   json_parser --test                 Run built-in self-test
 */
#include "parsing.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* -------------------------------------------------------------------------
 * Grammar Definition
 * ---------------------------------------------------------------------- */

static Grammar* createGrammar() {
	Grammar* g = Grammar_new();
	Grammar_setNoMemo(g);  // JSON grammar doesn't benefit from memoization
	g->skipWhitespace = TRUE; // Use fast hand-coded whitespace skip

	/* Tokens */
	SYMBOL(WS,      TOKEN("\\s+"));
	SYMBOL(NUMBER,  TOKEN("[+\\-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+\\-]?\\d+)?"));
	Token_setCustomRecognize(s_NUMBER, Token_recognizeJSONNumber);
	SYMBOL(STRING,  TOKEN("\"([^\"\\\\]|\\\\.)*\""));
	Token_setCustomRecognize(s_STRING, Token_recognizeJSONString);
	SYMBOL(TRUE,    TOKEN("true"));
	SYMBOL(FALSE,   TOKEN("false"));
	SYMBOL(NULL,    TOKEN("null"));

	/* Words (literal delimiters) */
	SYMBOL(LBRACE,   WORD("{"));
	SYMBOL(RBRACE,   WORD("}"));
	SYMBOL(LBRACKET, WORD("["));
	SYMBOL(RBRACKET, WORD("]"));
	SYMBOL(COMMA,    WORD(","));
	SYMBOL(COLON,    WORD(":"));

	/* Forward-declare Value for recursion (empty group, filled later) */
	ParsingElement* s_Value = ParsingElement_name(Group_new((Reference*[1]){NULL}), "Value");

	/* Object: { pair (, pair)* } */
	SYMBOL(Pair,        RULE(_S(STRING), _S(COLON), _S(Value)));
	SYMBOL(PairSuffix,  RULE(_S(COMMA), _S(Pair)));
	SYMBOL(Object,      RULE(_S(LBRACE), _O(Pair), _MO(PairSuffix), _S(RBRACE)));

	/* Array: [ value (, value)* ] */
	SYMBOL(ValueSuffix, RULE(_S(COMMA), _S(Value)));
	SYMBOL(Array,       RULE(_S(LBRACKET), _O(Value), _MO(ValueSuffix), _S(RBRACKET)));

	/* Fill in Value alternatives */
	ParsingElement_add(s_Value, Reference_Ensure(s_Object));
	ParsingElement_add(s_Value, Reference_Ensure(s_Array));
	ParsingElement_add(s_Value, Reference_Ensure(s_STRING));
	ParsingElement_add(s_Value, Reference_Ensure(s_NUMBER));
	ParsingElement_add(s_Value, Reference_Ensure(s_TRUE));
	ParsingElement_add(s_Value, Reference_Ensure(s_FALSE));
	ParsingElement_add(s_Value, Reference_Ensure(s_NULL));

	g->axiom = s_Value;
	g->skip  = s_WS;

	return g;
}

/* -------------------------------------------------------------------------
 * Match Tree Walker - Reconstructs JSON output
 *
 * Walks the libparsing match tree and writes reconstructed JSON to `out`.
 * If `out` is NULL, the walk is performed (to be fair for benchmarking)
 * but no output is produced.
 * ---------------------------------------------------------------------- */

/** Write a string to `out`, or do nothing if out is NULL. */
static inline void emit(FILE* out, const char* s) {
	if (out) fputs(s, out);
}

/** Write N chars to `out`, or do nothing if out is NULL. */
static inline void emitn(FILE* out, const char* s, size_t n) {
	if (out) fwrite(s, 1, n, out);
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
 * Walk a match node and emit reconstructed JSON.
 * Dispatches based on the element name.
 */
static void walk(Match* m, FILE* out, const char* input) {
	if (m == NULL || m->status != STATUS_MATCHED) return;
	m = unwrap(m);
	if (m == NULL) return;

	const char* name = Match_getElementName(m);
	char etype = Match_getElementType(m);

	/* Tokens: STRING, NUMBER, TRUE, FALSE, NULL */
	if (etype == TYPE_TOKEN) {
		if (name == NULL) return;
		if (strcmp(name, "STRING") == 0) {
			/* Output the raw matched string (already includes quotes) */
			const char* val = TokenMatch_group(m, 0);
			if (val) emit(out, val);
		} else if (strcmp(name, "NUMBER") == 0) {
			const char* val = TokenMatch_group(m, 0);
			if (val) emit(out, val);
		} else if (strcmp(name, "TRUE") == 0) {
			emit(out, "true");
		} else if (strcmp(name, "FALSE") == 0) {
			emit(out, "false");
		} else if (strcmp(name, "NULL") == 0) {
			emit(out, "null");
		}
		return;
	}

	/* Words: skip (they are structural delimiters handled by rules) */
	if (etype == TYPE_WORD) return;

	/* Group: Value - just walk the matched child */
	if (etype == TYPE_GROUP) {
		if (m->children) {
			walk(m->children, out, input);
		}
		return;
	}

	/* Rules: Object, Array, Pair, PairSuffix, ValueSuffix */
	if (etype == TYPE_RULE && name != NULL) {
		if (strcmp(name, "Pair") == 0) {
			/* Children: STRING, COLON, Value */
			Match* child = m->children;
			Match* key = unwrap(child);
			walk(key, out, input);
			emit(out, ": ");
			/* Skip COLON ref */
			child = child->next;
			if (child) child = child->next;
			Match* val = unwrap(child);
			walk(val, out, input);
			return;
		}

		if (strcmp(name, "PairSuffix") == 0) {
			/* Children: COMMA, Pair */
			Match* child = m->children;
			if (child) child = child->next; /* skip COMMA ref */
			Match* pair = unwrap(child);
			walk(pair, out, input);
			return;
		}

		if (strcmp(name, "ValueSuffix") == 0) {
			/* Children: COMMA, Value */
			Match* child = m->children;
			if (child) child = child->next; /* skip COMMA ref */
			Match* val = unwrap(child);
			walk(val, out, input);
			return;
		}

		if (strcmp(name, "Object") == 0) {
			/* Children: LBRACE, Pair?, PairSuffix*, RBRACE */
			emit(out, "{");
			Match* child = m->children;
			/* Skip LBRACE ref */
			if (child) child = child->next;
			/* Pair? (optional) */
			Match* first_pair_ref = child;
			if (child) child = child->next;
			/* PairSuffix* (many_optional) */
			Match* rest_ref = child;
			if (child) child = child->next;
			/* RBRACE - skip */

			Match* fp = unwrap(first_pair_ref);
			int has_first = (fp && fp->status == STATUS_MATCHED &&
			                 fp->element && Match_getElementType(fp) == TYPE_RULE);

			if (has_first) {
				walk(fp, out, input);
				/* Walk PairSuffix* list */
				if (rest_ref && rest_ref->children) {
					Match* ps = rest_ref->children;
					while (ps) {
						emit(out, ", ");
						Match* inner = unwrap(ps);
						walk(inner, out, input);
						ps = ps->next;
					}
				}
			}
			emit(out, "}");
			return;
		}

		if (strcmp(name, "Array") == 0) {
			/* Children: LBRACKET, Value?, ValueSuffix*, RBRACKET */
			emit(out, "[");
			Match* child = m->children;
			/* Skip LBRACKET ref */
			if (child) child = child->next;
			/* Value? (optional) */
			Match* first_val_ref = child;
			if (child) child = child->next;
			/* ValueSuffix* (many_optional) */
			Match* rest_ref = child;
			if (child) child = child->next;
			/* RBRACKET - skip */

			Match* fv = unwrap(first_val_ref);
			int has_first = (fv && fv->status == STATUS_MATCHED && fv->element);
			/* Check it's not an empty optional */
			char fv_etype = Match_getElementType(fv);
			if (has_first && (fv_etype == TYPE_GROUP || fv_etype == TYPE_RULE ||
			                  fv_etype == TYPE_TOKEN || fv_etype == TYPE_WORD)) {
				walk(fv, out, input);
				/* Walk ValueSuffix* list */
				if (rest_ref && rest_ref->children) {
					Match* vs = rest_ref->children;
					while (vs) {
						emit(out, ", ");
						Match* inner = unwrap(vs);
						walk(inner, out, input);
						vs = vs->next;
					}
				}
			}
			emit(out, "]");
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

/** Read all of stdin into a malloc'd string. */
static char* readStdin(void) {
	size_t capacity = 4096;
	size_t length = 0;
	char* buf = (char*)malloc(capacity);
	if (!buf) return NULL;
	while (1) {
		size_t nread = fread(buf + length, 1, capacity - length, stdin);
		length += nread;
		if (nread == 0) break;
		if (length == capacity) {
			capacity *= 2;
			buf = (char*)realloc(buf, capacity);
			if (!buf) return NULL;
		}
	}
	buf[length] = '\0';
	return buf;
}

/* -------------------------------------------------------------------------
 * High-precision timer
 * ---------------------------------------------------------------------- */

static double now(void) {
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

/* -------------------------------------------------------------------------
 * Self-test
 * ---------------------------------------------------------------------- */

static const char* TEST_JSON =
	"{\n"
	"    \"empty_object\" : {},\n"
	"    \"empty_array\"  : [],\n"
	"    \"booleans\"     : { \"YES\" : true, \"NO\" : false },\n"
	"    \"numbers\"      : [ 0, 1, -2, 3.3, 4.4e5, 6.6e-7 ],\n"
	"    \"strings\"      : [ \"This\", [ \"And\" , \"That\", \"And a \\\\\\\"b\" ] ],\n"
	"    \"nothing\"      : null\n"
	"}";

static int runTest(Grammar* g) {
	ParsingResult* result = Grammar_parseString(g, TEST_JSON);
	if (ParsingResult_isFailure(result)) {
		fprintf(stderr, "FAILED: could not parse test JSON\n");
		ParsingResult_free(result);
		return 1;
	}
	printf("OK - parsed test JSON successfully\n");
	walk(result->match, stdout, TEST_JSON);
	printf("\n");
	ParsingResult_free(result);
	return 0;
}

/* -------------------------------------------------------------------------
 * Main
 * ---------------------------------------------------------------------- */

int main(int argc, char** argv) {
	Grammar* g = createGrammar();
	Grammar_prepare(g);

	if (argc < 2) {
		fprintf(stderr,
			"Usage: %s <file.json>              Parse and print JSON\n"
			"       %s --benchmark N <file>      Parse N times, report timing\n"
			"       %s --benchmark N -           Read from stdin\n"
			"       %s --test                    Run self-test\n",
			argv[0], argv[0], argv[0], argv[0]);
		Grammar_free(g);
		return 1;
	}

	/* --test */
	if (strcmp(argv[1], "--test") == 0) {
		int rc = runTest(g);
		Grammar_free(g);
		return rc;
	}

	/* --benchmark N <file|-|string> */
	if (strcmp(argv[1], "--benchmark") == 0) {
		if (argc < 4) {
			fprintf(stderr, "Usage: %s --benchmark N <file|->\n", argv[0]);
			Grammar_free(g);
			return 1;
		}
		int iterations = atoi(argv[2]);
		if (iterations < 1) iterations = 1;

		char* input = NULL;
		if (strcmp(argv[3], "-") == 0) {
			input = readStdin();
		} else {
			input = readFile(argv[3]);
		}
		if (!input) {
			fprintf(stderr, "ERROR: could not read input\n");
			Grammar_free(g);
			return 1;
		}

		size_t input_len = strlen(input);

		/* Warm-up parse */
		ParsingResult* warmup = Grammar_parseString(g, input);
		if (ParsingResult_isFailure(warmup)) {
			fprintf(stderr, "FAILED: could not parse input (%zu bytes)\n", input_len);
			ParsingResult_free(warmup);
			free(input);
			Grammar_free(g);
			return 1;
		}
		/* Verify by walking (no output) */
		walk(warmup->match, NULL, input);
		ParsingResult_free(warmup);

		/* Timed iterations */
		double total_time = 0.0;
		for (int i = 0; i < iterations; i++) {
			double t0 = now();
			ParsingResult* r = Grammar_parseString(g, input);
			walk(r->match, NULL, input);
			double t1 = now();
			total_time += (t1 - t0);
			ParsingResult_free(r);
		}

		double avg = total_time / iterations;
		/* Output machine-readable timing: avg_seconds total_seconds iterations bytes */
		printf("%.9f %.9f %d %zu\n", avg, total_time, iterations, input_len);

		free(input);
		Grammar_free(g);
		return 0;
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
