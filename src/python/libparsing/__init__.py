#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 18-Dec-2014
# Last modification : 22-Feb-2017
# -----------------------------------------------------------------------------

from __future__ import print_function

import sys, os, re, glob, inspect, tempfile, collections
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

VERSION            = "0.9.3"
LICENSE            = "http://ffctn.com/doc/licenses/bsd"
PACKAGE_PATH       = dirname(abspath(__file__))

MatchTuple = collections.namedtuple("MatchTuple", "offset length id element")

# -----------------------------------------------------------------------------
#
# FFI
#
# -----------------------------------------------------------------------------

ffi            = None
lib            = None
LIBPARSING_FFI = join(PACKAGE_PATH, "_libparsing.ffi") if os.path.exists(join(PACKAGE_PATH, "_libparsing.ffi")) else None
LIBPARSING_EXT = None
LIBPARSING_SO  = None
LIBRARY_EXTS   = ("so", "dylib", "dll")

# We check if there is a _libparsing SO/DYLIB/DLL file. If not, we need to
# build it using CFFI.
from . import _buildext
if len([_ for _ in LIBRARY_EXTS if os.path.exists(join(PACKAGE_PATH, _buildext.filename(_)))]) == 0:
	logging.info("Building native libparsing Python bindings‥")
	_buildext.build()

# Now we look for the actual Python extension (_libparsing
# We need to support different extensions and different prefixes. CFFI
# will build extensions as " _libparsing.cpython-35m-x86_64-linux-gnu.so"
# on Linux.
PREFIX_EXT = _buildext.name() + "."
PREFIX_SO  = "libparsing."
for p in os.listdir(PACKAGE_PATH):
	if p.startswith(PREFIX_EXT) and p.rsplit(".",1)[-1] in LIBRARY_EXTS:
		LIBPARSING_EXT = os.path.join(PACKAGE_PATH, p)
	if p.startswith(PREFIX_SO)  and p.rsplit(".",1)[-1] in LIBRARY_EXTS:
		LIBPARSING_SO  = os.path.join(PACKAGE_PATH, p)

if LIBPARSING_EXT:
	# Using the EXT instead of the SO (ie. API vs ABI mode) improves performance
	# by ~25%, but the extension needs to be compiled specifically for the python
	# version.
	import importlib
	libparsing_ext = importlib.import_module("libparsing." + _buildext.name())
	lib = libparsing_ext.lib
	ffi = libparsing_ext.ffi
elif LIBPARSING_SO:
	assert os.path.exists(LIBPARSING_FFI), "libparsing: Missing FFI interface file {0}".format(LIBPARSING_FFI)
	ffi = FFI()
	with open(LIBPARSING_FFI, "r") as f: ffi.cdef(f.read())
	lib = ffi.dlopen(LIBPARSING_SO)
assert lib, "libparsing: Cannot find libparsing.{{so,dll,dylib}} or _libparsing[.*].{{so,dll,dylib}} in package {0}".format(PACKAGE_PATH)

# -----------------------------------------------------------------------------
#
# GLOBALS
#
# -----------------------------------------------------------------------------

NOTHING            = re
CARDINALITY_OPTIONAL      = b'?'
CARDINALITY_ONE           = b'1'
CARDINALITY_MANY_OPTIONAL = b'*'
CARDINALITY_MANY          = b'+'
CARDINALITY_NOT_EMPTY     = b'='
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
ID_BINDING                = -1
ID_UNBOUND                = -10

if sys.version_info.major >= 3:
	def ensure_bytes(v):
		"""Makes sure that this returns a byte string."""
		return v.encode("utf8") if isinstance(v,str) else v
	def ensure_cstring(v):
		"""Makes sure this returns a string that can be passed to C (a bytes string)"""
		return v.encode("utf8") if isinstance(v,str) else v.decode("utf8").encode("utf8")
	def ensure_str(v):
		"""Ensures the result is a string."""
		return v.decode("utf8") if isinstance(v,bytes) else v
	def ensure_unicode(v):
		"""Ensures the result is an unicode string(str)"""
		return ensure_str(v)
	def ensure_string( v ):
		"""Ensures the result is the default unicode string type (str)"""
		return ensure_unicode(v)
	def is_string( v ):
		return isinstance(v,str) or isinstance(v,bytes)
