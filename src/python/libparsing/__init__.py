#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 18-Dec-2014
# Last modification : 15-Nov-2016
# -----------------------------------------------------------------------------

from __future__ import print_function

import sys, os, re
from   cffi    import FFI
from   os.path import dirname, join, abspath

__doc__ = """
The CFFI-based Python wrapper for libparsing.
"""

# TODO: Switch to pre-compilation
# TODO: Use global callbacks http://cffi.readthedocs.io/en/latest/using.html#id3

try:
	import reporter as logging
except ImportError:
	import logging

VERSION            = "0.8.5"
LICENSE            = "http://ffctn.com/doc/licenses/bsd"
PACKAGE_PATH       = dirname(abspath(__file__))
LIB_PATH           = dirname(PACKAGE_PATH)
LIB_ALT_PATH       = dirname(LIB_PATH)
SRC_PATH           = join(dirname(LIB_PATH), "src")
FFI_PATH           = join(PACKAGE_PATH,       "libparsing.ffi")
H_PATH             = join(SRC_PATH,           "parsing.h")
NOTHING            = re

# -----------------------------------------------------------------------------
#
# FFI
#
# -----------------------------------------------------------------------------

ffi = FFI()
lib = None
LIB_PATHS = (LIB_PATH, LIB_ALT_PATH, PACKAGE_PATH)
assert os.path.exists(FFI_PATH), "libparsing: Missing FFI interface file {0}".format(FFI_PATH)
with open(FFI_PATH, "r") as f:
	ffi.cdef(f.read())
for p in LIB_PATHS:
	p = join(p, "libparsing.so")
	if os.path.exists(p):
		lib = ffi.dlopen(p)
		break
assert lib, "libparsing: Cannot find libparsing.so in any of {0}".format(", ".join(LIB_PATHS))

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
	def Wrap( cls, cobject ):
		return cls(cobject, wrap=cls.TYPE())

	@classmethod
	def TYPE( cls ):
		if not cls._TYPE:
			cls._TYPE = cls.__name__.rsplit(".")[-1] + "*"
		return cls._TYPE

	def __init__(self, *args, **kwargs):
		self._cobject = None
		self._init()
		if "wrap" in kwargs:
			assert len(kwargs) == 1
			assert len(args  ) == 1
			self._wrap(ffi.cast(kwargs["wrap"], args[0]))
		else:
			o = self._new(*args, **kwargs)
			if o is not None: self._cobject = ffi.cast(self.TYPE(), o)
			assert self._cobject

	def _init( self ):
		pass

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
# PARSING ELEMENT
#
# -----------------------------------------------------------------------------

