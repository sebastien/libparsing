#!/usr/bin/env python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cparse

path = sys.argv[1] if len(sys.argv) > 1 else "src/h/parsing.h"
clib = cparse.Library(path)

OPERATION_TYPES = ("type", "constructor", "operation", "method", "destructor")
# NOTE: We need to generate a little bit of preample before outputting
# the types.
cdef = (
	"typedef char* iterated_t;\n"
	"typedef struct Element        Element;\n"
	"typedef struct ParsingElement ParsingElement;\n"
	"typedef struct ParsingResult  ParsingResult;\n"
	"typedef struct ParsingStats   ParsingStats;\n"
	"typedef struct ParsingContext ParsingContext;\n"
	"typedef struct Match Match;\n"
	"typedef struct Grammar Grammar;\n"
	"typedef struct TokenMatchGroup TokenMatchGroup;\n"
) + clib.getCode(
	("ConditionCallback", None),
	("ProcedureCallback", None),
	("ContextCallback", None),
	("ElementWalkingCallback", None),
	("MatchWalkingCallback", None),
	("Element*", OPERATION_TYPES),
	("Reference*", OPERATION_TYPES),
	("Match*", OPERATION_TYPES),
	("Iterator*", OPERATION_TYPES),
	("ParsingContext*", OPERATION_TYPES),
	("ParsingElement*", OPERATION_TYPES),
	("ParsingResult*", OPERATION_TYPES),
	("ParsingStats*", OPERATION_TYPES),
	("Word*", OPERATION_TYPES),
	("Token", OPERATION_TYPES),
	("TokenMatch", OPERATION_TYPES),
	("Token_*", OPERATION_TYPES),
	("TokenMatch_*", OPERATION_TYPES),
	("Group*", OPERATION_TYPES),
	("Rule*", OPERATION_TYPES),
	("Procedure*", OPERATION_TYPES),
	("Condition*", OPERATION_TYPES),
	("Grammar*", OPERATION_TYPES),
)
cdef = "\n".join(_ for _ in cdef.split("\n") if _.strip())

print(cdef)

# EOF
