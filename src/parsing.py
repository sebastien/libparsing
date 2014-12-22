#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2014-12-18
# Last modification : 2014-12-19
# -----------------------------------------------------------------------------

from cffi import FFI
import re, os
import cdoclib

try:
	import reporter as logging
except ImportError:
	import logging

VERSION  = "0.0.0"
LICENSE  = "http://ffctn.com/doc/licenses/bsd"
FFI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parsing.ffi")
H_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parsing.h")
NOTHING  = re

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
		"typedef struct TokenMatchGroup TokenMatchGroup;\n"
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
		("TokenMatch",           O),
		("Token_*",              O),
		("TokenMatch_*",         O),
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
lib = ffi.dlopen("libparsing.so.0.3.0")

CARDINALITY_OPTIONAL      = '?'
CARDINALITY_ONE           = '1'
CARDINALITY_MANY_OPTIONAL = '*'
CARDINALITY_MANY          = '+'
TYPE_WORD                 = 'W'
TYPE_TOKEN                = 'T'
TYPE_GROUP                = 'G'
TYPE_RULE                 = 'R'
TYPE_CONDITION            = 'c'
TYPE_PROCEDURE            = 'p'
TYPE_REFERENCE            = '#'
STATUS_INIT               = '-'
STATUS_PROCESSING         = '~'
STATUS_MATCHED            = 'Y'
STATUS_FAILED             = 'X'
STATUS_INPUT_ENDED        = '.'
STATUS_ENDED              = 'E'
ID_BINDING                = -1
ID_UNBOUND                = -10

# -----------------------------------------------------------------------------
#
# C OJBECT ABSTRACTION
#
# -----------------------------------------------------------------------------

class CObject(object):

	_TYPE = None

	@classmethod
	def Wrap( cls, cobject, ocls=None ):
		if not cls._TYPE:
			cls._TYPE = cls.__name__.rsplit(".")[-1] + "*"
		return cls(cobject, wrap=cls._TYPE)

	def __init__(self, *args, **kwargs):
		self._cobject = None
		if "wrap" in kwargs:
			assert len(kwargs) == 1
			assert len(args  ) == 1
			self._wrap(ffi.cast(kwargs["wrap"], args[0]))
		else:
			o = self._new(*args, **kwargs)
			if o is not None: self._cobject = o
			assert self._cobject

	def _new( self ):
		raise NotImplementedError

	def _wrap( self, cobject ):
		assert self._cobject == None
		assert isinstance(cobject, FFI.CData), "%s: Trying to wrap non CData value: %s" % (self.__class__.__name__, cobject)
		assert cobject != ffi.NULL, "%s: Trying to wrap NULL value: %s" % (self.__class__.__name__, cobject)
		self._cobject = cobject
		return self

# -----------------------------------------------------------------------------
#
# MATCH
#
# -----------------------------------------------------------------------------

