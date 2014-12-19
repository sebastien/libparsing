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
		("Element*",             O),
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

	_IS  = None
	_NEW = None

	@classmethod
	def Is(cls, i ):
		if isinstance(i, cls):
			return True
		elif isinstance(i, CObject) and cls._IS and cls._IS(i._cobj):
			return True
		else:
			return False

	@classmethod
	def Wrap(cls, i):
		return cls(i)

	def __init__(self, o, wrap=True):
		self._cobj = o
		assert o

class Match(CObject):

	def walk( self, callback ):
		def c(m,s):
			m = Match(m)
			callback(m,s)
		c = ffi.callback("void(*)(void *, size_t)", c)
		return lib.Match__walk(self._cobj, c, 0)

class Reference(CObject):

	_IS  = lambda o: lib.Reference_Is(o)

	def _as( self, name ):
		lib.Reference_name(self._cobj, name)
		return self

class ParsingElement(CObject):

	_IS  = lambda o: lib.ParsingElement_Is(o)

	def add( self, *children ):
		for c in children:
			lib.ParsingElement_add(self._cobj, lib.Reference_Ensure(c._cobj))
		return self

	def _as( self, name ):
		lib.ParsingElement_name(self._cobj, name)
		return self

class Word(ParsingElement):

	def __init__( self, word, wrap=False):
		CObject.__init__(self, word if wrap else lib.Word_new(word))

class Token(ParsingElement):

	def __init__( self, token, wrap=False ):
		CObject.__init__(self, token if wrap else lib.Token_new(token))

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
		return Match(lib.Grammar_parseFromPath(self._cobj, path))

	def walk( self, callback ):
		def c(o,s):
			if    Reference.Is(o):
				o = Reference.Wrap(o)
			elif  ParsingElement.Is(o):
				# FIXME: Should return the proper references to the
				# wrapped objects
				o = ParsingElement.Wrap(o)
			else:
				o = Match.Wrap(o)
			callback(o, s)
		c = ffi.callback("void(*)(void *, size_t)", c)
		return lib.Element__walk(self._cobj.axiom, c, 0)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	g  = Grammar()
	a  = Word("a")._as("a")
	b  = Word("b")._as("b")
	ws = Token("\\s+")
	e  = Group(a, b)._as("e")
	g.axiom(e).skip(ws)
	match = g.parsePath("pouet.txt")
	def w(m, step):
		print "MATCH", step, m
	match.walk(w)

# EOF - vim: ts=4 sw=4 noet
