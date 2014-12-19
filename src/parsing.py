#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2014-Dec-18
# Last modification : 2014-Dec-18
# -----------------------------------------------------------------------------

from cffi import FFI
import re, os
import cdoclib

VERSION  = "0.0.0"
LICENSE  = "http://ffctn.com/doc/licenses/bsd"
FFI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parsing.ffi")
H_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parsing.h")

# Creates the .ffi file from the header or loads it directly from the
# previously generated one.
if os.path.exists(H_PATH):
	clib = cdoclib.Library(H_PATH)
	O    = ("type", "constructor", "operation", "method", "destructor")
	# NOTE: We need to generate a little bit of preample before outputting
	# the types.
	cdef = (
		"typedef char* iterated_t;\n"
		"typedef struct ParsingElement ParsingElement;\n"
		"typedef struct ParsingElement ParsingElement;\n"
		"typedef struct ParsingContext ParsingContext;\n"
		"typedef struct Match Match;\n"
	) + clib.getCode(
		("ConditionCallback",    None),
		("ProcedureCallback",    None),
		("Reference*",           O),
		("Match*",               O),
		("Iterator*",            O),
		("ParsingContext*",      O),
		("ParsingElement*",      O),
		("Word*" ,               O),
		("Token",                O),
		("Token_*",              O),
		("Group*",               O),
		("Rule*",                O),
		("Procedure*",           O),
		("Condition*",           O),
		("Grammar*",             O),
	)
	with file(FFI_PATH, "w") as f:
		f.write(cdef)
else:
	with file(FFI_PATH, "r") as f:
		cdef = f.read()

ffi = FFI()
ffi.cdef(cdef)
lib = ffi.dlopen("libparsing.so.0.1.2")

g   = lib.Grammar_new()
a   = lib.ParsingElement_name(lib.Word_new ("a"), ("a"))
b   = lib.ParsingElement_name(lib.Word_new ("b"), ("b"))
ws  = lib.Token_new("\\s+")
e   = lib.ParsingElement_name(lib.Group_new(ffi.NULL), "e")

lib.ParsingElement_add(e, lib.Reference_Ensure(a))
lib.ParsingElement_add(e, lib.Reference_Ensure(b))

g.axiom = e
g.skip  = ws
lib.Grammar_parseFromPath(g, "pouet.txt")

import ipdb
ipdb.set_trace()


# EOF - vim: ts=4 sw=4 noet
