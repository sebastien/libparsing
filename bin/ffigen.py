#!/usr/bin/env python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cparse

path = sys.argv[1] if len(sys.argv) > 1 else "src/h/parsing.h"
clib = cparse.Library(path)

O    = ("type", "constructor", "operation", "method", "destructor")
# NOTE: We need to generate a little bit of preample before outputting
# the types.
cdef = (
	"typedef char* iterated_t;\n"
	"typedef void   Element;\n"
	"typedef struct ParsingElement ParsingElement;\n"
	"typedef struct ParsingResult  ParsingResult;\n"
	"typedef struct ParsingStats   ParsingStats;\n"
	"typedef struct ParsingContext ParsingContext;\n"
	"typedef struct Match Match;\n"
	"typedef struct Grammar Grammar;\n"
	"typedef struct TokenMatchGroup TokenMatchGroup;\n"
) + clib.getCode(
	("ConditionCallback",    None),
	("ProcedureCallback",    None),
	("ContextCallback",      None),
	("WalkingCallback",      None),
	("Element*",             O),
	("Reference*",           O),
	("Match*",               O),
	("Iterator*",            O),
	("ParsingContext*",      O),
	("ParsingElement*",      O),
	("ParsingResult*",       O),
	("ParsingStats*",        O),
	("Word*" ,               O),
	("Token",                O),
	("TokenMatch",           O),
	("Token_*",              O),
	("TokenMatch_*",         O),
	("Group*",               O),
	("Rule*",                O),
	("Procedure*",           O),
	("Condition*",           O),
	("Grammar*",             O),
)
cdef = "\n".join(_ for _ in cdef.split("\n") if _.strip())

print (cdef)

# EOF