else:
	def ensure_bytes( v ):
		"""Makes sure that this returns a byte string."""
		return v.encode("utf8") if isinstance(v,unicode) else v
	def ensure_cstring(v):
		"""Makes sure this returns a string that can be passed to C (an str)"""
		return v.encode("utf8") if isinstance(v,unicode) else v.decode("utf8").encode("utf8")
	def ensure_str( v ):
		"""Ensures the resulting is a str (Python 2)"""
		return v.encode("utf8") if isinstance(v,unicode) else v
	def ensure_unicode( v ):
		"""Ensures the result is a unicode string."""
		return v.decode("utf8") if isinstance(v,str) else v
	def ensure_string( v ):
		"""Ensures the result is the default unicode string type (unicode)"""
		return ensure_unicode(v)
	def is_string( v ):
		return isinstance(v,str) or isinstance(v,unicode)

# -----------------------------------------------------------------------------
#
# C OJBECT ABSTRACTION
#
# -----------------------------------------------------------------------------

class CObject(object):
	"""A wrapper to create an OO API on top of native C API using ctypes. A
	few things to keep in mind:

	- Values passed to C need to be explicitely referenced, otherwise they
	  will be garbage collected, sometimes even before they're passed
	  to the C API (it's the case with string).

	- In Python3, `str` need to be `bytes`.

	The CObject offers a *recycling* facility. If the `_RECYCLABLE` class
	attribute is set, the cbjects will be appended to the `_RECYCLER` class
	stack on `__del__`, and the instance can be reused by calling
	`Reuse(pointer)`.
	"""

	_TYPE       = None
	_RECYCLER   = None
	_RECYCLABLE = False

	@classmethod
	def Wrap( cls, cobject ):
		return cls(cobject, wrap=cls.TYPE()) if cobject != ffi.NULL else None

	@classmethod
	def Recycle( cls, wrapped ):
		if cls._RECYCLER is None: cls._RECYCLER = []
		wrapped._cobject = None
		cls._RECYCLER.append(wrapped)

	@classmethod
	def Reuse( cls, cobject ):
		if cls._RECYCLER is None or len(cls._RECYCLER) == 0:
			return None
		else:
			o = cls._RECYCLER.pop()
			return o._repurpose(ffi.cast(cls.TYPE(), cobject))

	@classmethod
	def TYPE( cls ):
		if not cls._TYPE:
			cls._TYPE = ffi.typeof(cls.__name__.rsplit(".")[-1] + "*")
		return cls._TYPE

	def __init__(self, *args, **kwargs):
		self._cobject = None
		self._init()
		if "wrap" in kwargs:
			assert len(kwargs) == 1
			assert len(args  ) == 1
			self._wrap(ffi.cast(kwargs["wrap"], args[0]))
		elif "empty" in kwargs:
			pass
		else:
			o = self._new(*args, **kwargs)
			if o is not None: self._cobject = ffi.cast(self.TYPE(), o)
			assert self._cobject

	def _init( self ):
		pass

	def _new( self ):
		raise NotImplementedError

	def _repurpose( self, cobject ):
		assert cobject
		return self._wrap(cobject)

	def _wrap( self, cobject ):
		assert self._cobject == None
		#assert isinstance(cobject, FFI.CData), "%s: Trying to wrap non CData value: %s" % (self.__class__.__name__, cobject)
		assert cobject != ffi.NULL, "%s: Trying to wrap NULL value: %s" % (self.__class__.__name__, cobject)
		self._cobject = cobject
		return self

	def __del__( self ):
		if self.__class__._RECYCLABLE:
			self.__class__.Recycle(self)

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
		name = self._cobject.name
		return ensure_str(ffi.string(name)) if name else None

	@name.setter
	def name( self, name ):
		self._name = ensure_bytes(name)
		lib.ParsingElement_name(self._cobject, self._name)
		return self

	@property
	def id( self ):
		return self._cobject.id

	@property
	def type( self ):
		return self._cobject.type

	@property
	def children( self ):
		child = self._cobject.children
		res   = []
		while child:
			ref = Reference.Wrap(child)
			yield ref
			child = ref._cobject.next

	def clear( self ):
		# FIXME: This does not work
		lib.ParsingElement_clear(self._cobject)
		return self

	def set( self, *children ):
		self.clear()
		return self.add(*children)

	def insert( self, index, *children ):
		for c in children:
			assert isinstance(c, ParsingElement) or isinstance(c, Reference)
			lib.ParsingElement_insert(self._cobject, index, lib.Reference_Ensure(c._cobject))
			index += 1
		return self

	def add( self, *children ):
		for c in children:
			assert isinstance(c, ParsingElement) or isinstance(c, Reference)
			lib.ParsingElement_add(self._cobject, lib.Reference_Ensure(c._cobject))
		return self

	def prepend( self, *children ):
		l = list(self.children)
		self.clear()
		self.add(*children)
		self.add(*l)
		return self

	def _as( self, name ):
		self._name = ensure_bytes(name)
		return Reference(self)._as(self._name)

	def optional( self ):
		return Reference(self).optional()

	def notEmpty( self ):
		return Reference(self).notEmpty()

	def zeroOrMore( self ):
		return Reference(self).zeroOrMore()

	def oneOrMore( self ):
		return Reference(self).oneOrMore()

	def disableMemoize( self ):
		return self

	def disableFailMemoize( self ):
		return self

	def skip( self, value=True ):
		# TODO: Implement me
		return self

	def noskip( self ):
		self.skip(False)
		return self

	def slots( self ):
		child = self._cobject.children
		res   = []
		while child:
			ref = Reference.Wrap(child)
			name = ref.name
			if name:
				res.append(name)
			child = ref._cobject.next
		return res

	def indexForKey( self, name ):
		child = self._cobject.children
		index = 0
		while child:
			ref = Reference.Wrap(child)
			if ref.name == name:
				return index
			else:
				index += 1
				child = ref._cobject.next
		return -1

	def __repr__(self):
		classname = self.__class__.__name__.rsplit(".", 1)[-1]
		if not self._cobject:
			return "<{0}:Uninitialized>".format(classname)
		else:
			return "<{0} {1}@{2}#{3}>".format(
				classname,
				ensure_str(self.type),
				ensure_str(self.name),
				self.id
			)

