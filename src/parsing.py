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

# -----------------------------------------------------------------------------
#
# FFI
#
# -----------------------------------------------------------------------------

# Creates the .ffi file from the header or loads it directly from the
# previously generated one.
if os.path.exists(H_PATH):
	clib = cdoclib.Library(H_PATH)
	O    = ("type", "constructor", "operation", "method", "destructor")
	# NOTE: We need to generate a little bit of preample before outputting
	# the types.
	cdef = (
		"typedef char* iterated_t;\n"
		"typedef void Element;\n"
		"typedef struct ParsingElement ParsingElement;\n"
		"typedef struct ParsingElement ParsingElement;\n"
		"typedef struct ParsingContext ParsingContext;\n"
		"typedef struct Match Match;\n"
	) + clib.getCode(
		("ConditionCallback",    None),
		("ProcedureCallback",    None),
		("WalkingCallback",      None),
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
lib = ffi.dlopen("libparsing.so.0.2.0")

# -----------------------------------------------------------------------------
#
# C OJBECT ABSTRACTION
#
# -----------------------------------------------------------------------------

class CObject(object):

	def __init__(self, o):
		self._cobj = o
		assert o

class ParsingElement(CObject):

	def add( self, *children ):
		for c in children:
			lib.ParsingElement_add(self._cobj, lib.Reference_Ensure(c._cobj))
		return self

	def _as( self, name ):
		lib.ParsingElement_name(self._cobj, name)
		return self

class Word(ParsingElement):

	def __init__( self, word ):
		CObject.__init__(self, lib.Word_new(word))

class Token(ParsingElement):

	def __init__( self, token ):
		CObject.__init__(self, lib.Token_new(token))

class Group(ParsingElement):

	def __init__( self, *children ):
		CObject.__init__(self, lib.Group_new(ffi.NULL))
		self.add(*children)

class Rule(ParsingElement):

	def __init__( self, *children ):
		CObject.__init__(self, lib.Rule_new(ffi.NULL))
		self.add(*children)

class Grammar(CObject):

	def __init__(self):
		CObject.__init__(self, lib.Grammar_new())

	def prepare( self ):
		lib.Grammar_prepare(self._cobj)
		return self

	def axiom( self, axiom ):
		assert isinstance(axiom, ParsingElement)
		self._cobj.axiom = axiom._cobj
		return self.prepare()

	def skip( self, skip ):
		assert isinstance(skip, ParsingElement)
		self._cobj.skip = skip._cobj
		return self

	def parsePath( self, path ):
		return lib.Grammar_parseFromPath(self._cobj, path )

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if False:
	g   = lib.Grammar_new()
	a   = lib.ParsingElement_name(lib.Word_new ("a"), ("a"))
	b   = lib.ParsingElement_name(lib.Word_new ("b"), ("b"))
	ws  = lib.Token_new("\\s+")
	e   = lib.ParsingElement_name(lib.Group_new(ffi.NULL), "e")
	g.axiom = e
	g.skip  = ws

	lib.ParsingElement_add(e, lib.Reference_Ensure(a))
	lib.ParsingElement_add(e, lib.Reference_Ensure(b))
	lib.Grammar_parseFromPath(g, "pouet.txt")
else:
	g  = Grammar()
	a  = Word("a")._as("a")
	b  = Word("b")._as("b")
	ws = Token("\\s+")
	e  = Group(a, b)._as("e")
	g.axiom(e).skip(ws)
	match = g.parsePath("pouet.txt")

# EOF - vim: ts=4 sw=4 noet