class ParsingElement(CObject):

	_TYPE = "ParsingElement*"

	@classmethod
	def IsCType( self, element ):
		return isinstance(element, FFI.CData) and lib.ParsingElement_Is(element)

	def isReference( self ):
		return False

	@property
	def name( self ):
		return ffi.string(self._cobject.name)

	@name.setter
	def name( self, name ):
		lib.ParsingElement_name(self._cobject, name)
		return self

	@property
	def id( self ):
		return self._cobject.id

	@property
	def type( self ):
		return self._cobject.type

	def set( self, *children ):
		return self.add(*children)

	def add( self, *children ):
		for c in children:
			assert isinstance(c, ParsingElement) or isinstance(c, Reference)
			lib.ParsingElement_add(self._cobject, lib.Reference_Ensure(c._cobject))
		return self

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
		classname = self.__class__.__name__.rsplit(".", 1)[-1]
		if not self._cobject:
			return "<%s:Uninitialized>" % (classname)
		else:
			return "<%s:%s[%s]#%d>" % (
				classname,
				self.type,
				self.name,
				self.id
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
		# SEE: http://stackoverflow.com/questions/34392109/use-extern-python-style-cffi-callbacks-with-embedded-pypy
		def c(e,ctx):
			res = callback(ParsingElement.Wrap(e), ParsingContext.Wrap(ctx)) if callback else 1
			return res
		t = "bool(*)(ParsingElement *, ParsingContext *)"
		c = ffi.callback(t, c)
		return c

	def _new( self, callback ):
		self._callback = (self.WrapCallback(callback), callback)
		return lib.Condition_new(self._callback[0])

# -----------------------------------------------------------------------------
#
# PROCEDURE
#
# -----------------------------------------------------------------------------

class Procedure(ParsingElement):

	@classmethod
	def WrapCallback(cls, callback):
		def c(e,ctx):
			return callback(ParsingElement.Wrap(e), ParsingContext.Wrap(ctx))
		t = "void(*)(ParsingElement *, ParsingContext *)"
		c = ffi.callback(t, c)
		return c

	def _new( self, callback ):
		self._callback = (self.WrapCallback(callback), callback)
		return lib.Procedure_new(self._callback[0])

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
		assert element._cobject
		r = lib.Reference_FromElement(element._cobject)
		assert r.element == element._cobject, "Reference element should be {0}, got {1}".format(element._cobject, r.element)
		return r

	# =========================================================================
	# ACCESSORS
	# =========================================================================

	@property
	def name( self ):
		return ffi.string(self._cobject.name) if self._cobject.name != ffi.NULL else None

	@property
	def id( self ):
		return self._cobject.id

	@property
	def element( self ):
		return ParsingElement.Wrap(self._cobject.element)

	@property
	def type( self ):
		return TYPE_REFERENCE

	# =========================================================================
	# API
	# =========================================================================

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

	# =========================================================================
	# HELPERS
	# =========================================================================

	def cardinality( self ):
		return self._cobject.cardinality

	def isReference( self ):
		return True

	def isOne( self ):
		return self.cardinality() == CARDINALITY_ONE

	def isZeroOrMore( self ):
		return self.cardinality() == CARDINALITY_MANY_OPTIONAL

	def isOneOrMore( self ):
		return self.cardinality() == CARDINALITY_MANY

	def isOptional( self ):
		return self.cardinality() == CARDINALITY_OPTIONAL

	def isMany( self ):
		return self.isZeroOrMore() or self.isOneOrMore()

	def __repr__(self):
		return "<{0} {1}@{2}→{3}>".format(
			self.__class__.__name__.rsplit(".", 1)[-1],
			self.id,
			self.name,
			self.element
		)

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
		return Match(cobject, wrap=cls._TYPE)

	def _new( self, o ):
		return ffi.cast("Match*", o)

	# =========================================================================
	# ACCESSORS
	# =========================================================================

	@property
	def element( self ):
		return self._cobject.element

	@property
	def offset( self ):
		return self._cobject.offset

	@property
	def type( self ):
		return lib.Match_getElementType(self._cobject)

	@property
	def name( self ):
		name = lib.Match_getElementName(self._cobject)
		return ffi.string(name) if name else None

	@property
	def id( self ):
		return lib.Match_getElementID(self._cobject)

	@property
	def length( self ):
		return self._cobject.length

	@property
	def range( self ):
		o, l = self.offset(), self.length()
		return o, o + l

	def slots( self ):
		return list(_ for _ in self if _.name)

	def indexForKey( self, name ):
		for i,_ in enumerate(self):
			if _.name == name:
				return i
		return -1

	def hasChildren( self ):
		return lib.Match_hasChildren(self._cobject)

	def toJSON( self ):
		return lib.Match_toJSON(self._cobject, 1)

	# =========================================================================
	# SUGAR
	# =========================================================================

	def __iter__( self ):
		child = self._cobject.children
		while child:
			yield Match.Wrap(child)
			child = child.next

	def __getitem__( self, index ):
		if type(index) == int:
			for i,c in enumerate(self):
				if i == index:
					return c
			raise KeyError
		else:
			# FIXME: It would be better to do Match_indexForKey(‥)
			i = self.indexForKey(index)
			if i >= 0:
				return self[i]
			else:
				raise KeyError

	def __repr__(self):
		return "<{0} {1}:{2}@{3} {4}-{5}>".format(
			self.__class__.__name__.rsplit(".", 1)[-1],
			self.type,
			self.id,
			self.name,
			self.offset,
			self.offset + self.length,
		)

# -----------------------------------------------------------------------------
#
# MATCH RESULT
#
# -----------------------------------------------------------------------------

class MatchResult(object):

	def __init__( self, value, match ):
		assert not isinstance(value, MatchResult)
		self.value = value
		self.match = match

	@property
	def name( self ):
		return self.match.name

	@property
	def id( self ):
		return self.match.id

	def group( self, index=0 ):
		return self[index]

	def __getitem__( self, index ):
		if type(index) == int:
			if isinstance(self.value, list) or isinstance(self.value, tuple):
				if index < 0: index += len(self.value)
				for i,c in enumerate(self.value):
					if i == index:
						return c
			elif index == 0:
				return self.value
			else:
				raise Exception("MatchResult has non-iterable result: {0}".format(self))
		else:
			i = self.match.indexForKey(index)
			if i == -1:
				raise Exception("MatchResult does not define slot {1}, options are {2}: {0}".format(self, index, self.match.slots()))
			else:
				return self[i]

	def __repr__(self):
		return "<{0} {1}={2}>".format(
			self.__class__.__name__.rsplit(".", 1)[-1],
			self.match,
			self.value
		)

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
# PARSING CONTEXT
#
# -----------------------------------------------------------------------------

class ParsingContext(CObject):

	_TYPE = "ParsingContext*"

	@property
	def offset( self ):
		return lib.ParsingContext_getOffset(self._cobject)

	@property
	def line( self ):
		return self._cobject.iterator.lines

	def push( self ):
		lib.ParsingContext_push(self._cobject)
		return self

	def pop( self ):
		lib.ParsingContext_pop(self._cobject)
		return self

	def set( self, key, value ):
		assert isinstance(value, int)
		lib.ParsingContext_setInt(self._cobject, key, value)
		return value

	def get( self, key ):
		return lib.ParsingContext_getInt(self._cobject, key)

	def __getitem__( self, offset ):
		return lib.ParsingContext_charAt(self._cobject, offset)

# -----------------------------------------------------------------------------
#
# PARSING RESULT
#
# -----------------------------------------------------------------------------

class ParsingResult(CObject):

	_TYPE = "ParsingResult*"

	@property
	def status( self ):
		return self._cobject.status

	@property
	def match( self ):
		return Match.Wrap(self._cobject.match)

	@property
	def stats( self ):
		return ParsingStats.Wrap(self._cobject.context.stats)

	@property
	def line( self ):
		return self._cobject.context.iterator.lines

	@property
	def offset( self ):
		return self._cobject.context.iterator.offset

	@property
	def remaining( self ):
		return lib.ParsingResult_remaining(self._cobject)

	@property
	def textOffset( self ):
		return lib.ParsingResult_textOffset(self._cobject)

	@property
	def text( self ):
		return ffi.string(self._cobject.context.iterator.buffer)

	# =========================================================================
	# METHODS
	# =========================================================================

	def isSuccess( self ):
		return True if lib.ParsingResult_isSuccess(self._cobject) != 0 else False

	def isFailure( self ):
		return True if lib.ParsingResult_isFailure(self._cobject) != 0 else False

	def isPartial( self ):
		return True if lib.ParsingResult_isPartial(self._cobject)!= 0 else False

	# =========================================================================
	# HELPERS
	# =========================================================================

	def lastMatchRange( self ):
		# FIXME: Should be wrapped in a a function
		o = self._cobject.context.stats.matchOffset or 0
		r = self._cobject.context.stats.matchLength or 0
		return (o, o + r)

	def textAround( self, before=3, after=3 ):
		t    = self.text
		s,e  = self.lastMatchRange()
		bt   = t[0:s].rsplit("\n", before + 1)[-before-1:]
		at   = t[e:].split("\n", after + 1)[:after+1]
		c    = bt[-1] + t[s:e] + at[0]
		bc   = len(bt[-1]) * " "
		cc   = "⤒" + (max(0,e-s)) * "⤒"
		ac   = max(0,len(at[-1]) - 1) * " "
		return (
			"\n│ ".join(bt[:-1]) + \
			"\n└┐" + c +  \
			"\n┌┘" + bc + cc + ac + "\n│ " + \
			"\n│ ".join(at[1:])
		)

	def describe( self ):
		if self.isSuccess():
			return "Parsing successful"
		else:
			s,e   = self.lastMatchRange ()
			t     = self.textAround()
			lines = self.text[:s].split("\n")
			line  = len(lines) - 1
			char  = len(lines[-1])
			return "Parsing failed at line {0}:{1}, range {2}→{3}:{4}".format(
				line, char, s, e,
				"\n".join([_ for _ in t.split("\n")])
			)

	def toJSON( self ):
		return self.match.toJSON()

	def XXX__repr__( self ):
		return "<{0}(status={2}, line={3}, char={4}, offset={5}, remaining={6}) at {1:02x}>".format(
			self.__class__.__name__,
			id(self),
			self.status, self.line, -1, self.offset, 0
		)

	def __del__( self ):
		# The parsing result is the only one we really need to free
		# along with the grammar
		# lib.ParsingResult_free(self._cobject)
		pass

# -----------------------------------------------------------------------------
#
# PARSING STATS
#
# -----------------------------------------------------------------------------

class ParsingStats(CObject):

	def bytesRead( self ):
		return self._cobject.bytesRead

	def parseTime( self ):
		return self._cobject.parseTime

	def totalSuccess( self ):
		return sum(self._cobject.successBySymbol[i] for i in range(self._cobject.symbolsCount))

	def totalFailures( self ):
		return sum(self._cobject.failureBySymbol[i] for i in range(self._cobject.symbolsCount))

	def symbolsCount( self ):
		return self._cobject.symbolsCount

	def symbols( self ):
		return [
			(i, self._cobject.successBySymbol[i], self._cobject.failureBySymbol[i]) for i in range(self.symbolsCount())
		]

	def report( self, grammar=None, output=sys.stdout ):
		br    = self.bytesRead()
		pt    = self.parseTime()
		ts    = self.totalSuccess()
		tf    = self.totalFailures()
		def write(s):
			output.write(s)
			output.write("\n")
		write("Bytes read :  {0}".format(br))
		write("Parse time :  {0}s".format(pt))
		write("Throughput :  {0}Mb/s".format(br/1024.0/1024.0/pt))
		write("-" * 80)
		write("Sucesses   :  {0}".format(ts))
		write("Failures   :  {0}".format(tf))
		write("Throughput :  {0}op/s".format((ts + tf) / pt))
		write("Op time    : ~{0}/op".format(pt / (ts + tf)))
		write("Op/byte    :  {0}".format((ts + tf) / br))
		write("-" * 80)
		write("   SYMBOL   NAME                               SUCCESSES       FAILURES")
		s  = sorted(self.symbols(), lambda a,b:cmp(b[1] + b[2], a[1] + a[2]))
		c  = 0
		ct = 0
		for sid, s, f in s:
			ct += 1
			if s == 0 and f == 0: continue
			e = grammar.symbol(sid) if grammar else None
			n = ""
			if e:
				if e.isReference():
					n = "*" + e.element().name() + "(" + e.cardinality() + ")"
					if e.name():
						n += ":" + e.name()
				else:
					n = e.name()
			write("{0:9d} {1:31s} {2:14d} {3:14d}".format(sid, n, s, f))
			c += 1
		write("-" * 80)
		write("Activated  :  {0}/{1} ~{2}%".format(c, ct, int(100.0 * c / ct)))
		return self


# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

class Grammar(CObject):

	_TYPE = "Grammar*"

	def _new(self, name=None, isVerbose=True ):
		self.name    = name
		self.symbols = Symbols()
		g = lib.Grammar_new()
		g.isVerbose = 1 if isVerbose else 0
		self._prepared  = False
		self._anonymous = []
		return g

	# =========================================================================
	# PARSING
	# =========================================================================

	def parsePath( self, path ):
		self._prepare()
		return ParsingResult.Wrap(lib.Grammar_parsePath(self._cobject, path))

	def parseString( self, text ):
		self._prepare()
		return ParsingResult.Wrap(lib.Grammar_parseString(self._cobject, text))

	# =========================================================================
	# AXIOM AND SKIPPING
	# =========================================================================

	@property
	def axiom( self ):
		return self._cobject.axiom

	@axiom.setter
	def axiom( self, axiom ):
		self._prepared = False
		if isinstance(axiom, Reference):
			axiom = axiom._cobject.element
			assert axiom
		assert isinstance(axiom, ParsingElement)
		self._cobject.axiom = axiom._cobject
		return self

	@property
	def skip( self ):
		return self._cobject.skip

	@skip.setter
	def skip( self, skip ):
		self._prepared = False
		assert isinstance(skip, ParsingElement)
		self._cobject.skip = skip._cobject
		return self

	# =========================================================================
	# FACTORY METHODS
	# =========================================================================

	def word( self, name, word):
		self._prepared = False
		r = Word(word)
		r.name = name
		self.symbols[name] = r
		return r

	def aword( self, word):
		self._prepared = False
		return self._registerAnonymous(Word(word))

	def token( self, name, token):
		self._prepared = False
		r = Token(token)
		r.name = name
		self.symbols[name] = r
		return r

	def atoken( self, token):
		self._prepared = False
		return self._registerAnonymous(Token(token))

	def procedure( self, name, callback):
		self._prepared = False
		r = Procedure(callback)
		r.name = name
		self.symbols[name] = r
		return r

	def aprocedure( self, callback):
		self._prepared = False
		return self._registerAnonymous(Procedure(callback))

	def condition( self, name, callback=None):
		self._prepared = False
		r = Condition(callback)
		r.name = name
		self.symbols[name] = r
		return r

	def acondition( self, callback=None):
		self._prepared = False
		return self._registerAnonymous(Condition(callback))

	def group( self, name, *children):
		self._prepared = False
		r = Group(*children)
		r.name = name
		self.symbols[name] = r
		return r

	def agroup( self, *children):
		self._prepared = False
		return self._registerAnonymous(Group(*children))

	def rule( self, name, *children):
		self._prepared = False
		r = Rule(*children)
		r.name = name
		self.symbols[name] = r
		return r

	def arule( self, *children):
		self._prepared = False
		return self._registerAnonymous(Rule(*children))

	def _registerAnonymous( self, element ):
		"""Forces the grammar to keep references to anonymous symbols it
		created."""
		self._anonymous.append(element)
		return element

	# =========================================================================
	# META / HELPERS
	# =========================================================================

	def setVerbose( self, verbose=True ):
		# FIXME: That cast should not be necessary
		e = ffi.cast("Grammar*", self._cobject)
		e.isVerbose = 1 if verbose else 0
		return self

	def isVerbose( self, verbose ):
		# FIXME: That cast should not be necessary
		e = ffi.cast("Grammar*", self._cobject)
		return e.isVerbose == 1

	def symbol( self, id ):
		if type(id) is int:
			e = ffi.cast("Reference*", self._cobject.elements[id])
			if e.type == TYPE_REFERENCE:
				return Reference.Wrap(e)
			else:
				return ParsingElement.Wrap(e)
		else:
			return getattr(self.symbols, id)

	def list( self ):
		"""Lists the symbols defined in the grammar."""
		res = []
		for k in dir(self.symbols):
			if k.startswith("__"): continue
			res.append((k, getattr(self.symbols, k)))
		return res

	def _prepare( self ):
		"""Ensures the grammar is prepared."""
		if not self._prepared:
			self.prepare()

	def prepare( self ):
		lib.Grammar_prepare(self._cobject)
		self._prepared = True

	def __del__( self ):
		# The parsing result is the only one we really need to free
		# along with the grammar
		# lib.Grammar_free(self._cobject)
		pass


# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------

class Processor:

	def __init__( self, grammar=None ):
		self.depth = 0
		self.setGrammar(self.ensureGrammar(grammar))

	def ensureGrammar( self, grammar ):
		return grammar or self.createGrammar()

	def createGrammar( self ):
		raise NotImplementedError

	def setGrammar( self, grammar ):
		self.symbols      = grammar.list() if grammar else []
		self.symbolByName = {}
		self.symbolByID   = {}
		self.handlerByID  = {}
		self._bindSymbols()
		self._bindHandlers()

	def _bindSymbols( self ):
		for name, s in self.symbols:
			if not s:
				reporter.error("Name without symbol: %s" % (name))
				continue
			self.symbolByName[name] = s
			if s.id in self.symbolByID:
				if s.id >= 0:
					raise Exception("Duplicate symbol id: %d, has %s already while trying to assign %s" % (s.id(), self.symbolByID[s.id()].name(), s.name()))
				else:
					logging.warn("Unused symbol: %s" % (repr(s)))
			self.symbolByID[s.id] = s

	def _bindHandlers( self ):
		for k in dir(self):
			if not k.startswith("on"): continue
			name = k[2:]
			if not name:
				continue
			assert name in self.symbolByName, "Handler does not match any symbol: {0}, symbols are {1}".format(k, ", ".join(self.symbolByName.keys()))
			symbol = self.symbolByName[name]
			self.handlerByID[symbol.id] = getattr(self, k)

	def process( self, match ):
		self.depth += 1
		match  = match.match if isinstance(match, ParsingResult) else match
		result = self._processMatch(match) if isinstance(match, Match) else match
		self.depth -= 1
		return result.value if self.depth == 0 and isinstance(result, MatchResult) else result


	def _processMatch( self, match ):
		"""Processes a match element."""
		t = match.type
		i = match.id
		r = None
		if t == TYPE_WORD:
			r = self._processWord(match)
		elif t == TYPE_TOKEN:
			r = self._processToken(match)
		elif t == TYPE_CONDITION:
			r = self._processCondition(match)
		elif t == TYPE_PROCEDURE:
			r = self._processProcedure(match)
		elif t == TYPE_GROUP:
			r = self._processGroup(match)
		elif t == TYPE_RULE:
			r = self._processRule(match)
		elif t == TYPE_REFERENCE:
			r = self._processReference(match)
		else:
			raise Exception("Unsupported match type: {0} in {1}".format(t, match))
		h = self.handlerByID.get(i)
		r = h(MatchResult(r,match)) if h else r
		return r.value if isinstance(r, MatchResult) else r

	def _processWord( self, match ):
		return ffi.string(lib.Word_word(match.element))

	def _processToken( self, match ):
		n = lib.TokenMatch_count(match._cobject)
		if n == 0:
			return None
		elif n == 1:
			return ffi.string(lib.TokenMatch_group(match._cobject, 0))
		else:
			return list(ffi.string(lib.TokenMatch_group(match._cobject, i)) for i in range(n))

	def _processCondition( self, match ):
		return True

	def _processProcedure( self, match ):
		return True

	def _processGroup( self, match ):
		# FIXME: This should probably not be wrapped in a list
		return self._processMatch(match[0])

	def _processRule( self, match ):
		return list(self._processMatch(_) for _ in match)

	def _processReference( self, match ):
		if not lib.Reference_IsMany(match.element):
			return self._processMatch(match[0]) if match.hasChildren() else None
		else:
			return list(self._processMatch(_) for _ in match)

class TreeWriter(Processor):
	"""A special processor that outputs the named parsing elements
	registered in the parse tree. It is quite useful for debugging grammars."""

	def __init__( self, grammar=None, output=sys.stdout ):
		AbstractProcessor.__init__(self, grammar)
		self.output = output
		self.reset()

	def reset( self ):
		self.indent = 0
		self.count  = 0

	def defaultProcess(self, match):
		named = isinstance(match.element() , ParsingElement) and match.element().name() != "_"
		if named:
			self.output.write("{0:04d}|{1}{2}\n".format(self.count, self.indent * "    "  + "|---" , match.element().name()))
			self.indent += 1
		self.count  += 1
		r = AbstractProcessor.defaultProcess(self, match)
		if named:
			self.indent -= 1
		return r

def __init__():
	pass

# EOF - vim: ts=4 sw=4 noet