# -----------------------------------------------------------------------------
#
# WORD
#
# -----------------------------------------------------------------------------

class Word(ParsingElement):

	def _new( self, word):
		self._word = ensure_bytes(word)
		return lib.Word_new(self._word)

# -----------------------------------------------------------------------------
#
# TOKEN
#
# -----------------------------------------------------------------------------

class Token(ParsingElement):

	def _new( self, token):
		self._token = ensure_bytes(token)
		return lib.Token_new(self._token)

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
			return callback(ParsingElement.Wrap(e), ParsingContext.Wrap(ctx)) if callback else 1
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
			callback(ParsingElement.Wrap(e), ParsingContext.Wrap(ctx))
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
		self._element = element
		assert r.element == element._cobject, "Reference element should be {0}, got {1}".format(element._cobject, r.element)
		return r

	# =========================================================================
	# ACCESSORS
	# =========================================================================

	@property
	def name( self ):
		return ensure_str(ffi.string(self._cobject.name)) if self._cobject.name != ffi.NULL else None

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
		self._name = ensure_bytes(name)
		lib.Reference_name(self._cobject, self._name)
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

	def notEmpty( self ):
		lib.Reference_cardinality(self._cobject, CARDINALITY_NOT_EMPTY)
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
			ensure_str(self.name),
			self.element
		)

	def __del__( self ):
		super(self.__class__, self).__del__()
		# References are managed by the grammar, you should not create
		# them directly, so we don't need to free them either.
		pass

