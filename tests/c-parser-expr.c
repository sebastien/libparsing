#include "parsing.h"
#include "testing.h"

/**
 * This test case exercises the following:
 *
 * - No argument: proper deallocation of a grammar on `Grammar_free`
 * - With argument: proper deallocation of matches, result and context
*/
Grammar* createGrammar() {
	Grammar* g = Grammar_new();
	// Grammar_setVerbose(g);

	SYMBOL (WS,             TOKEN("\\s+"));
	SYMBOL (NUMBER,         TOKEN("\\d+(\\.\\d+)?"));
	SYMBOL (VARIABLE,       TOKEN("\\w+"));
	SYMBOL (OPERATOR,       TOKEN("[\\+\\-\\*/]"));

	SYMBOL (Value,         GROUP( _S(NUMBER), _S(VARIABLE)));
	SYMBOL (Suffix,        RULE (_AS(_S(OPERATOR), "operator"), _AS(_S(Value), "value")));
	SYMBOL (Expression,    RULE (_S(Value), MANY_OPTIONAL(_S(Suffix))));

	AXIOM(Expression);
	SKIP(WS);

	return g;
}

int main (int argc, char** argv) {
	// We define the grammar
	Grammar* g = createGrammar();

	for (int i=1 ; i < argc ; i++) {
		ParsingResult* result = Grammar_parsePath(g, argv[i]);
		if (ParsingResult_isSuccess(result)) {
			printf("Successful parsing of '%s', parsed %d, remaining %zd\n", argv[i], ParsingResult_textOffset(result), ParsingResult_remaining(result));
		} else if (ParsingResult_isPartial(result)) {
			printf("Partial parsing of '%s', parsed %d, remaining %zd\n", argv[i], ParsingResult_textOffset(result), ParsingResult_remaining(result));
		} else {
			printf("Failed parsing of '%s'\n", argv[i]);
		}
		ParsingResult_free(result);
	}

	Grammar_free(g);
	TEST_SUCCEED;
}

