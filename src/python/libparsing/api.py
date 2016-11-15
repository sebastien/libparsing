#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : libparsing (Python bindings)
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2016-01-21
# Last modification : 2016-11-08
# -----------------------------------------------------------------------------

from __future__ import print_function
import sys, traceback, inspect
from   libparsing.bindings import *
from   copy import copy

try:
	import reporter as logging
except ImportError as e:
	import logging

__doc__ = """
Object-oriented bindings to the libparsing C library.
"""

LIB      = None
NOTHING  = object()

# -----------------------------------------------------------------------------
#
# DEFINES/LIBRARY
#
# -----------------------------------------------------------------------------

CARDINALITY_OPTIONAL      = b'?'
CARDINALITY_ONE           = b'1'
CARDINALITY_MANY_OPTIONAL = b'*'
CARDINALITY_MANY          = b'+'
TYPE_WORD                 = b'W'
TYPE_TOKEN                = b'T'
TYPE_GROUP                = b'G'
TYPE_RULE                 = b'R'
TYPE_CONDITION            = b'c'
TYPE_PROCEDURE            = b'p'
TYPE_REFERENCE            = b'#'
STATUS_INIT               = b'-'
STATUS_PROCESSING         = b'~'
STATUS_MATCHED            = b'Y'
STATUS_FAILED             = b'X'
STATUS_INPUT_ENDED        = b'.'
STATUS_ENDED              = b'E'

# -----------------------------------------------------------------------------
#
# PARSING ELEMENTS
#
# -----------------------------------------------------------------------------

class ParsingElement(CObject):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	void  ParsingElement_free(ParsingElement* this);
	"""

	@cproperty
	def name( self ):
		return cproperty

	@property
	def children( self ):
		# By default, a parsing element has no children
		return ()

	def getBindings( self ):
		return dict( (e.name,i) for i,e in enumerate(self.children) if e.name)

	def _as( self, name ):
		"""Returns a new Reference wrapping this parsing element."""
		return Reference.FromElement(element=self, name=name)

	def one( self ):
		return Reference.FromElement(element=self, cardinality=CARDINALITY_ONE)

	def optional( self ):
		return Reference.FromElement(element=self, cardinality=CARDINALITY_OPTIONAL)

	def zeroOrMore( self ):
		return Reference.FromElement(element=self, cardinality=CARDINALITY_MANY_OPTIONAL)

	def oneOrMore( self ):
		return Reference.FromElement(element=self, cardinality=CARDINALITY_MANY)

# -----------------------------------------------------------------------------
#
# COMPOSITE PARSING ELEMENTS
#
# -----------------------------------------------------------------------------

class CompositeElement(ParsingElement):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	this* ParsingElement_add(ParsingElement* this, Reference* child); // @as _add
	this* ParsingElement_clear(ParsingElement* this);                 // @as _clear
	"""

	def _new(self, *args):
		ParsingElement._new(self, None)
		for _ in args:
			self.add(_)

	@caccessor
	def children(self):
		"""Returns the children of this ParsingElement as a tuple."""
		child_cvalue  = self._cobject.children
		children      = []
		while child_cvalue:
			children.append(self.LIBRARY.wrap(child_cvalue))
			child_cvalue = child_cvalue.contents.next
		return tuple(children)

	def set( self, *references ):
		self.clear()
		self.add(*references)
		return self

	def clear( self ):
		self._clear()
		self._cobjectCache["children"] = ((), ())
		return self

	def add( self, *references ):
		res = list(self.children)
		for i, reference in enumerate(references):
			assert reference, "{0}.add: no reference given, got {1} as argument #{2}".format(self.__class__.__name__, reference, i)
			assert isinstance(reference, ParsingElement) or isinstance(reference, Reference), "{0}.add: Expected ParsingElement or Reference, got {1} as argument #{2}".format(self.__class__, reference, i)
			reference = Reference.Ensure(reference)
			assert isinstance(reference, Reference)
			self._add(reference)
			# TODO: Should update the underlying children as well
			res.append(reference)
		# FIXME: Not sure what we should do with the second argument of the cache
		self._cobjectCache["children"] = (res, None)
		return self

	def __getitem__( self, index ):
		return self.children[index]

	def __iter__( self ):
		for _ in self.children:
			yield _

# -----------------------------------------------------------------------------
#
# REFERENCE
#
# -----------------------------------------------------------------------------