# -----------------------------------------------------------------------------
#
# MATCH
#
# -----------------------------------------------------------------------------

class Match(CObject):

	_TYPE       = ffi.typeof("Match*")
	_RECYCLABLE = False

	@classmethod
	def Wrap( cls, cobject ):
		assert cobject.element != ffi.NULL, "Match C object does not have an element: %s %d+%d" % (cobject.status, cobject.offset, cobject.length)
		return cls.Reuse(cobject) or Match(cobject, wrap=cls._TYPE)

	def _new( self, o ):
		return ffi.cast(self._TYPE, o)

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
	def line( self ):
		return self._cobject.line

	@property
	def type( self ):
		return lib.Match_getType(self._cobject)

	@property
	def name( self ):
		name = lib.Match_getElementName(self._cobject)
		return ensure_str(ffi.string(name)) if name else None

	@property
	def id( self ):
		return lib.Match_getElementID(self._cobject)

	@property
	def length( self ):
		return self._cobject.length

	@property
	def range( self ):
		o, l = self.offset or 0, self.length or 0
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

	def countChildren( self ):
		"""Returns the number of children."""
		count = 0
		child = self._cobject.children
		while child:
			child = child.next
			count += 1
		return count

	def _toHelper( self, callback ):
		(fd, fn) = tempfile.mkstemp()
		callback(self._cobject, fd)
		os.close(fd)
		with open(fn) as f:
			text = f.read()
		os.unlink(fn)
		return text

	def toJSON( self ):
		return self._toHelper(lib.Match_writeJSON)

	def toXML( self ):
		return self._toHelper(lib.Match_writeXML)

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
			# We correct the index
			if index < 0:
				index = self.countChildren() + index
			# We do a while iteration so that we don't wrap unncessary children
			i     = 0
			child = self._cobject.children
			while child:
				if i == index:
					return Match.Wrap(child)
				else:
					child = child.next
					i += 1
			raise KeyError("Cannot find item #{0} in {1}".format(index, self))
		else:
			# FIXME: It would be better to do Match_indexForKey(‥)
			i = self.indexForKey(index)
			if i >= 0:
				return self[i]
			else:
				raise KeyError("Cannot find item #{0} in {1}".format(index, self))

	def __repr__(self):
		if not self._cobject:
			return "<{0} NULL {1}>".format(
				self.__class__.__name__.rsplit(".", 1)[-1],
				id(self)
			)
		else:
			return "<{0} {1}:{2}@{3} {4}-{5}>".format(
				self.__class__.__name__.rsplit(".", 1)[-1],
				ensure_str(self.type),
				self.id,
				ensure_str(self.name) or "_",
				self.offset,
				self.offset + self.length,
			)

	def __del__( self ):
		super(self.__class__, self).__del__()
		# Matches are managed by ParsingResult, so we don't need to
		# free  them.
		pass

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

	_TYPE = ffi.typeof("ParsingContext*")

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
		lib.ParsingContext_setInt(self._cobject, ensure_cstring(key), value)
		return value

	def get( self, key ):
		return lib.ParsingContext_getInt(self._cobject, ensure_cstring(key))

	def __getitem__( self, offset ):
		return lib.ParsingContext_charAt(self._cobject, offset)

	def __del__( self ):
		super(self.__class__, self).__del__()
		# Parsing contexts are owned by parsing results, so we don't need
		# to free them
		pass

# -----------------------------------------------------------------------------
#
# PARSING RESULT
#
# -----------------------------------------------------------------------------