class Match(CObject):

	_TYPE = "Match*"

	@classmethod
	def Wrap( cls, cobject ):
		assert cobject.element != ffi.NULL, "Match C object does not have an element: %s %d+%d" % (cobject.status, cobject.offset, cobject.length)
		e = ffi.cast("ParsingElement*", cobject.element)
		if e.type == TYPE_WORD:
			return WordMatch( cobject, wrap=cls._TYPE)
		elif e.type == TYPE_TOKEN:
			return TokenMatch( cobject, wrap=cls._TYPE)
		else:
			return cls(cobject, wrap=cls._TYPE)

	def _new( self, o ):
		return ffi.cast("Match*", o)

	def group( self ):
		e = ffi.cast("ParsingElement*", self._cobject.element)
		if e.type == TYPE_GROUP:
			return self.children()[0]
		else:
			return self.children()

	def walk( self, callback ):
		def c(m,s):
			m = Match.Wrap(m)
			return callback(m,s)
		c = ffi.callback("int(*)(void *, int)", c)
		return lib.Match__walk(self._cobject, c, 0)

	def next( self ):
		return Match.Wrap(self._cobject.next) if self._cobject.next != ffi.NULL else None

	def child( self ):
		return Match.Wrap(self._cobject.child) if self._cobject.child != ffi.NULL else None

	def resolveID( self, id ):
		for c in self.children():
			e = match.element()
			if isinstance(e, Reference) and e.id() == id:
				pass

	def variables( self ):
		"""Returns a list of named references"""
		pass

	def children( self ):
		child = self._cobject.child
		res   = []
		while child and child != ffi.NULL:
			assert child.element
			res.append(Match.Wrap(child))
			child = child.next
		return res

	def element( self ):
		return Reference.Wrap(self._cobject.element) if self.isFromReference() else ParsingElement.Wrap(self._cobject.element)

	def isFromReference( self ):
		return lib.Reference_Is(self._cobject.element)

	def data( self, data=NOTHING ):
		if data is NOTHING:
			return self._cobject.data
		else:
			self._cobject.data = data
			return data

	def offset( self ):
		return self._cobject.offset

	def length( self ):
		return self._cobject.length

	def range( self ):
		o, l = self.offset(), self.length()
		return o, o + l

	def __iter__( self ):
		return self.children()

	def __getitem__( self, index ):
		assert type(index) is int
		i = 0
		for c in self.children():
			if i == index:
				return c
			i += 1
		return None

	def __repr__(self):
		element = self.element()
		type    = element._cobject.type
		name    = element.name() or "#" + str(element.id())
		if isinstance(element, Reference):
			suffix = element.cardinality()
		else:
			suffix = ""
		return "<%s:%s[%s]%s(%d) %d-%d>" % (
			self.__class__.__name__.rsplit(".", 1)[-1],
			type,
			name,
			suffix,
			len(self.children()),
			self.offset(),
			self.offset() + self.length(),
		)

# -----------------------------------------------------------------------------
#
# WORD MATCH
#
# -----------------------------------------------------------------------------

class WordMatch(Match):

	def group( self ):
		return "FIXME:WORD"
		# FIXME: The following causes a segfault
		element = ffi.cast("ParsingElement*", self._cobject)
		config = ffi.cast("WordConfig*", element.config)
		return ffi.string(config.word)

# -----------------------------------------------------------------------------
#
# TOKEN MATCH
#
# -----------------------------------------------------------------------------

class TokenMatch(Match):

	def group( self, i=0 ):
		r = lib.TokenMatch_group(self._cobject, i)
		s      = lib.TokenMatch_group(self._cobject, i)
		r      = "" + ffi.string(s)
		return r

# -----------------------------------------------------------------------------
#
# REFERENCE
#
# -----------------------------------------------------------------------------

class Reference(CObject):

	@classmethod
	def IsCType( self, element ):
		return isinstance(element, FFI.CData) and lib.Reference_Is(element)

	def _new( self, element ):
		assert isinstance(element, ParsingElement)
		r = lib.Reference_New(element._cobject)
		assert r.element == element._cobject
		return r

	def name( self ):
		return ffi.string(self._cobject.name) if self._cobject.name != ffi.NULL else None

	def id( self ):
		return self._cobject.id

	def _as( self, name ):
		lib.Reference_name(self._cobject, name)
		return self

	def one( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_ONE)
		return self

	def isOne( self ):
		return self.cardinality() == CARDINALITY_ONE

	def optional( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_OPTIONAL)
		return self

	def isOptional( self ):
		return self.cardinality() == CARDINALITY_OPTIONAL

	def zeroOrMore( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_MANY_OPTIONAL)
		return self

	def isZeroOrMore( self ):
		return self.cardinality() == CARDINALITY_MANY_OPTIONAL

	def oneOrMore( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_MANY)
		return self

	def isOneOrMore( self ):
		return self.cardinality() == CARDINALITY_MANY

	def cardinality( self ):
		return self._cobject.cardinality

	def disableMemoize( self ):
		return self

	def disableFailMemoize( self ):
		return self