class Reference(CObject):

	WRAPPED   = TReference

	FUNCTIONS = """
	Reference* Reference_FromElement(ParsingElement* element);           // @as _FromElement
	Reference* Reference_new(void);
	void       Reference_free(Reference* this);
	bool       Reference_hasElement(Reference* this);
	bool       Reference_hasNext(Reference* this);
	"""

	@classmethod
	def Ensure( cls, element ):
		return element if isinstance(element, Reference) else cls.FromElement(element)

	@classmethod
	def FromElement( cls, element, name=None, cardinality=None ):
		assert isinstance( element, ParsingElement)
		assert element._cobject
		res = cls._FromElement(element)
		assert isinstance(res, Reference), "Expected reference, got: {0}".format(res)
		res.element = element
		assert ctypes.addressof(res._cobject.element.contents) == ctypes.addressof(element._cobject), "CObject refernce transparency is broken: {0} != {1}".format(res._cobject.element, element._cobjectPointer)
		assert res.element is element
		if name        is not None: res.name        = name
		if cardinality is not None: res.cardinality = cardinality
		# The reference will be freed automatically by the element
		res._mustFree = False
		return res

	def _new( self, element=None, name=None, cardinality=NOTHING ):
		CObject._new(self)
		if element:
			self.element = element
			assert self.element is element
		if name is not None:
			self.name = name
		if cardinality in (CARDINALITY_ONE, CARDINALITY_OPTIONAL, CARDINALITY_MANY_OPTIONAL, CARDINALITY_MANY):
			self._cobject.cardinality = cardinality
			assert self.cardinality == cardinality

	# =========================================================================
	# PROPERTIES
	# =========================================================================

	@cproperty
	def name( self ):
		return cproperty

	@cproperty
	def element( self ):
		return cproperty

	# =========================================================================
	# PREDICATES
	# =========================================================================

	def one( self ):
		self._cobject.cardinality = CARDINALITY_ONE
		assert self.cardinality == CARDINALITY_ONE
		return self

	def optional( self ):
		self._cobject.cardinality = CARDINALITY_OPTIONAL
		assert self.cardinality == CARDINALITY_OPTIONAL
		return self

	def zeroOrMore( self ):
		assert None
		self._cobject.cardinality = CARDINALITY_MANY_OPTIONAL
		assert self.cardinality == CARDINALITY_MANY_OPTIONAL
		return self

	def oneOrMore( self ):
		self._cobject.cardinality = CARDINALITY_MANY
		assert self.cardinality == CARDINALITY_MANY
		return self

	def _as( self, name ):
		self.name = name
		assert self.name == name
		return self

	def __repr__( self ):
		return "<Reference#{1}:{0}={2}({3}) at {4}>".format(self.name, self.id, self.element, self.cardinality, hex(id(self)))

	def __getitem__( self, index):
		return self.element[index]

# -----------------------------------------------------------------------------
#
# WORD
#
# -----------------------------------------------------------------------------

