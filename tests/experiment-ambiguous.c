#include "parsing.h"

void main () {
	Grammar g;
	SYMBOL(x, WORD("x"));
	SYMBOL(S, NULL)
	ParsingElement_add(s_S, GROUP(
		SINGLE(RULE( _S(x), _S(S), _S(x))),
		_S(x)
	));
}