class ParsingResult(CObject):

	_TYPE = ffi.typeof("ParsingResult*")

	@classmethod
	def Wrap( cls, cobject, text=None, path=None, grammar=None, context=None ):
		res = super(ParsingResult, cls).Wrap(cobject)
		# NOTE: We keep refernces to the text, path, grammar and context,
		# in order for them not to be garbage-collected too early.
		if res:
			res._text    = text
			res._path    = path
			res._grammar = grammar
			res._context = context
		return res

	@property
	def status( self ):
		return self._cobject.status

	@property
	def match( self ):
		return Match.Wrap(self._cobject.match)

	@property
	def lastMatch( self ):
		return MatchTuple(
			offset  = self.lastMatchOffset,
			length  = self.lastMatchLength,
			id      = self.lastMatchElementID,
			element = self._grammar.symbol(self.lastMatchElementID) if self.lastMatchElementID != -1 else None,
		)

	@property
	def lastMatchOffset( self ):
		return self._cobject.context.lastMatchOffset

	@property
	def lastMatchLength( self ):
		return self._cobject.context.lastMatchLength

	@property
	def lastMatchElementID( self ):
		return self._cobject.context.lastMatchElementID

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
		return ensure_str(ffi.string(self._cobject.context.iterator.buffer))

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
		match = self.lastMatch
		if match:
			o = match.offset
			l = match.length
			return (o, o + l)
		else:
			return (self.textOffset, self.textOffset)

	def getContext( self, start=None, end=None, before=3, after=3 ):
		"""Returns a triple `(before:[Line], current:Line, after:[Line])`
		around the start/end offsets"""
		if start is None or end is None:
			start, end = self.lastMatchRange()
		s    = start
		e    = end
		t    = ensure_str(self.text)
		bt   = t[0:s].rsplit("\n", before + 1)[-before-1:]
		at   = t[e:].split("\n", after + 1)[:after+1]
		c    = bt[-1] + t[s:e] + at[0]
		return dict(
			before=bt[:-1],
			line=c,
			after=at[1:],
			start=start,
			end=end,
			lineBefore=bt[-1],
			lineMatch=t[s:e],
			lineAfter=at[0],
			lineOffset=len(bt[-1]),
			lineLength=max(0,e-s),
		)

	def _asSpaces( self, line, char=" " ):
		r = []
		for c in line:
			r.append(c if c in "\t" else char)
		return "".join(r)

	def formatContext( self, context ):
		red    = '[0m[01;31m'
		yellow = '[0m[01;33m'
		orange = '[0m[00;33m'
		reset  = '[0m[00;00m'
		before = "\n│ " + "\n│ ".join(context["before"])
		after  = "\n│ " + "\n│ ".join(context["after"])
		line   = "\n└┐" + yellow + context["line"] + reset
		error  = "\n┌┘" + (
			orange +
			self._asSpaces(context["lineBefore"], "▸")     +
			red +
			self._asSpaces(context["lineMatch"],  "▲") +
			reset +
			self._asSpaces(context["lineAfter"])
		)
		return "".join([before,line,error,after])

	def describe( self, context=3, color=True ):
		"""Returns a nicely formatted description of the error"""
		if self.isSuccess():
			return "Parsing successful"
		else:
			# m     = self.lastMatch
			# s,e   = self.lastMatchRange ()
			# l     = m.line
			# print ("LAST MATCH {0} line={1}, start={2}-{3}".format(m,l,s,e))
			m     = self.lastMatch
			s,e   = self.lastMatchRange ()
			t     = self.formatContext(self.getContext(before=context, after=context))
			lines = self.text[:s].split("\n")
			line  = len(lines) - 1
			char  = len(lines[-1])
			sym   = ", symbol " + str(self._grammar.symbol(m.id)) if m and m.id and m.id >= 0 else ""
			return "Parsing failed at line {0} character {1}, offset {2}→{3}{4}:{5}".format(
				line, char, s, e,
				sym,
				"\n".join([_ for _ in t.split("\n")])
			)

	def toJSON( self ):
		return self.match.toJSON()

	def toXML( self ):
		return self.match.toXML()

	def __repr__( self ):
		return "<{0}(status={2}, line={3}, char={4}, offset={5}, remaining={6}) at {1:02x}>".format(
			self.__class__.__name__,
			id(self),
			self.status, self.line, -1, self.offset, 0
		)

	def __del__( self ):
		super(self.__class__, self).__del__()
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

	_TYPE = ffi.typeof("Grammar*")

	def _new(self, name=None, isVerbose=False ):
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
		_path = ensure_cstring(ensure_unicode(path))
		return ParsingResult.Wrap(lib.Grammar_parsePath(self._cobject, _path), path=(path, _path), grammar=self)

	def parseStream( self, stream ):
		return self.parseString(stream.read())

	def parseString( self, text ):
		self._prepare()
		_text = ensure_cstring(ensure_unicode(text))
		return ParsingResult.Wrap(lib.Grammar_parseString(self._cobject,_text), text=(text, _text), grammar=self)

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

	@property
	def isVerbose( self ):
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
		super(self.__class__, self).__del__()
		# The parsing result is the only one we really need to free
		# along with the grammar
		lib.Grammar_free(self._cobject)

# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------

class Processor:

	LAZY  = 0
	EAGER = 1

	def __init__( self, grammar=None, strict=True ):
		self.depth    = 0
		self._handler = None
		self.isStrict = strict
		self.strategy = self.LAZY
		self.setGrammar(self.ensureGrammar(grammar))
		self._defaults  = dict( (k,getattr(self,v) if hasattr(self,v) else None)  for (k,v) in {
			TYPE_WORD       : "processWord",
			TYPE_TOKEN      : "processToken",
			TYPE_GROUP      : "processGroup",
			TYPE_RULE       : "processRule",
			TYPE_CONDITION  : "processCondition",
			TYPE_PROCEDURE  : "processProcedure",
		}.items())

	def asEager( self ):
		self.strategy = self.EAGER
		return self

	def asLazy( self ):
		self.strategy = self.LAZY
		return self

	def ensureGrammar( self, grammar ):
		return grammar or self.createGrammar()

	def createGrammar( self ):
		raise NotImplementedError

	def setGrammar( self, grammar ):
		self.symbols      = grammar.list() if grammar else []
		self.symbolByName = {}
		self.symbolByID   = {}
		self.handlerByID  = {}
		self.grammar      = grammar
		if self.grammar:
			# We prepare the grammar
			self.grammar.prepare()
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
					raise Exception("Duplicate symbol id: %d, has %s already while trying to assign %s" % (s.id, self.symbolByID[s.id].name, s.name))
				elif self.isStrict:
					logging.warn("Unused symbol: %s" % (repr(s)))
			self.symbolByID[s.id] = s

	def _bindHandlers( self ):
		for k in dir(self):
			if not k.startswith("on"): continue
			name = k[2:]
			if not name:
				continue
			assert not self.isStrict or name in self.symbolByName, "Handler does not match any symbol: {0}, symbols are {1}".format(k, ", ".join(self.symbolByName.keys()))
			symbol = self.symbolByName.get(name)
			if symbol:
				self.handlerByID[symbol.id] = self._createHandler( getattr(self, k), symbol )

	def _createHandler( self, handler, symbol ):
		kwargs = {}
		# We only bind the arguments listed
		sig  = inspect.getargspec(handler)
		params = sig.args[0:-len(sig.defaults)] if sig.defaults else sig.args
		params  = params[1:] if params[0] == "self" else params
		slots   = tuple((_, symbol.indexForKey(_)) for _ in params[1:] )
		missing = tuple(_ for _ in slots if _[1] <  0)
		valid   = tuple(_ for _ in slots if _[1] >= 0)
		if missing:
			raise Exception("Handler {0} for {1} arguments do not match grammar: {2} should be a subset of {3}".format(handler, symbol, missing, symbol.slots()))
		elif valid:
			def wrapper( match ):
				kwargs = dict( (name, self.process(match[index])) for (name,index) in valid)
				return self.postProcess(match, handler(match, **kwargs))
			return wrapper
		else:
			return handler

	def process( self, match ):
		self.depth += 1
		match  = match.match if isinstance(match, ParsingResult) else match
		result = self._processMatch(match) if isinstance(match, Match) else match
		self.depth -= 1
		return result.value if isinstance(result, MatchResult) else result

	def postProcess( self, match, result ):
		return result

	def _processMatch( self, match ):
		if self.strategy == self.EAGER:
			return self._processEager(match)
		else:
			return self._processLazy(match)

	def _processEager( self, match, handler=True, default=True ):
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
		h = self.handlerByID.get(i) if handler else (self._defaults.get(t) if default else None)
		r = h(MatchResult(r,match)) if h else r
		return r.value if isinstance(r, MatchResult) else r

	def _processLazy( self, match ):
		"""Processes a match element."""
		t = match.type
		i = match.id
		r = None
		h = self.handlerByID.get(i)
		if not h or self._handler == h:
			# If there's no handler defined,then we apply the eager method. We only
			# use the default handler if there is no current handler matching the element
			return self._processEager(match, handler=False, default=not h)
		else:
			# If there is a handler defined
			ph = self._handler
			self._handler = h
			if t == TYPE_WORD or t == TYPE_TOKEN or t == TYPE_CONDITION or t == TYPE_PROCEDURE:
				res = h(match)
			else:
				res = h(match)
			self._handler = ph
			return res

	def _processWord( self, match ):
		return ensure_unicode(ffi.string(lib.WordMatch_group(match._cobject)))

	def _processToken( self, match ):
		n = lib.TokenMatch_count(match._cobject)
		if n == 0:
			return None
		else:
			return list(ensure_unicode(ffi.string(lib.TokenMatch_group(match._cobject, i))) for i in range(n))

	def _processCondition( self, match ):
		return True

	def _processProcedure( self, match ):
		return True

	def _processGroup( self, match ):
		# NOTE: We need to wrap this in a list so that proces(match[0]) work
		# for groups.
		return [self._processMatch(match[0])]

	def _processRule( self, match ):
		return list(self._processMatch(_) for _ in match)

	def _processReference( self, match ):
		if not lib.Reference_IsMany(match.element):
			res = self._processMatch(match[0]) if match.hasChildren() else None
			return res
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
			self.output.write(u"{0:04d}|{1}{2}\n".format(self.count, self.indent * "    "  + "|---" , match.element().name()))
			self.indent += 1
		self.count  += 1
		r = AbstractProcessor.defaultProcess(self, match)
		if named:
			self.indent -= 1
		return r

class Indentation(object):

	VALUES = {
		" "  : 1,
		"\t" : 4,
	}

	@classmethod
	def Indent( self, element, context ):
		indent = context.get("indent") or 0
		context.set("indent", indent + 1)

	@classmethod
	def Dedent( self, element, context ):
		indent = context.get("indent") or 0
		context.set("indent", indent - 1)

	@classmethod
	def CheckIndent( self, element, context, min=False ):
		indent = context.get("indent") or 0
		o      = context.offset or 0
		so     = max(o - indent, 0)
		eo     = o
		tabs   = 0
		# This is a fix
		if so == eo and so > 0:
			so = eo
		for i in range(so, eo):
			if context[i] == b"\t":
				tabs += 1
		return tabs == indent

	def __init__( self, allows="\t ", step=1, values=None):
		self.allows = allows
		self.values = values
		self.step   = step

	def withTabs( self ):
		self.allows = "\t"
		self.values = {"\t":1}
		self.step   = 1


def __init__():
	pass

# EOF - vim: ts=4 sw=4 noet