# -----------------------------------------------------------------------------
#
# PARSING ELEMENT
#
# -----------------------------------------------------------------------------

class ParsingElement(CObject):

	_TYPE = "ParsingElement*"

	@classmethod
	def IsCType( self, element ):
		return isinstance(element, FFI.CData) and lib.ParsingElement_Is(element)

	def add( self, *children ):
		for c in children:
			assert isinstance(c, ParsingElement) or isinstance(c, Reference)
			lib.ParsingElement_add(self._cobject, lib.Reference_Ensure(c._cobject))
		return self

	def name( self ):
		return ffi.string(self._cobject.name)

	def id( self ):
		return self._cobject.id

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

	def __repr__(self):
		return "<%s:%s[%s]#%d>" % (
			self.__class__.__name__.rsplit(".", 1)[-1],
			self._cobject.type,
			ffi.string(self._cobject.name),
			self._cobject.id,
		)

# -----------------------------------------------------------------------------
#
# WORD
#
# -----------------------------------------------------------------------------

class Word(ParsingElement):

	def _new( self, word):
		return lib.Word_new(word)

# -----------------------------------------------------------------------------
#
# TOKEN
#
# -----------------------------------------------------------------------------

class Token(ParsingElement):

	def _new( self, token):
		return lib.Token_new(token)

# -----------------------------------------------------------------------------
#
# GROUP
#
# -----------------------------------------------------------------------------

class Group(ParsingElement):

	def _new( self, *children ):
		self._cobject = lib.Group_new(ffi.NULL)
		self.add(*children)

# -----------------------------------------------------------------------------
#
# RULE
#
# -----------------------------------------------------------------------------

class Rule(ParsingElement):

	def _new( self, *children ):
		self._cobject = lib.Rule_new(ffi.NULL)
		self.add(*children)

# -----------------------------------------------------------------------------
#
# CONDITION
#
# -----------------------------------------------------------------------------

class Condition(ParsingElement):

	@classmethod
	def WrapCallback(cls, callback):
		def c(e,ctx):
			callback(e,ctx)
			return ffi.NULL
		t = "Match*(*)(ParsingElement *, ParsingContext *)"
		c = ffi.callback(t, c)
		return c

	def _new( self, callback ):
		return lib.Condition_new(ffi.NULL) # ;self.WrapCallback(callback))

# -----------------------------------------------------------------------------
#
# PROCEDURE
#
# -----------------------------------------------------------------------------

class Procedure(ParsingElement):

	@classmethod
	def WrapCallback(cls, callback):
		def c(e,ctx):
			callback(e,ctx)
			return ffi.NULL
		t = "void(*)(ParsingElement *, ParsingContext *)"
		c = ffi.callback(t, c)
		return c

	def _new( self, callback ):
		return lib.Procedure_new(ffi.NULL) #;self.WrapCallback(callback))

# -----------------------------------------------------------------------------
#
# SYMBOLS
#
# -----------------------------------------------------------------------------

class Symbols:

	def __setitem__( self, key, value ):
		setattr(self, key, value)
		return value

	def __getitem__( self, key ):
		return getattr(self, key)

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

class Grammar(CObject):

	def _new(self, name=None ):
		self.name    = name
		self.symbols = Symbols()
		return lib.Grammar_new()

	def list( self ):
		res = []
		for k in dir(self.symbols):
			if k.startswith("__"): continue
			res.append((k, getattr(self.symbols, k)))
		return res

	def word( self, name, word):
		r = Word(word)
		r.setName(name)
		self.symbols[name] = r
		return r

	def token( self, name, token):
		r = Token(token)
		r.setName(name)
		self.symbols[name] = r
		return r

	def procedure( self, name, callback):
		r = Procedure(callback)
		r.setName(name)
		self.symbols[name] = r
		return r

	def aprocedure( self, callback):
		return Procedure(callback)

	def condition( self, name, callback):
		r = Condition(callback)
		r.setName(name)
		self.symbols[name] = r
		return r

	def acondition( self, callback):
		return Condition(callback)

	def group( self, name, *children):
		r = Group(*children)
		r.setName(name)
		self.symbols[name] = r
		return r

	def agroup( self, *children):
		return Group(*children)

	def rule( self, name, *children):
		r = Rule(*children)
		r.setName(name)
		self.symbols[name] = r
		return r

	def arule( self, *children):
		return Rule(*children)

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
			if    Reference.IsCType(o):
				o = Reference.Wrap(o)
			elif  ParsingElement.IsCType(o):
				o = ParsingElement.Wrap(o)
			else:
				o = Match.Wrap(o)
			return callback(o, s)
		c = ffi.callback("int(*)(void *, int)", c)
		return lib.Element__walk(self._cobject.axiom, c, 0)

