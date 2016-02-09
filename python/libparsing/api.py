#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : libparsing (Python bindings)
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2016-01-21
# Last modification : 2016-02-09
# -----------------------------------------------------------------------------

from __future__ import print_function
import sys, traceback
from   libparsing.bindings import *
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
			child_cvalue  = child_cvalue.contents.next
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
		res._mustFree = True
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

	def __repr__( self ):
		return "<Word#{1}:{0}=`{2}` at {3}>".format(self.name, self.id, self._getWord(), hex(id(self)))

class Token(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Token_new(const char* expr);
	void Token_free(ParsingElement* this);
	void Token_print(ParsingElement* this); // @as _print
	const char* Token_expr(ParsingElement* this);  // @as _getExpr
	"""

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
		self.callback = None

	def _new( self, callback ):
		self.callback = (callback, C.TYPES["ConditionCallback"](callback))
		return ParsingElement._new(self, self.callback[1])

	def __repr__( self ):
		return "<Condition#{1}:{0}={2} at {3}>".format(self.name, self.id, self.callback[0], hex(id(self)))

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
		self.callback = None

	def _new( self, callback ):
		self.callback = (callback, C.TYPES["ProcedureCallback"](callback))
		return ParsingElement._new(self, self.callback[1])

	def __repr__( self ):
		return "<Procedure#{1}:{0}={2} at {3}>".format(self.name, self.id, self.callback[0], hex(id(self)))

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
		return "<Rule#{1}:{0}=[2] at {3}>".format(self.name, self.id, len(list(self)), hex(id(self)))

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
	void Match_free(Match* this);
	int Match__walk(Match* this, WalkingCallback callback, int step, void* context );
	"""

	def _init( self ):
		self._value = NOTHING

	def group( self, index=0 ):
		raise NotImplementedError("{0}.group not() implemented".format(self.__class__.__name__))

	def _extractValue( self ):
		raise NotImplementedError("{0}._extractValue() not implemented".format(self.__class__.__name__))

	@property
	def children( self ):
		return ()

	@property
	def name( self ):
		"""The name of the reference."""
		print ("MATCH NAME", self, ":", self.element.name)
		return self.element.name

	@property
	def value( self ):
		"""Value is an accessor around this Match's value, which can
		be transformed by a match processor. By default, there is no value."""
		if self._value != NOTHING:
			return self._value
		else:
			return self._extractValue()

	@value.setter
	def value( self, value ):
		"""Sets the value in this specific match."""
		self._value = value
		return self

	def range( self ):
		"""Returns the range (start, end) of the match."""
		return (self.offset, self.offset + self.length)

	def isReference( self ):
		"""A utility shorthand to know if a match is a reference."""
		return self.getType() == TYPE_REFERENCE

	def text( self ):
		s,e = self.range()
		return self.context.text()[s:e]

	def __repr__( self ):
		element = self.element
		return "<{0}:{1}#{2}({3}):{4}+{5}>".format(self.__class__.__name__, element.type, element.id, element.name or "_", self.offset, self.length)

# -----------------------------------------------------------------------------
#
# COMPOSITE MATCH
#
# -----------------------------------------------------------------------------

class CompositeMatch(Match):

	@caccessor
	def children(self):
		"""Returns the children of this ParsingElement as a tuple."""
		child_cvalue  = self._cobject.child
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
	def element( self ):
		return self.LIBRARY.wrap(ctypes.cast(self._cobject.element, C.TYPES["Reference*"]))

	@property
	def name( self ):
		"""The name of the reference."""
		return self.element.name

	@property
	def cardinality( self ):
		return self.element.cardinality

	def _extractValue( self ):
		if self.isOne() or self.isOptional():
			return self.child.value if self.child is not None else None
		else:
			return [_.value for _ in self.children]

	# def group( self, index=0 ):
	# 	if self.child is None:
	# 		return None
	# 	elif self.isOne():
	# 		return self.child.group(0)
	# 	else:
	# 		return self.getChild(index).group()

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
		return "<{0}:{1}#{2}:{3}{4}@{5}>".format(self.__class__.__name__, self.element.type, self.element.id, self.element.name, self.cardinality, hex(id(self)))

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
		return self._group()

	def group( self, index=0 ):
		"""Returns the word matched"""
		if index != 0: raise IndexError
		assert index == 0
		element = ctypes.cast(self._cobject.element,   C.TYPES["ParsingElement*"])
		config  = ctypes.cast(element.config, C.TYPES["WordConfig*"])
		return config.contents.word

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

	def _extractValue( self ):
		return self._group(0)

	def group( self, index=0 ):
		return self._group(index)

	def groups( self ):
		element = ctypes.cast(self._cobject.element, C.TYPES["ParsingElement*"]).contents
		match   = ctypes.cast(self._cobject.data,    C.TYPES["TokenMatch*"]).contents
		return [self.group(i) for i in range(match.count)]

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
	char*  ParsingContext_text(ParsingContext* this);
	"""

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
	bool   ParsingResult_isComplete(ParsingResult* this); // @as _isComplete
	int    ParsingResult_textOffset(ParsingResult* this); // @as _textOffset
	size_t ParsingResult_remaining(ParsingResult* this);
	"""

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

	def isComplete( self ):
		return True if self._isComplete() != 0 else False

	def isPartial( self ):
		return True if self._isPartial() != 0 else False

	def lastMatchRange( self ):
		o = self.context.stats.matchOffset
		r = self.context.stats.matchLength
		return (o, o + r)

	# def textAround( self, line=None ):
	# 	if line is None: line = self.line
	# 	i = self.offset
	# 	t = self.text
	# 	while i > 1 and t[i] != "\n": i -= 1
	# 	if i != 0: i += 1
	# 	return t[i:(i+100)].split("\n")[0]

	def textAround( self ):
		# We should get the offset range covered by the iterator's buffer
		o = self.offset - self.textOffset
		t = self.text
		s = o
		e = o
		while s > 0      and t[s] != "\n": s -= 1
		while e < len(t) and t[e] != "\n": e += 1
		l = t[s:e]
		i = " " * (o - s - 1) + "^"
		return l + "\n" + i

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
	ParsingResult* Grammar_parseString( Grammar* this, const char* text );
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

	#def __del__( self ):
	#	if self._mustFree:
	#		self.free()

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

class Processor(object):
	"""The main entry point when using `libparsing` form Python. Subclass
	the processor and define parsing element handlers using the convention
	`on<ParsingElement's name`. For instance, if your grammar has a `NAME`
	symbol defined, then `onNAME` will be invoked with its match element.

	Note that symbol handlers (`onXXX` methods) take the `match` object
	as first argument as well as the named elements defined in the symbol,
	if it is a composite symbol (rule, group, etc). The named elements
	are the ones you declare using `_as`."""

	def __init__( self, grammar ):
		assert isinstance(grammar, Grammar)
		self.symbolByName = {}
		self.symbolByID   = {}
		self.handlerByID  = {}
		self.grammar      = grammar
		self._bindSymbols(grammar)
		self._bindHandlers()

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
				symbol = self.symbolByName[name]
				self.handlerByID[symbol.id] = getattr(self, k)

	def on( self, symbol, callback ):
		"""Binds a handler for the given symbol."""
		if not isinstance(symbol, ParsingElement):
			symbol = self.symbolByName[symbol]
		self.handlerByID[symbol.id] = callback
		return self

	def process( self, match ):
		"""The main entry point to processing a match."""
		if isinstance(match, ParsingResult):
			match = match.match
		if isinstance(match, ReferenceMatch):
			return self._processReferenceMatch(match)
		elif isinstance(match, Match):
			return self._processParsingElementMatch(match)
		else:
			# Match is in that case a value that we pass as-is
			return match

	def processChildren( self, match ):
		return [self.process(_) for _ in match.children]

	def _processParsingElementMatch( self, match ):
		"""Processes the given match, applying the matching handlers when found."""
		if not match: return None
		assert not isinstance(match, ReferenceMatch), "{0}.process: match expected not to be reference match, got {1}".format(self.__class__.__name__, match)
		# We retrieve the element's id
		eid     = match.element.id
		# We retrieve the handler for
		handler = self.handlerByID.get(eid)
		if handler:
			# A handler was found, so we apply it to the match. The handler
			# returns a value that should be assigned to the match
			# print ("process[H]: applying handler", handler, "TO", match)
			result = self._applyHandler( handler, match )
			# print ("processed[H]: {0}#{1} : {2} --> {3}".format(match.__class__.__name__, match.name, repr(match.value), repr(result)))
			if result is not None:
				match.value = result
			return result or match.value
		else:
			return self.defaultProcess(match)

	def defaultProcess( self, match ):
		assert not isinstance(match, ReferenceMatch), "defaultProcess expected a ParsingElementMatch, not a ReferenceMatch: {0}".format(match)
		if isinstance(match, GroupMatch):
			result = match.value = self._processReferenceMatch(match.child)
		elif isinstance(match, CompositeMatch):
			result = match.value = [self._processReferenceMatch(_) for _ in match.children]
		else:
			result = match.value
		# print ("processed[*]: {0}#{1} : {2} --> {3}".format(match.__class__.__name__, match.name, repr(match.value), repr(result)))
		return result

	def _processReferenceMatch( self, match ):
		"""Processes the reference match."""
		assert isinstance(match, ReferenceMatch)
		if match.isOne() or match.isOptional():
			result = self.process(match.child)
		else:
			result  = [self.process(_) for _ in match.children]
		# print ("_processReferenceMatch: {0}[{1}]#{2}({3}) : {4} -> {5}".format(match.__class__.__name__, match.element.type, match.element.name, match.cardinality, repr(match.value), repr(result)))
		match.value = result
		return result

	def _applyHandler( self, handler, match ):
		"""Applies the given handler to the given match, returning the value
		produces but the handler."""
		# We only bind the arguments listed
		fcode    = handler.func_code
		argnames = fcode.co_varnames[0:fcode.co_argcount]
		# We want argnames to be anything after (self, match, ...) or (match, ...)
		if argnames[0] == "self":
			argnames = argnames[2:]
		else:
			argnames = argnames[1:]
		# We skip self and match, which are required
		kwargs   = dict((_,None) for _ in argnames if _ not in ("self", "match"))
		for m in match.children:
			k = m.name
			assert isinstance(m, ReferenceMatch)
			if k and k in argnames:
				kwargs[k] = self.process(m)
		try:
			value  = match.value
			result = handler(match, **kwargs)
			# print ("_applyHandler: {0}#{1} : {2} --> {3}".format(match.__class__.__name__, match.name, repr(value), repr(result)))
			match.result = result
			return result
		except HandlerException as e:
			raise e
		except Exception as e:
			args = ["match"] + list(kwargs.keys())
			exc_type, exc_obj, tb = sys.exc_info()
			context = traceback.format_exc().splitlines()
			raise HandlerException(e, kwargs, handler, context)

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

	@classmethod
	def Init( cls ):
		"""Initializes the types and structures defined in libparsing."""
		if cls.IsInitialized: return True
		# We pre-declare the types that are required by the structure declarations.
		# It's OK if they're void* instead of the actual structure definition.
		cls.IsInitialized = True

	def __init__( self, name="_libparsing"):
		self.__class__.Init()
		CLibrary.__init__(self, name)
		self.register(
			Reference,
			ParsingElement,
			Match,
			ParsingContext,
			ParsingResult,
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
				element_type = value.contents.element.contents.type
				if element_type == TYPE_REFERENCE:   py_value = ReferenceMatch.Wrap(value)
				elif element_type == TYPE_WORD:      py_value = WordMatch.Wrap(value)
				elif element_type == TYPE_TOKEN:     py_value = TokenMatch.Wrap(value)
				elif element_type == TYPE_RULE:      py_value = RuleMatch.Wrap(value)
				elif element_type == TYPE_GROUP:     py_value = GroupMatch.Wrap(value)
				elif element_type == TYPE_CONDITION: py_value = ConditionMatch.Wrap(value)
				elif element_type == TYPE_PROCEDURE: py_value = ProcedureMatch.Wrap(value)
				else: raise ValueError("Match type not supported yet: {0}".format(element_type))
			elif resolved_type is TParsingElement:
				element_type = value.contents.type
				if element_type == TYPE_REFERENCE:   py_value = Reference.Wrap(value)
				elif element_type == TYPE_WORD:      py_value = Word.Wrap(value)
				elif element_type == TYPE_TOKEN:     py_value = Token.Wrap(value)
				elif element_type == TYPE_RULE:      py_value = Rule.Wrap(value)
				elif element_type == TYPE_GROUP:     py_value = Group.Wrap(value)
				elif element_type == TYPE_CONDITION: py_value = Condition.Wrap(value)
				elif element_type == TYPE_PROCEDURE: py_value = Procedure.Wrap(value)
				else: raise ValueError("ParsingElement type not supported yet: {0} from {1}".format(element_type, wrapped))
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

# EOF - vim: ts=4 sw=4 noet