class Word(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Word_new(const char* word);
	void Word_free(ParsingElement* this);
	void Word_print(ParsingElement* this); // @as _print
	const char* Word_word(ParsingElement* this);  // @as _getWord
	"""

	def _new( self, word ):
		self.__word = (word, self.LIBRARY.unwrap(word))
		ParsingElement._new(self, self.__word[1])
		assert self._getWord() == self.__word[1], "Word: could not assign word Python={0} → unwrapped={1} → libparsing={2}".format(repr(word), repr(self.__word[1]), repr(self._getWord()))

	def __repr__( self ):
		return "<Word#{1}:{0}=`{2}` at {3}>".format(self.name, self.id, self._getWord(), hex(id(self)))

class Token(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Token_new(const char* expr);
	void Token_free(ParsingElement* this);
	void Token_print(ParsingElement* this); // @as _print
	const char* Token_expr(ParsingElement* this);  // @as _getExpr
	"""
	def _new( self, expr ):
		self.__expr = (expr, self.LIBRARY.unwrap(expr))
		ParsingElement._new(self, self.__expr[1])

	def __repr__( self ):
		return "<Token#{1}:{0}=`{2}` at {3}>".format(self.name, self.id, self._getExpr(), hex(id(self)))

# -----------------------------------------------------------------------------
#
# CONDITION
#
# -----------------------------------------------------------------------------

class Condition(ParsingElement):
	FUNCTIONS = """
	ParsingElement* Condition_new(ConditionCallback c);
	"""

	def _init( self ):
		ParsingElement._init(self)
		self._callback = None

	def _new( self, callback=None ):
		py_callback = lambda element, context: (callback(self.LIBRARY.wrap(element),self.LIBRARY.wrap(context)) and True) if callback else True
		c_callback  = C.TYPES["ConditionCallback"](py_callback)
		self._callback = (py_callback, c_callback, callback)
		return ParsingElement._new(self, c_callback)

	def __repr__( self ):
		return "<Condition#{1}:{0}={2} at {3}>".format(self.name, self.id, None, hex(id(self)))

# -----------------------------------------------------------------------------
#
# PROCEDURE
#
# -----------------------------------------------------------------------------

class Procedure(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Procedure_new(ProcedureCallback c);
	"""

	def _init( self ):
		ParsingElement._init(self)
		self._callback = None

	def _new( self, callback ):
		py_callback = lambda element,context: (callback(self.LIBRARY.wrap(element),self.LIBRARY.wrap(context)) and None) if callback else None
		c_callback  = C.TYPES["ProcedureCallback"](py_callback)
		self._callback = (py_callback, c_callback, callback)
		return ParsingElement._new(self, c_callback)

	def __repr__( self ):
		return "<Procedure#{1}:{0}={2} at {3}>".format(self.name, self.id, None, hex(id(self)))

# -----------------------------------------------------------------------------
#
# RULE
#
# -----------------------------------------------------------------------------

class Rule(CompositeElement):

	# FIXME: No free method here
	FUNCTIONS = """
	ParsingElement* Rule_new(void* children);
	"""

	def __repr__( self ):
		return "<Rule#{1}:{0}<2> at {3}>".format(self.name, self.id, len(list(self)), hex(id(self)))

# -----------------------------------------------------------------------------
#
# GROUP
#
# -----------------------------------------------------------------------------

class Group(CompositeElement):

	# FIXME: No free method here
	FUNCTIONS = """
	ParsingElement* Group_new(void* children);
	"""

	def __repr__( self ):
		return "<Group#{1}:{0}=[2] at {3}>".format(self.name, self.id, len(list(self)), hex(id(self)))

# -----------------------------------------------------------------------------
#
# MATCH
#
# -----------------------------------------------------------------------------

class Match(CObject):

	WRAPPED   = TMatch
	FUNCTIONS = """
	bool Match_isSuccess(Match* this);
	int Match_getOffset(Match* this);
	int Match_getLength(Match* this);
	char Match_getElementType(Match* this);
	const char* Match_getElementName(Match* this);
	bool Match_hasNext(Match* this);
	Match* Match_getNext(Match* this);
	bool Match_hasChildren(Match* this);
	bool Match_getChildren(Match* this);
	void Match_free(Match* this);
	int Match__walk(Match* this, WalkingCallback callback, int step, PyObject* context );
	int Match_countAll(Match* this);
	void Match_toJSON(Match* this, int fd); // @as _toJSON
	"""

	def _init( self ):
		self._value   = NOTHING

	def group( self, index=0 ):
		raise NotImplementedError("{0}.group not() implemented".format(self.__class__.__name__))

	def _extractValue( self ):
		raise NotImplementedError("{0}._extractValue() not implemented".format(self.__class__.__name__))

	@property
	def children( self ):
		return ()

	@property
	def count( self ):
		return len(self.children)

	@caccessor
	def element( self ):
		return self.LIBRARY.wrap(self._cobject.element)

	@property
	def name( self ):
		"""The name of the reference."""
		return self.element.name

	@property
	def value( self ):
		"""Value is an accessor around this Match's value, which can
		be transformed by a match processor. By default, there is no value."""
		if self._value != NOTHING:
			return self._value
		else:
			self._value = self._extractValue()
			return self._value

	@value.setter
	def value( self, value ):
		"""Sets the value in this specific match."""
		self._value = value
		return self

	# FIXME: Not sure that offset/length are working
	def range( self ):
		"""Returns the range (start, end) of the match."""
		o = self.offset or 0
		l = self.length or 0
		return (o, o+l)

	def isReference( self ):
		"""A utility shorthand to know if a match is a reference."""
		return self.getType() == TYPE_REFERENCE

	def text( self ):
		s,e = self.range()
		return self.context.text()[s:e]

	def toJSON( self ):
		return self._toJSON(1)

	def __repr__( self ):
		element = self.element
		return "<{0}:{1}#{2}:{3}+{4} @ {5}>".format(self.__class__.__name__, element.name or element.type, element.id, self.offset, self.length, hex(id(self)))

# -----------------------------------------------------------------------------
#
# COMPOSITE MATCH
#
# -----------------------------------------------------------------------------

class CompositeMatch(Match):

	@caccessor
	def children(self):
		"""Returns the children of this Match as a tuple."""
		child_cvalue  = self._cobject.children
		children      = []
		while child_cvalue:
			children.append(self.LIBRARY.wrap(child_cvalue))
			child_cvalue = child_cvalue.contents.next
		return tuple(children)

	def get( self, name=NOTHING ):
		if name is NOTHING:
			return dict((_.name, _) for _ in self.children if _.name)
		else:
			for _ in self.children:
				if _.name == name:
					return _
			return None

	def names( self ):
		return [_.name for _ in self]

	def group( self, index=NOTHING ):
		if index is NOTHING:
			return [_.group() for _ in self]
		else:
			return self[index].group()

	def __getitem__( self, index ):
		if isinstance(index, str):
			return self.get(index)
		else:
			return self.children[index]

	def __iter__( self ):
		for _ in self.children:
			yield _

	def __len__( self ):
		return len(self.children)

# -----------------------------------------------------------------------------
#
# REFERENCE MATCH
#
# -----------------------------------------------------------------------------

class ReferenceMatch(CompositeMatch):

	@caccessor
	def reference( self ):
		return self.LIBRARY.wrap(ctypes.cast(self._cobject.element, C.TYPES["Reference*"]))

	@caccessor
	def element( self ):
		return self.reference.element

	@property
	def name( self ):
		"""The name of the reference."""
		return self.reference.name

	@property
	def cardinality( self ):
		return self.reference.cardinality

	def _extractValue( self ):
		if self.isOne() or self.isOptional():
			return self.children[0].value if self.children else None
		else:
			return [_.value for _ in self.children]

	# TODO: We might want to restore that
	# def group( self, index=0 ):
	# 	if self.child is None:
	# 		return None
	# 	elif self.isOne():
	# 		return self.child.group(0)
	# 	else:
	# 		return self.getChild(index).group()
	#
	# def groups( self ):
	# 	return [_.group() for _ in self]

	def isOne( self ):
		return self.cardinality == CARDINALITY_ONE

	def isOptional( self ):
		return self.cardinality == CARDINALITY_OPTIONAL

	def isZeroOrMore( self ):
		return self.cardinality == CARDINALITY_MANY_OPTIONAL

	def isOneOrMore( self ):
		return self.cardinality == CARDINALITY_MANY

	def __repr__( self ):
		return "<{0}:{1}={2}#{3}[{4}] @ {5}>".format(self.__class__.__name__, self.reference.name, self.element.name, self.element.id, self.cardinality, hex(id(self)))

# -----------------------------------------------------------------------------
#
# WORD MATCH
#
# -----------------------------------------------------------------------------

class WordMatch(Match):

	FUNCTIONS = """
	const char* WordMatch_group(Match* this); // @as _group
	"""

	def _extractValue( self ):
		return self.group()

	def group( self, index=0 ):
		"""Returns the word matched"""
		if index != 0: raise IndexError
		assert index == 0
		if "group" not in self._cobjectCache:
			c_value  = self._group()
			py_value = c_value.decode("utf8")
			self._cobjectCache["group"] = (py_value, c_value)
		return self._cobjectCache["group"][0]

	def __getitem__( self, index ):
		return self.group(index)

# -----------------------------------------------------------------------------
#
# TOKEN MATCH
#
# -----------------------------------------------------------------------------

class TokenMatch(Match):

	FUNCTIONS = """
	const char* TokenMatch_group(Match* this, int index); // @as _group
	int TokenMatch_count(Match* this);
	"""

	@caccessor
	def data( self ):
		return ctypes.cast(self._cobject.data,    C.TYPES["TokenMatch*"]).contents.decode("utf-8")

	def _extractValue( self ):
		return self.group(0)

	def group( self, index=0 ):
		groups = self._cobjectCache.setdefault("group", {})
		if index not in groups:
			c_value  = self._group(index)
			py_value = c_value.decode("utf8") if c_value is not None else None
			groups[index] = (py_value, c_value)
		return groups[index][0]

	def groups( self ):
		return [self.group(i) for i in range(self.match.count)]

	def __getitem__( self, index ):
		return self.group(index)

# -----------------------------------------------------------------------------
#
# PROCEDURE MATCH
#
# -----------------------------------------------------------------------------

class ProcedureMatch(Match):

	def group( self, index=0):
		return True

	def _extractValue( self ):
		return True

# -----------------------------------------------------------------------------
#
# CONDITION MATCH
#
# -----------------------------------------------------------------------------

class ConditionMatch(Match):

	def group( self, index=0):
		return True

	def _extractValue( self ):
		return True

# -----------------------------------------------------------------------------
#
# RULE MATCH
#
# -----------------------------------------------------------------------------

class RuleMatch(CompositeMatch):

	def _extractValue( self ):
		return [_.value for _ in self.children]

# -----------------------------------------------------------------------------
#
# GROUP MATCH
#
# -----------------------------------------------------------------------------

class GroupMatch(CompositeMatch):

	def _extractValue( self ):
		c = list(self.children)
		assert len(c) <= 1
		return c[0].value

# -----------------------------------------------------------------------------
#
# PARSING CONTEXT
#
# -----------------------------------------------------------------------------

class ParsingContext(CObject):

	WRAPPED   = TParsingContext
	FUNCTIONS = """
	ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator );
	void*  ParsingContext_get(ParsingContext* this, const char* name);
	void   ParsingContext_set(ParsingContext* this, const char* name, void* value);
	void   ParsingContext_push( ParsingContext* this );
	void   ParsingContext_pop( ParsingContext* this );
	void   ParsingContext_on(ParsingContext* this, ConditionCallback callback);
	int    ParsingContext_getVariableCount(ParsingContext* this);
	size_t ParsingContext_getOffset(ParsingContext* this);
	char   ParsingContext_charAt ( ParsingContext* this, size_t offset );
	void ParsingContext_free( ParsingContext* this );
	"""

	@property
	def offset( self ):
		return self.getOffset()

	@property
	def text( self ):
		return self.iterator.buffer

	def char( self, offset ):
		return self.charAt(offset)

	def __getitem__( self, offset ):
		return self.charAt(offset)

# -----------------------------------------------------------------------------
#
# PARSING STATS
#
# -----------------------------------------------------------------------------

class ParsingStats(CObject):

	WRAPPED   = TParsingStats
	FUNCTIONS = """
	"""

	def totalSuccess( self ):
		return sum(self._cobject.successBySymbol[i] for i in range(self.symbolsCount))

	def totalFailures( self ):
		return sum(self._cobject.failureBySymbol[i] for i in range(self.symbolsCount))

	def symbols( self ):
		return [
			(i, self._cobject.successBySymbol[i], self._cobject.failureBySymbol[i]) for i in range(self.symbolsCount)
		]

	def report( self, grammar=None, output=sys.stdout ):
		br    = self.bytesRead
		pt    = self.parseTime
		ts    = self.totalSuccess()
		tf    = self.totalFailures()
		def write(s):
			output.write(s)
			output.write("\n")
		write("Bytes read :  {0}".format(br))
		write("Parse time :  {0}s".format(pt))
		write("Throughput :  {0:0.3}Mb/s".format(br/1024.0/1024.0/pt))
		write("-" * 80)
		write("Sucesses   :  {0}".format(ts))
		write("Failures   :  {0}".format(tf))
		write("Throughput :  {0:0.3f}kop/s".format(((ts + tf) / pt) / 1000.0))
		write("Op/byte    :  {0}".format((ts + tf) / br))
		write("-" * 80)
		write("   SYMBOL   NAME                               SUCCESSES       FAILURES     RATE")
		sy = sorted(self.symbols(), lambda a,b:cmp(b[1] + b[2], a[1] + a[2]))
		c  = 0
		ct = 0
		ts = 0
		tf = 0
		for sid, s, f in sy:
			ct += 1
			if s == 0 and f == 0: continue
			e = grammar.symbol(sid) if grammar else None
			n = ""
			if e:
				if isinstance(e, Reference):
					n = "*" + e.element.name + "(" + e.cardinality + ")"
					if e.name:
						n += ":" + e.name
				else:
					n = e.name
			write("{0:9d}   {1:29s} {2:14d} {3:14d} {4:7d}%".format(sid, n, s, f, 100 * s/(s+f)))
			ts += s
			tf += f
			c += 1
		write("-" * 80)
		write("{0:9d}   {1:29s} {2:14d} {3:14d} {4:7d}%".format(len(sy), "SYMBOLS / MATCHES", ts, tf, 100 * ts/(ts+tf)))
		write("-" * 80)
		write("Symbols activated  :  {0}/{1} ~{2}%".format(c, ct, int(100.0 * c / ct)))
		return self

# -----------------------------------------------------------------------------
#
# PARSING RESULTS
#
# -----------------------------------------------------------------------------

class ParsingResult(CObject):

	WRAPPED   = TParsingResult
	FUNCTIONS = """
	void   ParsingResult_free(ParsingResult* this);
	bool   ParsingResult_isFailure(ParsingResult* this);  // @as _isFailure
	bool   ParsingResult_isPartial(ParsingResult* this);  // @as _isPartial
	bool   ParsingResult_isSuccess(ParsingResult* this);  // @as _isSuccess
	int    ParsingResult_textOffset(ParsingResult* this); // @as _textOffset
	size_t ParsingResult_remaining(ParsingResult* this);
	"""

	@caccessor
	def stats( self ):
		return self.LIBRARY.wrap(self._cobject.context.contents.stats)

	@property
	def line( self ):
		return self.context.iterator.lines

	@property
	def offset( self ):
		return self.context.iterator.offset

	@property
	def text( self ):
		return self.context.iterator.buffer

	@property
	def textOffset( self ):
		return self._textOffset()

	def isSuccess( self ):
		return True if self._isSuccess() != 0 else False

	def isFailure( self ):
		return True if self._isFailure() != 0 else False

	def isPartial( self ):
		return True if self._isPartial() != 0 else False

	def lastMatchRange( self ):
		o = self.context.stats.matchOffset or 0
		r = self.context.stats.matchLength or 0
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

	def __repr__( self ):
		return "<{0}(status={2}, line={3}, char={4}, offset={5}, remaining={6}) at {1:02x}>".format(
			self.__class__.__name__,
			id(self),
			self.status, self.line, -1, self.offset, self.remaining() or 0
		)

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

class Grammar(CObject):

	WRAPPED   = TGrammar

	FUNCTIONS = """
	Grammar* Grammar_new(void);
	void Grammar_free(Grammar* this);
	void Grammar_prepare ( Grammar* this );
	ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator );
	ParsingResult* Grammar_parsePath( Grammar* this, const char* path );
	ParsingResult* Grammar_parseString( Grammar* this, const char* text ); // @as _parseString
	"""

	PROPERTIES = lambda:dict(
		axiom = Word
	)

	@classmethod
	def Register( cls, *classes ):
		for _ in classes:
			cls.RegisterParsingElement(_)

	@classmethod
	def RegisterParsingElement( cls, parsingClass ):
		c = parsingClass
		assert issubclass(c, ParsingElement)
		def anonymous_creator( self, *args, **kwargs ):
			element = c(*args, **kwargs)
			# The element will be freed by the grammar when its
			# reference will be lost
			# element._mustFree   = False
			self._symbols["_" + str(element.id)] = element
			return element
		def named_creator( self, name, *args, **kwargs ):
			element = c(*args, **kwargs)
			# NOTE: This was causing some problems before as it was
			# overriding the field
			element.name = name
			# The element will be freed by the grammar when its
			# reference will be lost
			# element._mustFree   = False
			self._symbols[name] = element
			assert name in self._symbols
			assert hasattr(self.symbols, name)
			return element
		name = c.__name__.rsplit(".", 1)[-1].lower()
		setattr(cls, name,       named_creator)
		setattr(cls, "a" + name, anonymous_creator)

	def _init( self ):
		assert "name" not in self.ACCESSORS
		self.name = None

	def _new( self, name=None, isVerbose=False, axiom=None ):
		CObject._new(self)
		self.name      = name
		self.isVerbose = isVerbose and 1 or 0
		self.axiom     = axiom
		self.symbols   = CLibrary.Symbols()
		self._symbols  = self.symbols.__dict__

	def symbol( self, id ):
		if type(id) is int:
			return self.LIBRARY.wrap(self._cobject.elements[id])
		else:
			return getattr(self.symbols, id)

	def parseString( self, text ):
		self.text = text
		return self._parseString( text )

# -----------------------------------------------------------------------------
#
# PROCESS
#
# -----------------------------------------------------------------------------

class HandlerException(Exception):
	"""An exception that happened in processor handler. Stores a reference to
	the handler as well as the arguments and context, which is super useful
	for debugging."""

	def __init__( self, exception, args, handler, context):
		self.exception = exception
		self.args      = args
		self.handler   = handler
		self.context   = context

	def __str__( self ):
		return "{0}: {1} in {2} with {3}".format(self.__class__.__name__, self.exception, self.handler, self.args)

class FastMatch(object):

	def __init__( self, element ):
		self.element  = element
		self.bindings = element.getBindings() if element else {}
		self.value    = None
		self.range    = None

	def set( self, value, range ):
		self.value = value
		self.range = range
		return self

	def group( self, value ):
		return self[value]

	def __getitem__( self, value ):
		if value == 0 and isinstance( self.element, Group):
			return self.value
		elif isinstance(value,str) or isinstance(value,bytes):
			return self.value[self.bindings[value]]
		else:
			return self.value[value]

class FastProcessor(object):
	"""The main entry point when using `libparsing` form Python. Subclass
	the processor and define parsing element handlers using the convention
	`on<ParsingElement's name`. For instance, if your grammar has a `NAME`
	symbol defined, then `onNAME` will be invoked with its match element.

	Note that symbol handlers (`onXXX` methods) take the `match` object
	as first argument as well as the named elements defined in the symbol,
	if it is a composite symbol (rule, group, etc). The named elements
	are the ones you declare using `_as`."""

	def __init__(self, grammar=None):
		self._grammar  = None
		self.setGrammar(grammar)

	def ensureGrammar( self ):
		if not self._grammar: self.setGrammar(self.createGrammar())
		return self._grammar

	def createGrammar( self ):
		return None

	def setGrammar( self, grammar ):
		if grammar == self._grammar: return
		self._grammar  = grammar
		if grammar:
			g = grammar
			s = g.symbols
			handlers = {}
			max_id   = 0
			elements = {}
			for k in dir(s):
				e = getattr(s,k)
				if isinstance(e, ParsingElement) and e.id >= 0:
					max_id = max(max_id, e.id + 1)
					elements[e.id] = e
			self._symbols  = [elements.get(_)     for _ in range(0, max_id)]
			self._matches  = [FastMatch(_)        for _ in self._symbols]
			self._handlers = [self._getHandler(_) for _ in self._symbols]
		else:
			self._handlers = None
			self._matches  = None
			self._symbols  = None

	def process( self, match ):
		if isinstance(match, ParsingResult): match = match.match
		if isinstance(match, Match):
			return LIB.symbols.Match_processPython(match._cobject, self._handlers)
		else:
			return match

	def _defaultHandler( self, match=None, range=None, id=None ):
		return match

	def _getHandler( self, element ):
		if not element: return None
		name = element.name
		i    = element.id
		mname   = "on" + name[0].upper() + name[1:]
		mid     = "on" + str(i)
		handler = self._defaultHandler
		if hasattr(self, mname):
			handler = self._wrapHandler(getattr(self, mname), element)
		elif hasattr(self, mid):
			handler = self._wrapHandler(getattr(self, mid), element)
		return handler

	def _wrapHandler( self, handler, element ):
		params = inspect.getargspec(handler).args
		params = params[2:] if params[0]=="self" else params[1]
		match  = self._matches[int(element.id)]
		# We create simple wrappers for the regular cases, where
		# the handler is h(match), h(match,range), h(match,range,id)
		def wrapper(m,r,i):
			try:
				res = handler(match.set(m,r))
				return res
			except Exception as e:
				exc_type, exc_obj, tb = sys.exc_info()
				context         = traceback.format_exc().splitlines()
				print ("libparsing: Error")
				for _ in context:
					print (_)
				return None

		# Now we're in a more complex case where we need to extract variables
		# kwargs         = [_ for _ in params if _ not in ("range", "id")]
		# slots          = dict( (_.name,i) for i,_ in enumerate(element.children) if _.name)
		# kwargs_valid   = [_ for _ in kwargs if _ in     slots]
		# kwargs_invalid = [_ for _ in kwargs if _ not in slots]
		# indexes        = slots.items()
		# def wrapper( match, range=None, id=None):
		# 	kw = dict( (k,match[i]) for (k,i) in indexes)
		# 	print ("CALLING", handler, kw)
		# 	if has_range and "range" not in kw: kw["range"] = range
		# 	if has_id    and "id"    not in kw: kw["id"]    = id
		# 	try:
		# 		result = handler(match, **kw)
		# 	except Exception as e:
		# 		return error(e)
		return wrapper

class Processor(object):
	"""The main entry point when using `libparsing` form Python. Subclass
	the processor and define parsing element handlers using the convention
	`on<ParsingElement's name`. For instance, if your grammar has a `NAME`
	symbol defined, then `onNAME` will be invoked with its match element.

	Note that symbol handlers (`onXXX` methods) take the `match` object
	as first argument as well as the named elements defined in the symbol,
	if it is a composite symbol (rule, group, etc). The named elements
	are the ones you declare using `_as`."""


	def __init__( self, grammar=None ):
		self.setGrammar(grammar)

	def setGrammar( self, grammar ):
		self.result       = None
		self.symbolByName = {}
		self.symbolByID   = {}
		self.handlerByID  = {}
		self.grammar      = grammar
		if grammar:
			self._bindSymbols(grammar)
			self._bindHandlers()

	def createGrammar( self ):
		return None

	def ensureGrammar( self ):
		if not self.grammar:
			self.setGrammar(self.createGrammar())
			assert self.grammar, "Processor has not grammar bound: {0}".format(self)
		return self.grammar

	def _bindSymbols( self, grammar ):
		"""Registers the symbols from the grammar into this processor. This
		will create a mapping from the symbol name and the symbol id to the
		symbol itself."""
		grammar.prepare()
		for name, symbol in grammar._symbols.items():
			# print ("SYMBOL#{0:4d}={1}".format(symbol.id, name))
			if symbol.id < 0:
				logging.warn("Unused symbol: %s" % (repr(symbol)))
				continue
			if symbol.id in self.symbolByID:
				raise Exception("Duplicate symbol id: %d, has %s already while trying to assign %s" % (symbol.id, self.symbolByID[symbol.id].name, symbol.name))
			self.symbolByID[symbol.id]     = symbol
			self.symbolByName[symbol.name] = symbol

	def _bindHandlers( self ):
		"""Discovers the handlers"""
		assert len(self.symbolByName) > 0, "{0}._bindHandlers: No symbols registered, got {1} symbol IDs from grammar {2}".format(self.__class__.__name__, len(self.symbolByID), self.grammar)
		for k in dir(self):
			if not k.startswith("on"): continue
			name = k[2:]
			if not name:
				continue
			if name not in self.symbolByName:
				logging.warn("Handler `{0}` does not match any of {1}".format(k, ", ".join(self.symbolByName.keys())))
			else:
				symbol   = self.symbolByName[name]
				handler  = getattr(self, k)
				callback = self._prepareHandler(handler)
				self.handlerByID[symbol.id] = callback

	def on( self, symbol, callback ):
		"""Binds a handler for the given symbol."""
		if not isinstance(symbol, ParsingElement):
			symbol = self.symbolByName[symbol]
		self.handlerByID[symbol.id] = self._prepareHandler(callback)
		return self

	def parse( self, text ):
		self.text   = text
		self.result = r = self.ensureGrammar().parseString(text)
		if r.isSuccess():
			return self.process(r.match)
		else:
			return None

	def process( self, match ):
		return self._defaultHandler(match)

	def _defaultHandler( self, match ):
		if isinstance(match, ParsingResult):
			match = match.match
		if isinstance(match, ReferenceMatch):
			result = [self.process(_) for _ in match]
			if result and (match.isOne() or match.isOptional()): result = result[0]
			match.value = result
			return result
		else:
			assert isinstance(match, Match), "Match expected, got: {0}".format(match)
			eid     = match.element.id
			handler = self.handlerByID.get(eid)
			if handler:
				# A handler was found, so we apply it to the match. The handler
				# returns a value that should be assigned to the match
				# print ("process[H]: applying handler", handler, "TO", match)
				result = match.value = handler( match )
				# print ("processed[H]: {0}#{1} : {2} --> {3}".format(match.__class__.__name__, match.name, repr(match.value), repr(result)))
			elif isinstance(match, GroupMatch):
				result = match.value = self.process(match[0])
			elif isinstance(match, CompositeMatch):
				result = match.value = [self.process(_) for _ in match]
			else:
				result = match.value
			return result

	def _prepareHandler( self, handler ):
		argnames = inspect.getargspec(handler).args
		# We want argnames to be anything after (self, match, ...) or (match, ...)
		if argnames[0] == "self":
			argnames = argnames[2:]
		else:
			argnames = argnames[1:]
		# def callback(match, handler=handler, argnames=argnames):
		# 	return self._applyHandler(handler, match, argnames)
		# return callback
		return lambda m:self._applyHandler(handler, m, argnames)

	def _applyHandler( self, handler, match, argnames ):
		"""Applies the given handler to the given match, returning the value
		produces but the handler."""
		# We skip self and match, which are required
		kwargs = dict((_.name,self.process(_)) for _ in match.children if _.name in argnames)
		try:
			result = handler(match, **kwargs)
			#print ("_applyHandler: {0}.value={1} --> {2}".format(match, repr(value), repr(result)))
			match.value = result
			return result
		except HandlerException as e:
			raise e
		except Exception as e:
			args                  = ["match"] + list(kwargs.keys())
			exc_type, exc_obj, tb = sys.exc_info()
			context               = traceback.format_exc().splitlines()
			res                   = HandlerException(e, kwargs, handler, context)
			logging.error(res)
			for _ in context: logging.warn(_)
			raise res


	# NOTE: This is the seed for a faster implementation, where we bypass
	# the wrapper.
	# def _defaultHandler( self, match ):
	# 	TokenMatch_group = LIB.symbols.TokenMatch_group
	# 	WordMatch_group  = LIB.symbols.WordMatch_group
	# 	def walk( match, step, matches ):
	# 		matches    = ctypes.cast(matches, ctypes.py_object).value
	# 		match      = ctypes.cast(match, C.TYPES["Match*"])
	# 		element    = ctypes.cast(match.contents.element, C.TYPES["ParsingElement*"])
	# 		match_type = LIB.symbols.Match_getElementType(match)
	# 		match_name = LIB.symbols.Match_getElementName(match)
	# 		if   match_type == TYPE_REFERENCE:
	# 			value = None
	# 		elif match_type == TYPE_RULE:
	# 			value = None
	# 		elif match_type == TYPE_GROUP:
	# 			value = None
	# 		elif match_type == TYPE_TOKEN:
	# 			value = TokenMatch_group(match,0)
	# 		elif match_type == TYPE_WORD:
	# 			value = WordMatch_group(match)
	# 		return step
	# 	callback  = C.TYPES["WalkingCallback"](walk)
	# 	context   = {"result":None}
	# 	c_context = ctypes.py_object(context)
	# 	LIB.symbols.Match__walk(match._cobjectPointer, callback, 0, c_context)
	# 	return context["result"]

# -----------------------------------------------------------------------------
#
# TREE WRITER
#
# -----------------------------------------------------------------------------

class TreeWriter(Processor):
	"""A special processor that outputs the named parsing elements
	registered in the parse tree. It is quite useful for debugging grammars."""

	def __init__( self, grammar=None, output=sys.stdout ):
		Processor.__init__(self, grammar)
		self.output = output
		self.reset()

	def reset( self ):
		self.indent = 0
		self.count  = 0

	def defaultProcess(self, match):
		self.output.write("{0:04d}|{1}{2}\n".format(self.count, self.indent * "│    "  + "├────" , match.name))
		self.indent += 1
		self.count  += 1
		r = Processor.defaultProcess(self, match)
		self.indent -= 1
		return r

# -----------------------------------------------------------------------------
#
# LIBPARSING LIBRARY
#
# -----------------------------------------------------------------------------

class Libparsing(CLibrary):
	"""Provides dedicated wrapping/unwrapping/caching functions for libparsing."""

	IsInitialized = False

	MATCH_TABLE = {
		TYPE_REFERENCE  : ReferenceMatch.Wrap,
		TYPE_WORD       : WordMatch.Wrap,
		TYPE_TOKEN      : TokenMatch.Wrap,
		TYPE_RULE       : RuleMatch.Wrap,
		TYPE_GROUP      : GroupMatch.Wrap,
		TYPE_CONDITION  : ConditionMatch.Wrap,
		TYPE_PROCEDURE  : ProcedureMatch.Wrap,
	}

	ELEMENT_TABLE = {
		TYPE_REFERENCE  : Reference.Wrap,
		TYPE_WORD       : Word.Wrap,
		TYPE_TOKEN      : Token.Wrap,
		TYPE_RULE       : Rule.Wrap,
		TYPE_GROUP      : Group.Wrap,
		TYPE_CONDITION  : Condition.Wrap,
		TYPE_PROCEDURE  : Procedure.Wrap,
	}

	DECLARES = """
	int Parsing_getPythonVersion():
	PyObject* Match_processPython( Match* match, PyObject* callback );
	"""

	@classmethod
	def Init( cls ):
		"""Initializes the types and structures defined in libparsing."""
		if cls.IsInitialized: return True
		# We pre-declare the types that are required by the structure declarations.
		# It's OK if they're void* instead of the actual structure definition.
		cls.IsInitialized = True

	def __init__( self, name="__libparsing"):
		self.__class__.Init()
		CLibrary.__init__(self, name)
		self.register(
			Reference,
			ParsingElement,
			Match,
			ParsingContext,
			ParsingResult,
			ParsingStats,
			Grammar,
			Word,      WordMatch,
			Token,     TokenMatch,
			Rule,      RuleMatch,
			Group,     GroupMatch,
			Condition, ConditionMatch,
			Procedure, ProcedureMatch,
		)
		# We dynamically register shorthand factory methods for parsing elements in
		# the Grammar.
		Grammar.Register(Word, Token, Group, Rule, Condition, Procedure)

	def wrap( self, value ):
		"""Wraps the given C value in corresponding Python values."""
		# NOTE: This function is called A LOT, so it needs to be fast.
		# We return None if it's a reference to a NULL pointer
		if isinstance(value, str) or isinstance(value, int): return value
		if not value: return None
		py_value      = value
		resolved_type = C.TYPES.get(type(value))
		if resolved_type:
			# FIXME: It might be better if we could directly get the pointer
			address = ctypes.addressof(value.contents)
			if address in C.COBJECTS:
				# The wrapper is in the cache, so we use it
				py_value = C.COBJECTS[address]
			elif resolved_type is TMatch:
				# Values are most likely to be matches, and we create
				# specific instances based on the element type
				if not value.contents or not value.contents.element:
					py_value = None
				else:
					element_type = value.contents.element.contents.type
					py_value     = self.MATCH_TABLE[element_type](value)
			elif resolved_type is TParsingElement:
				element_type = value.contents.type
				py_value = self.ELEMENT_TABLE[element_type](value)
			elif resolved_type is TReference:
				py_value    = Reference.Wrap(value)
			elif resolved_type in self.ctypeToCObject:
				cobject_class = self.ctypeToCObject[resolved_type]
				py_value = cobject_class.Wrap(value)
			else:
				# In this case, we have a pointer to a structure, so we return
				# the pointer content's in order to manipulate/access it.
				py_value = value.contents
		return py_value

LIB = LIB or Libparsing()

# EOF - vim: ts=4 sw=4 noet
