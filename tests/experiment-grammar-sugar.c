#!/usr/bin/tcc -run -lpcre3
#include "src/parsing.h"

int main()
{
	SYMBOL(NUMBER,   TOKEN("\\d+"))
	SYMBOL(VAR,      TOKEN("\\w+"))
	SYMBOL(OPERATOR, TOKEN("[\\+\\-\\*\\/]"))

	SYMBOL(Value,  GROUP( _S(NUMBER),   _S(VAR)     ))
	SYMBOL(Suffix, RULE(  _S(OPERATOR), _S(Value)   ))
	SYMBOL(Expr,   RULE(  _S(Value),    _MO(Suffix) ))

	return 0;
}

// EOF