# -----------------------------------------------------------------------------
#
# ABSTRACT PROCESSOR
#
# -----------------------------------------------------------------------------

class AbstractProcessor:

	def __init__( self, grammar ):
		self.symbols = grammar.list()
		self.symbolByName = {}
		self.symbolByID   = {}
		self.handlerByID  = {}
		self._bindSymbols()
		self._bindHandlers()

	def _bindSymbols( self ):
		for n, s in self.symbols:
			if not s:
				reporter.error("[!] Name without symbol: %s" % (n))
				continue
			self.symbolByName[s.name()] = s
			if s.id() in self.symbolByID:
				if s.id() >= 0:
					raise Exception("Duplicate symbol id: %d, has %s already while trying to assign %s" % (s.id(), self.symbolByID[s.id()].name(), s.name()))
				else:
					logging.warn("Unused symbol: %s" % (repr(s)))
			self.symbolByID[s.id()]     = s

	def _bindHandlers( self ):
		for k in dir(self):
			if not k.startswith("on"): continue
			name = k[2:]
			# assert name in self.symbolByName, "Handler does not match any symbol: {0}".format(k)
			symbol = self.symbolByName[name]
			self.handlerByID[symbol.id()] = getattr(self, k)

	def process( self, match ):
		# res = [self.walk(_) for _ in match.children()]
		#print "MATCH", match.element().name(), ":", res, self._process(match)
		return self._process(match)

	def _process( self, match ):
		eid = match.element().id()
		handler = self.handlerByID.get(eid)
		# print "[PROCESS]", eid, match.element().name()
		if handler:
			kwargs = {}
			for m in match.children():
				e = m.element()
				n = e.name()
				if n: kwargs[n] = self.process(m)
			if match.isFromReference():
				return handler(match, **kwargs)
			else:
				return handler(match, **kwargs)
		else:
			# If we don't have a handler, we recurse
			return self.defaultProcess(match)

	def defaultProcess( self, match ):
		m = [self._process(m) for m in match.children()]
		if not m:
			return match.group() or None
		elif len(m) == 1 and m[0] is None:
			return None
		elif match.isFromReference():
			r = match.element()
			if r.isOptional():
				return m[0]
			elif r.isOne():
				return m[0]
			else:
				return m
		else:
			return m

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	g  = Grammar()
	s  = g.symbols
	g.token("NUMBER",   "\d+(\.\d+)?")
	g.token("VARIABLE", "\w[\w_\d]*")
	g.token("OPERATOR", "[\-\+\*/\^]")
	g.group("Value",      s.NUMBER, s.VARIABLE)
	g.rule("Suffix",      s.OPERATOR, s.Value)
	g.rule("Expression")
	s.Expression.set(s.Value, s.Suffix.zeroOrMore(), s.Expression)
	g.axiom(s.Expression)
	# lib.Grammar_prepare(g._cobject)

	visited = []
	def gw(e, step):
		# The following is an exit condition for recursion
		if step > e.id(): return -1
		print "[%5d] %s%s:%d" % (step, "*" if isinstance(e, Reference) else " ", e.name(), e.id())
		return step
	g.walk(gw)


	# print lib.Reference_New(
	# 	lib.Word_new("POUET")
	# ).element
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
