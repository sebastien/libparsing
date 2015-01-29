#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 18-Dec-2014
# Last modification : 30-Dec-2014
# -----------------------------------------------------------------------------

import sys, os, re
from   cffi    import FFI
from   os.path import dirname, join, abspath

try:
	import reporter as logging
except ImportError:
	import logging

VERSION            = "0.5.1"
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

# Creates the .ffi file from the header or loads it directly from the
# previously generated one.
if os.path.exists(H_PATH):
	sys.path.insert(0, dirname(dirname(abspath(__file__))))
	import cdoclib
	clib = cdoclib.Library(H_PATH)
	O    = ("type", "constructor", "operation", "method", "destructor")
	# NOTE: We need to generate a little bit of preample before outputting
	# the types.
	cdef = (
		"typedef char* iterated_t;\n"
		"typedef void Element;\n"
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
	with open(FFI_PATH, "w") as f:
		f.write(cdef)
else:
	with open(FFI_PATH, "r") as f:
		cdef = f.read()

ffi = FFI()
ffi.cdef(cdef)
lib = None
for p in (LIB_PATH, LIB_ALT_PATH, PACKAGE_PATH):
	p = join(p, "libparsing.so")
	if os.path.exists(p):
		lib = ffi.dlopen(p)
		break
assert lib, "libparsing: Cannot find libparsing.so"
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
		if "wrap" in kwargs:
			assert len(kwargs) == 1
			assert len(args  ) == 1
			self._wrap(ffi.cast(kwargs["wrap"], args[0]))
		else:
			o = self._new(*args, **kwargs)
			if o is not None: self._cobject = ffi.cast(self.TYPE(), o)
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
		if type(index) == int:
			i = 0
			for c in self.children():
				if i == index:
					return c
				i += 1
		else:
			for c in self.children():
				if c.element().name() == index:
					return c
			raise KeyError
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
		element = ffi.cast("ParsingElement*", self._cobject.element)
		config  = ffi.cast("WordConfig*", element.config)
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

	def element( self ):
		return ParsingElement.Wrap(self._cobject.element)

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

	def isReference( self ):
		return True

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
# PARSING RESULT
#
# -----------------------------------------------------------------------------

class ParsingResult(CObject):

	_TYPE = "ParsingResult*"

	def match( self ):
		return Match.Wrap(self._cobject.match)

	def status( self ):
		return self._cobject.status

	def stats( self ):
		return ParsingStats.Wrap(self._cobject.context.stats)

	def line( self ):
		return self._cobject.context.iterator.lines

	def offset( self ):
		return self._cobject.context.iterator.offset

	def text( self ):
		return ffi.string(self._cobject.context.iterator.buffer)

	def textaround( self, line=None ):
		if line is None: line = self.line()
		i = self.offset()
		t = self.text()
		while i > 1 and t[i] != "\n": i -= 1
		if i != 0: i += 1
		return t[i:(i+100)].split("\n")[0]

	def __del__( self ):
		# The parsing result is the only one we really need to free
		# along with the grammar
		lib.ParsingResult_free(self._cobject)

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

	def _new(self, name=None, verbose=True ):
		self.name    = name
		self.symbols = Symbols()
		g = lib.Grammar_new()
		g.isVerbose = 1 if verbose else 0
		return g

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

	def aword( self, word):
		return Word(word)

	def token( self, name, token):
		r = Token(token)
		r.setName(name)
		self.symbols[name] = r
		return r

	def atoken( self, token):
		return Token(token)

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
		return ParsingResult.Wrap(lib.Grammar_parseFromPath(self._cobject, path))

	def parseString( self, text ):
		return ParsingResult.Wrap(lib.Grammar_parseFromString(self._cobject, text))

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

	def __del__( self ):
		# The parsing result is the only one we really need to free
		# along with the grammar
		lib.Grammar_free(self._cobject)

# -----------------------------------------------------------------------------
#
# ABSTRACT PROCESSOR
#
# -----------------------------------------------------------------------------

class AbstractProcessor:

	def __init__( self, grammar ):
		self.symbols = grammar.list() if grammar else []
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
		if isinstance(match, ParsingResult): match = match.match()
		return self._process(match)

	def _process( self, match ):
		eid = match.element().id()
		handler = self.getHandler(eid)
		# print "[PROCESS]", eid, match.element().name()
		if handler:
			kwargs = {}
			# We only bind the arguments listed
			varnames = handler.func_code.co_varnames
			for m in match.children():
				e = m.element()
				n = e.name()
				if n and n in varnames:
					kwargs[n] = self.process(m)
			if match.isFromReference():
				return handler(match, **kwargs)
			else:
				return handler(match, **kwargs)
		else:
			# If we don't have a handler, we recurse
			return self.defaultProcess(match)

	def getHandler( self, eid ):
		return self.handlerByID.get(eid)

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


class TreeWriter(AbstractProcessor):
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

# EOF - vim: ts=4 sw=4 noet
