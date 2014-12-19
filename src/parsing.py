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

CARDINALITY_OPTIONAL      = '?'
CARDINALITY_ONE           = '1'
CARDINALITY_MANY_OPTIONAL = '*'
CARDINALITY_MANY          = '+'

class CObject(object):

	_IS   = None
	_NEW  = None
	_TYPE = None

	@classmethod
	def Is(cls, i ):
		if isinstance(i, cls):
			return True
		elif isinstance(i, CObject) and cls._IS and cls._IS(i._cobject):
			return True
		else:
			return False

	@classmethod
	def Wrap(cls, i):
		return cls(ffi.cast(cls._TYPE, i))

	def __init__(self, o, wrap=True):
		self._cobject = o if not self._TYPE else ffi.cast(self._TYPE, o)
		assert o

class Match(CObject):

	_TYPE = "Match*"

	def walk( self, callback ):
		def c(m,s):
			m = Match(m)
			callback(m,s)
		c = ffi.callback("void(*)(void *, size_t)", c)
		return lib.Match__walk(self._cobject, c, 0)

	def offset( self ):
		return self._cobject.offset

	def length( self ):
		return self._cobject.length

class Reference(CObject):

	_TYPE = "Reference*"
	_IS  = lambda o: lib.Reference_Is(o)

	def __init__(self, o=None, wrap=False):
		if not wrap:
			assert isinstance(o, ParsingElement)
			assert o._cobject != ffi.NULL
			print "POUET", o._cobject
			print lib.Reference_New(o._cobject).element
			CObject.__init__(self, lib.Reference_New(o._cobject))
			print self._cobject.element
			assert self._cobject.element, "Ensured reference has no element: o={0}, reference={1}".format(e, self._cobject)
		else:
			assert o
			print "REF2", o
			CObject.__init__(self, lib.Reference_New(o))

	def _as( self, name ):
		lib.Reference_name(self._cobject, name)
		return self

	def one( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_ONE)
		return self

	def optional( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_OPTIONAL)
		return self

	def zeroOrMore( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_MANY_OPTIONAL)
		return self

	def oneOrMore( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_MANY)
		return self

	def disableMemoize( self ):
		return self

	def disableFailMemoize( self ):
		return self

class ParsingElement(CObject):

	_TYPE = "ParsingElement*"
	_IS  = lambda o: lib.ParsingElement_Is(o)

	def add( self, *children ):
		for c in children:
			assert isinstance(c, ParsingElement) or isinstance(c, Reference)
			lib.ParsingElement_add(self._cobject, lib.Reference_Ensure(c._cobject))
		return self

	def setName( self, name ):
		lib.ParsingElement_name(self._cobject, name)
		return self

	def set( self, *children ):
		return self.add(*children)

	def _as( self, name ):
		return Reference(self)._as(name)

	def optional( self ):
		return Reference(self).optional()

	def zeroOrMore( self ):
		return Reference(self).zeroOrMore()

	def oneOrMore( self ):
		return Reference(self).oneOrMore()

	def disableMemoize( self ):
		return self

	def disableFailMemoize( self ):
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

class Condition(ParsingElement):

	@classmethod
	def WrapCallback(cls, callback):
		def c(e,ctx):
			return callback(e,ctx)
		t = "Match*(*)(ParsingElement *, ParsingContext *)"
		c = ffi.callback(t, c)
		return c

	def __init__( self, callback, wrap=False ):
		CObject.__init__(self, callback if wrap else lib.Condition_new(self.WrapCallback(callback)))

class Procedure(ParsingElement):

	@classmethod
	def WrapCallback(cls, callback):
		def c(e,ctx):
			return callback(e,ctx)
		t = "void(*)(ParsingElement *, ParsingContext *)"
		c = ffi.callback(t, c)
		return c

	def __init__( self, callback, wrap=False ):
		CObject.__init__(self, callback if wrap else lib.Procedure_new(self.WrapCallback(callback)))

class Symbols:

	def __setitem__( self, key, value ):
		setattr(self, key, value)
		return value

	def __getitem__( self, key ):
		return getattr(self, key)

class Grammar(CObject):

	def __init__(self, name=None ):
		CObject.__init__(self, lib.Grammar_new())
		self.name    = name
		self.symbols = Symbols()

	def word( self, name, word):
		r = Word(word)
		self.symbols[name] = r
		return r

	def token( self, name, token):
		r = Token(token)
		self.symbols[name] = r
		return r

	def procedure( self, name, callback):
		r = Procedure(callback)
		self.symbols[name] = r
		return r

	def aprocedure( self, callback):
		return Procedure(callback)

	def condition( self, name, callback):
		r = Condition(callback)
		self.symbols[name] = r
		return r

	def acondition( self, callback):
		return Condition(callback)

	def group( self, name, *children):
		r = Group(*children)
		self.symbols[name] = r
		return r

	def rule( self, name, *children):
		r = Rule(*children)
		self.symbols[name] = r
		return r

	def arule( self, name, *children):
		return Rule(*children)

	def agroup( self, name, *children):
		return Group(*children)

	def prepare( self ):
		lib.Grammar_prepare(self._cobject)
		return self

	def axiom( self, axiom ):
		if isinstance(axiom, Reference):
			axiom = axiom._cobject.element
			assert axiom
		assert isinstance(axiom, ParsingElement)
		self._cobject.axiom = axiom._cobject
		return self.prepare()

	def skip( self, skip ):
		assert isinstance(skip, ParsingElement)
		self._cobject.skip = skip._cobject
		return self

	def parsePath( self, path ):
		return Match(lib.Grammar_parseFromPath(self._cobject, path))

	def walk( self, callback ):
		def c(o,s):
			# FIXME: This does not seem to work
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
		return lib.Element__walk(self._cobject.axiom, c, 0)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	g  = Grammar()
	print lib.Reference_New(
		lib.Word_new("POUET")
	).element
	# print Word("a")._as("name")
	# assert Word("a")._cobject
	# a  = Word("a")._as("a")
	# b  = Word("b")._as("b")
	# ws = Token("\\s+")
	# e  = Group(a, b)._as("e")
	# g.axiom(e).skip(ws)
	# match = g.parsePath("pouet.txt")
	# def mw(m, step):
	# 	print "MATCH", step, m.offset(), m.length()
	# def gw(e, step):
	# 	print "ELEMENT", e
	# match.walk(mw)
	# NOTE: The following does not work
	# g.walk(gw)

# EOF - vim: ts=4 sw=4 noet
