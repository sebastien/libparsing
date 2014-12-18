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


clib = cdoclib.Library("src/parsing.h")
cdef = "typedef char* iterated_t;typedef struct ParsingElement Parsing;\n" + clib.getCode(
	("Reference",      "type"),
	("Match",          "type"),
	("Iterator",       "type"),
	("ParsingContext", "type"),
	("ParsingElement", "type"),
	("Grammar",        "type"),
)
#cdef = file("src/parsing.ffi").read()
file("src/parsing.ffi", "w").write(cdef)


ffi     = FFI()
ffi.cdef(cdef)

# EOF - vim: ts=4 sw=4 noet
