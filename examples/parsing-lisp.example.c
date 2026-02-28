#include "parsing.h"
#include "testing.h"

static Grammar* createGrammar() {
	Grammar* g = Grammar_new();

	SYMBOL(WS,       TOKEN("\\s+"));
	SYMBOL(NUMBER,   TOKEN("-?\\d+(\\.\\d+)?"));
	SYMBOL(SYMBOL,   TOKEN("[a-zA-Z+\\-*/<>=?!][a-zA-Z0-9+\\-*/<>=?!]*"));
	SYMBOL(STRING,   TOKEN("\"[^\"]*\""));
	SYMBOL(LPAREN,   TOKEN("\\("));
	SYMBOL(RPAREN,   TOKEN("\\)"));
	SYMBOL(QUOTE,    TOKEN("[']"));

	SYMBOL(Atom,     GROUP(_S(NUMBER), _S(SYMBOL), _S(STRING)));

	SYMBOL(Quoted,   RULE(_S(QUOTE), _S(Atom)));

	SYMBOL(Program,  GROUP(_S(Atom), _S(Quoted)));
	g->axiom = s_Program;
	g->skip  = s_WS;

	return g;
}

static void printMatch(Match* m, int indent, ParsingContext* context) {
	for (int i = 0; i < indent; i++) printf("  ");
	if (!m || m->status == STATUS_FAILED) {
		printf("()\n");
		return;
	}
	Element* e = m->element;
	if (e && e->name) {
		printf("[%s] ", e->name);
	}
	printf("len=%zu ", m->length);
	if (m->length > 0 && context) {
		printf("'");
		for (size_t i = 0; i < m->length && m->offset + i < strlen(context->iterator->buffer); i++) {
			printf("%c", context->iterator->buffer[m->offset + i]);
		}
		printf("'");
	}
	printf("\n");
	if (m->children) {
		printMatch(m->children, indent + 1, context);
	}
	if (m->next) {
		printMatch(m->next, indent, context);
	}
}

static void parseFile(Grammar* g, const char* path) {
	printf("\n=== Parsing: %s ===\n", path);
	ParsingResult* result = Grammar_parsePath(g, path);
	if (ParsingResult_isSuccess(result)) {
		printf("SUCCESS: parsed %zu bytes\n", result->match->offset + result->match->length);
		printf("AST:\n");
		printMatch(result->match, 0, result->context);
	} else if (ParsingResult_isPartial(result)) {
		printf("PARTIAL: parsed %zu bytes, remaining %zd\n",
			result->match->offset + result->match->length, ParsingResult_remaining(result));
	} else {
		printf("FAILED\n");
	}
	ParsingResult_free(result);
}

int main(int argc, char** argv) {
	Grammar* g = createGrammar();
	Grammar_prepare(g);

	if (argc > 1) {
		for (int i = 1; i < argc; i++) {
			parseFile(g, argv[i]);
		}
	} else {
		printf("Usage: %s <lisp-file.lsp>...\n", argv[0]);
		printf("Example files: examples/parsing-lisp.example.lsp\n");
	}

	Grammar_free(g);
	TEST_SUCCEED;
}