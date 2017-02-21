#include "parsing.h"
#include "testing.h"

#define TEST_A = "a";

/**
 * This test case exercises the following:
 *
 * - No argument: proper deallocation of a grammar on `Grammar_free`
 * - With argument: proper deallocation of matches, result and context
 *
 * Run this with `valgrind --leak-check=full`
*/
Grammar* createGrammar(char* type) {
	Grammar* g = Grammar_new();
	Grammar_setVerbose(g);

	if ( strcmp(type, "word") == 0 ) {
		SYMBOL (WORD_A, WORD("a"));
		AXIOM(WORD_A);
	} else if (strcmp(type, "token") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		AXIOM(TOKEN_A);

	} else if (strcmp(type, "rule") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (RULE_A, RULE(_S(TOKEN_A)));
		AXIOM(RULE_A);
	} else if (strcmp(type, "rule01") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (RULE_A, RULE(OPTIONAL(_S(TOKEN_A))));
		AXIOM(RULE_A);
	} else if (strcmp(type, "rule0N") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (RULE_A, RULE(MANY_OPTIONAL(_S(TOKEN_A))));
		AXIOM(RULE_A);
	} else if (strcmp(type, "rule1N") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (RULE_A, RULE(MANY(_S(TOKEN_A))));
		AXIOM(RULE_A);

	} else if (strcmp(type, "group") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (GROUP_A, GROUP(_S(TOKEN_A)));
		AXIOM(GROUP_A);
	} else if (strcmp(type, "group01") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (GROUP_A, GROUP(OPTIONAL(_S(TOKEN_A))));
		AXIOM(GROUP_A);
	} else if (strcmp(type, "group0N") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (GROUP_A, GROUP(MANY_OPTIONAL(_S(TOKEN_A))));
		AXIOM(GROUP_A);
	} else if (strcmp(type, "group1N") == 0) {
		SYMBOL (TOKEN_A, TOKEN("a"));
		SYMBOL (GROUP_A, GROUP(MANY(_S(TOKEN_A))));
		AXIOM(GROUP_A);
	} else {
		Grammar_free(g);
		g = NULL;
	}

	return g;
}

const char* getText( char* type ) {
	if (
		strcmp(type, "word")  == 0 ||
		strcmp(type, "token") == 0 ||
		strcmp(type, "rule")  == 0 ||
		strcmp(type, "group") == 0
	) {
		return "a";
	} else {
		return "aaa";
	}
}

int main (int argc, char** argv) {
	const char* all[] = {
		"word", "token", "rule", "group",
		"rule01",  "rule0N",  "rule1N",
		"group01", "group0N", "group1N"
	};
	for (int i=1 ; i<argc ; i++) {
		char* type = argv[i];
		Grammar* g    = createGrammar(type);
		const char* s = getText(type);
		printf("Parsing type '%s':'%s'\n", type, type);
		if (g != NULL ) {
			// ParsingResult* r = Grammar_parseString(g, s);
			// TEST_TRUE( ParsingResult_isSuccess(r) );
			// ParsingResult_free(r);
			Grammar_free(g);
		} else {
			printf("[!] Unknown type: %s\n", s);
		}
	}
	TEST_SUCCEED;
}

