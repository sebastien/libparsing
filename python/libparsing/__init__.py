#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : libparsing (Python bindings)
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2016-01-21
# Last modification : 2016-02-02
# -----------------------------------------------------------------------------

from __future__ import print_function

VERSION = "0.0.0"
LICENSE = "http://ffctn.com/doc/licenses/bsd"

import ctypes, os, re, sys, traceback

try:
	import reporter as logging
except ImportError as e:
	import logging

NOTHING = ctypes
C_API   = None

# NOTE: This ctypes implementation is noticeably longer than the corresponding
# CFII equivalent, while also being prone to random segfaults, which need
# to be investigated (memory management).

# NOTE: ctypes and Python3 is a little bit tricky regarding string types. In
# particular, str have to be converted to bytes.
# SEE <http://stackoverflow.com/questions/23852311/different-behaviour-of-ctypes-c-char-p>


# -----------------------------------------------------------------------------
#
# DEFINES/LIBRARY
#
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
#
# C INTERFACE
#
# -----------------------------------------------------------------------------

class C:
	"""An interface/helper to the `ctypes` module. The `C.TYPES` mapping maps
	C type names to their corresponding `ctypes` type declaration. In addition
	to smart unwrapping functions, this library also offers functions to
	parse simple C structure and prototype definitions.
	"""

	RE_AS = re.compile("@as\s+([_\w]+)\s*$")

	TYPES = {
		"void"            : None,
		"bool"            : ctypes.c_byte,
		"char"            : ctypes.c_char,
		"void*"           : ctypes.c_void_p,
		"char*"           : ctypes.c_char_p,
		"const char*"     : ctypes.c_char_p,
		"const char**"    : ctypes.POINTER(ctypes.c_char_p),
		"int"             : ctypes.c_int,
		"float"           : ctypes.c_float,
		"double"          : ctypes.c_double,
		"size_t"          : ctypes.c_size_t,
		"size_t*"         : ctypes.POINTER(ctypes.c_size_t),
	}

	# NOTE: Unwrap and UnwrapCast is highly specific to this library, and
	# should probably be moved in the init.

	@classmethod
	def String( cls, value ):
		"""Ensures that the given value is a CString"""
		return value.encode("utf-8") if isinstance(value, str) else value

	@classmethod
	def Unwrap( cls, value ):
		# CObjectWrapper might be garbage collected at this time
		if CObjectWrapper and isinstance(value, CObjectWrapper):
			return value._wrapped
		if not CObjectWrapper and hasattr( value, "_wrapped"):
			return value._wrapped
		if isinstance(value, str):
			print ("UNWRAPPING", (value, cls.String(value)))
			return cls.String(value)
		else:
			return value

	@classmethod
	def UnwrapCast( cls, value, type ):
		value = cls.Unwrap(value)
		if issubclass(value.__class__, type):
			return value
		# The cast does not always work
		#elif issubclass(value, ctypes.pointer):
		#	return ctypes.cast(value, type)
		#else:
		return value

	@classmethod
	def ParseStructure( cls, text ):
		"""Parses a structure definition, ie. the body of a C `struct {}`
		declaration. This requires all the referenced types to be defined
		in the `C.TYPES` mapping."""
		res = []
		for line in text.split("\n"):
			line = line.split(";",1)[0]
			line = [_.strip() for _ in line.split()]
			line = [_ for _ in line if _ and _ != "struct"]
			if not line: continue
			name = line[-1]
			type = " ".join(line[0:-1])
			if "->" in type:
				# We handle function pointers
				type = type.split("->")
				type = ctypes.CFUNCTYPE(*[cls.TYPES[_] for _ in type if _ != "void"])
			else:
				# Otherwise it's just a regular type
				type = cls.TYPES[type]
			res.append((name, type))
		return res

	@classmethod
	def BindStructure( cls, ctypeClass ):
		"""Parses the given `ctypes.Structure` subclass's `STRUCTURE` attribute and assign
		it to its `_fields_` property."""
		assert issubclass(ctypeClass, ctypes.Structure)
		ctypeClass._fields_ = cls.ParseStructure(ctypeClass.STRUCTURE)

	@classmethod
	def Register( cls, *ctypeClasses ):
		"""Registers the given `ctypes.Structure` subclasses in this
		C interface. This will update the `C.TYPES` map with pointer types
		to the given structure."""
		types = {}
		for _ in ctypeClasses:
			assert issubclass(_, ctypes.Structure)
			# And we register, possibly overriding the already
			# registered type.
			c_name = _.__name__.rsplit(".", 1)[-1]
			assert c_name.startswith("T"), c_name
			c_name = c_name[1:] + "*"
			types[c_name]       = ctypes.POINTER(_)
			types[c_name + "*"] = ctypes.POINTER(types[c_name])
			# It's important to update the type directly here
			# print ("C:Register: type {0} from {1}".format(c_name, _))
			cls.TYPES[c_name]       = types[c_name]
			cls.TYPES[c_name + "*"] = types[c_name + "*"]
		for _ in ctypeClasses:
			# We bind the fields of the structure as a separate iteration, so
			# as to ensure that the types are already available.
			cls.BindStructure(_)
		return types

	@classmethod
	def GetType( cls, name, selfType=None ):
		if name == "this*":
			return ctypes.POINTER(selfType)
		else:
			return cls.TYPES[name]

	@classmethod
	def ParsePrototype( cls, prototype, selfType=None ):
		"""Parses a function prototype, returning `(name, argument ctypes, return ctype)`"""
		# print "C:Parsing prototype", prototype
		as_name   = cls.RE_AS.search(prototype)
		prototype = prototype.replace(" *", "* ")
		prototype = prototype.replace("struct ", "")
		prototype = prototype.split("//",1)[0].split(";",1)[0]
		ret_name, params = prototype.split("(", 1)
		params           = params.rsplit(")",1)[0]
		ret, name        = (_.strip() for _ in ret_name.strip().rsplit(" ", 1))
		params           = [_.strip().rsplit(" ", 1) for _ in params.split(",",) if _.strip()]
		# We convert the type, preserving its name and its original type name
		params           = [(cls.GetType(_[0], selfType),_[1],_[0]) for _ in params if _ != ["void"]]
		return ([name,as_name.group(1) if as_name else None] , params, [cls.GetType(ret, selfType), None, ret])

	@classmethod
	def ParsePrototypes( cls, declarations, selfType=None ):
		for line in (declarations or "").split("\n"):
			line = line.replace("\t", " ").strip()
			if not line: continue
			proto = cls.ParsePrototype(line, selfType)
			yield proto

	@classmethod
	def LoadFunctions( cls, symbols, declarations, selfType=None ):
		"""Retrieves typed versions of the given declarations from the given
		library symbols, as a list of `(func, proto)` couples."""
		res = []
		for proto in cls.ParsePrototypes(declarations, selfType):
			name, argtypes, restype = proto
			name, alias             = name
			# print ("C:Loading function {0} with {1} -> {2}".format( name, argtypes, restype))
			# NOTE: Something to now about `ctypes` is that you cannot mutate
			# the argtypes/restype of the symbol. Instead, you refer to it,
			# change it and assign the result. I assume it's because ctypes
			# often returns new ephemeral instances upon native object access.
			func          = symbols[name]
			func.argtypes = argtypes = [_[0] for _ in argtypes]
			func.restype  = restype  = restype[0]
			# print ("C:Loaded {0} with {1} → {2}".format(name, argtypes, restype))
			assert func.argtypes == argtypes, "ctypes: argtypes do not match {0} != {1}".format(func.argtypes, argtypes)
			assert func.restype  == restype , "ctypes: restype does not match {0} != {1}".format(func.restype , restype)
			res.append((func, proto))
		return res

# -----------------------------------------------------------------------------
#
# C LIBRARY
#
# -----------------------------------------------------------------------------

class CLibrary:
	"""A abstraction of a C library loaded with `ctypes`, in which
	`CObjectWrapper` subclasses register themselves."""

	WRAPS = []
	PATHS   = [
		".",
		__file__,
		os.path.join(__file__, ".."),
		os.path.join(__file__, "..", ".."),
		"/usr/local/lib",
		"/usr/lib",
		"/lib",
	]
	PREFIX = [""]
	EXT    = ["", ".so", ".ld", ".dyld"]

	# FROM: http://goodcode.io/articles/python-dict-object/
	class Symbols(object):
		def __init__(self, d=None):
			self.__dict__ = d or {}
		def __iter__( self ):
			for v in self.__dict__.values():
				yield v

	@classmethod
	def Find( cls, name ):
		"""Tries to find a library with the given name."""
		for path in cls.PATHS:
			path = os.path.abspath(path)
			for ext in cls.EXT:
				p = os.path.join(path, name + ext)
				for prefix in cls.PREFIX:
					pp = prefix + p
					if os.path.exists(pp) and not os.path.isdir(pp):
						return pp
		return None

	@classmethod
	def Load( cls, name ):
		return ctypes.cdll.LoadLibrary(cls.Find(name))

	def __init__( self, path ):
		self._cdll    = self.Load(path)
		self.symbols  = CLibrary.Symbols()
		self._wraps   = [] + self.WRAPS

	def register( self, *wrapperClasses ):
		"""Register the given `CObjectWrapper` in this library, loading the
		corresponding functions and binding them to the class."""
		for _ in wrapperClasses:
			_.LIBRARY = self
			assert issubclass(_, CObjectWrapper)
			# We load the functions from the library
			functions = C.LoadFunctions(self._cdll, _.GetFunctions(), _.WRAPPED)
			for func, proto in functions:
				name = proto[0][0]
				# print ("L:Library: binding symbol {0} with {1} → {2}".format(name, func.argtypes, func.restype))
				self.symbols.__dict__[name] = func
			# We bind the functions declared in the wrapper
			_.BindFunctions(functions)
			_.BindFields()
			if _.WRAPPED:
				self._wraps.append((
					ctypes.POINTER(_.WRAPPED),
					_.Wrap
				))
		return self

	def wrap( self, cValue ):
		"""Passes the given value through this library's `_wraps` filter
		list, processing the first filter bound to a matching type."""
		for t,f in self._wraps:
			if isinstance(cValue, t): return f(cValue)
		# NOTE: If POINTER(..) had a parent class, we could test it, but this
		# should work in the meantime. In essence, we want to return a reference
		# to the structure as opposed to a pointer to it.
		if not isinstance(cValue, CObjectWrapper) and hasattr(cValue, "contents"):
			cValue = cValue.contents
		return cValue

	def unwrap( self, value):
		return C.Unwrap(value)

	def unwrapCast( self, value, type ):
		return C.UnwrapCast(value, type)

# -----------------------------------------------------------------------------
#
# OBJECT WRAPPER
#
# -----------------------------------------------------------------------------

class CObjectWrapper(object):
	"""The CObjectWrapper class wrap pointers to `ctypes.Structure` objects
	(ie. abstractions of underlying C structures) in an object-oriented API. This
	class seamlessly integrates with the `Library` class to dynamically load
	and type functions from the underlying C library and manage the
	conversion of values to and from C types."""

	WRAPPED   = None
	FUNCTIONS = None
	LIBRARY   = None
	ACCESSORS = None

	@classmethod
	def GetFunctions( cls ):
		res = []
		for _ in cls.__bases__:
			if hasattr(_, "GetFunctions"):
				f = _.GetFunctions()
				if f: res.append(f)
		if cls.FUNCTIONS: res.append(cls.FUNCTIONS)
		return "\n".join(res)

	@classmethod
	def BindFields( cls ):
		"""Binds the fields in this wrapped object."""
		if cls.WRAPPED:
			cls.ACCESSORS = {}
			for name, type in cls.WRAPPED._fields_:
				accessor = cls._CreateAccessor(name, type)
				assert name not in cls.ACCESSORS, "Accessor registered twice: {0}".format(name)
				cls.ACCESSORS[name] = accessor
				if not hasattr(cls, name):
					setattr(cls, name, accessor)

	@classmethod
	def _CreateAccessor( cls, name, type ):
		"""Returns an accessor for the given field from a `ctypes.Structure._fields_`
		definition."""
		c = C
		def getter( self ):
			value = getattr(self._wrapped.contents, name)
			# print "g: ", cls.__name__ + "." + name, type, "=", value
			# We manage string decoding here
			if isinstance(value, bytes): value = value.decode("utf-8")
			return self.LIBRARY.wrap(value)
		def setter( self, value ):
			# This is required for Python3
			if isinstance(value, str): value = value.encode("utf-8")
			value = self.LIBRARY.unwrapCast(value, type)
			# print "s: ", cls.__name__ + "." + name, type, "<=", value
			return setattr(self._wrapped.contents, name, value)
		return property(getter, setter)

	@classmethod
	def BindFunctions( cls, functions ):
		"""Invoked by the library when the Wrapper is registered. Will update
		the class with definition of methods declared in the `FUNCTIONS`
		class property."""
		res = []
		for f, proto in functions:
			res.append(cls.BindFunction(f, proto))
		return res

	@classmethod
	def _CreateFunction( cls, ctypesFunction, proto):
		c = C
		assert proto[2][2] != "this*", "Function cannot return this"
		is_constructor = proto[0][0].endswith("_new")
		def function(cls, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			u_args = [cls.LIBRARY.unwrap(_) for _ in args]
			print ("F: ", proto[0], args, "→", u_args, ":", ctypesFunction.argtypes, "→", ctypesFunction.restype)
			res  = ctypesFunction(*u_args)
			if not is_constructor:
				# Non-constructors must wrap the result
				res  = cls.LIBRARY.wrap(res)
			print ("F=>", res)
			return res
		return function

	@classmethod
	def _CreateMethod( cls, ctypesFunction, proto):
		c = C
		returns_this = proto[2][2] == "this*"
		def method(self, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			# print "M: ", proto[0], args
			args = [self.LIBRARY.unwrap(self)] + [self.LIBRARY.unwrap(_) for _ in args]
			assert args[0], "CObjectWrapper: method {0} `this` is None in {1}".format(proto[0], self)
			try:
				res  = ctypesFunction(*args)
			except ctypes.ArgumentError as e:
				raise ValueError("{1} failed with {2}: {3}".format(cls.__name__, proto[0][0], args, e))
			res  = self if returns_this else self.LIBRARY.wrap(res)
			# print "M=>", res
			return res
		return method

	@classmethod
	def BindFunction( cls, ctypesFunction, proto ):
		class_name = cls.__name__.rsplit(".",1)[-1]
		# We need to keep a reference to C as otherwise it might
		# be freed before we invoke self.LIBRARY.unwrap.
		method    = None
		is_method = len(proto[1]) >= 1 and proto[1][0][1] == "this"
		if is_method:
			method = cls._CreateMethod(ctypesFunction, proto)
		else:
			method = cls._CreateFunction(ctypesFunction, proto)
		# We assume the convention is <Classname>_methodName, but in practice
		# Classname could be the name of a super class.
		#assert proto[0].startswith(class_name + "_"), "Prototype does not start with class name: {0} != {1}".format(proto[0], class_name)
		name = proto[0][1] or proto[0][0].split("_", 1)[1]
		# If we're not binding a method, we bind it as a static method
		if name == "new":
			# Any method called "new" will be bound as the constructor
			assert not is_method
			name   = "_constructor"
			method = classmethod(method)
		elif not is_method:
			assert proto[0][0][0].upper() == proto[0][0][0], "Class functions must start be CamelCase: {0}".format(proto[0][0])
			method = classmethod(method)
		# print ("O:{1} bound as {3} {0}.{2}".format(cls.__name__, proto[0][0], name, "method" if is_method else "function"))
		setattr(cls, name, method)
		assert hasattr(cls, name)
		return (name, method)

	@classmethod
	def Wrap( cls, wrapped ):
		"""Wraps the given object in this CObjectWrapper. The given
		object must be a ctypes value, usually a pointer to a struct."""
		return cls( wrappedCObject=wrapped )

	@classmethod
	def _Create( cls, *args ):
		return cls._constructor(*args)

	def __init__( self, *args, **kwargs ):
		self._wrapped = None
		self._init()
		if "wrappedCObject" in kwargs:
			self._wrap(kwargs["wrappedCObject"])
		else:
			self._new(*args, **kwargs)

	def _wrap( self, wrapped ):
		assert not self._wrapped
		self._wrapped = wrapped
		assert isinstance(self._wrapped, ctypes.POINTER(self.WRAPPED))
		assert self._wrapped != None, "{0}(wrappedCObject): wrappedCObject expected, got: {1}".format(self.__class__.__name__, self._wrapped)
		self._mustFree = False

	def _new( self, *args, **kwargs ):
		# We ensure that the _wrapped value returned by the creator is
		# unwrapped. In fact, we might want to implement a special case
		# for new that returns directly an unwrapped value.
		instance       = self.__class__._Create(*args)
		assert isinstance( instance, ctypes.POINTER(self.WRAPPED)), "{0}(): {1} pointer expected, got {2}".format(self.__class__.__name__, self.WRAPPED, instance)
		assert not self._wrapped
		assert instance != None, "{0}(): created instance seems to have no value: {1}".format(self.__class__.__name__, self._wrapped)
		self._wrapped  = instance
		self._mustFree = True

	def _init ( self ):
		pass

	# FIXME: We experience many problems with destructors, ie. segfaults in GC.
	# This needs to be sorted out.
	# def __del__( self ):
	# 	if self._wrapped and self._mustFree:
	# 		# FIXME: There are some issues with the __DEL__ when other stuff is not available
	# 		if hasattr(self, "free") and getattr(self, "free"):
	# 			print ("FREEING", self)
	# 			self.free(self._wrapped)

# -----------------------------------------------------------------------------
#
# C STRUCTURES
#
# -----------------------------------------------------------------------------

# {{{
# The `T*` types are `ctypes.Structure` subclasses that wrap the structures
# defined in the `libparsing` C API. They are not meant to be directly
# instanciated or referenced, but are to be obtained and manipulated through
# a `Libparsing` instance.
# }}}

class TElement(ctypes.Structure):

	STRUCTURE = """
	char           type;
	int            id;
	"""

class TParsingElement(ctypes.Structure):

	STRUCTURE = """
	char           type;
	int            id;
	const char*    name;       // The parsing element's name, for debugging
	void*          config;     // The configuration of the parsing element
	struct Reference*     children;   // The parsing element's children, if any
	ParsingElement*->ParsingContext*->Match* recognize;
	ParsingElement*->ParsingContext*->Match*->Match* process;
	Match*->void freeMatch;
	"""


class TWordConfig(ctypes.Structure):

	STRUCTURE = """
	const char* word;
	size_t      length;
	"""

class TTokenConfig(ctypes.Structure):

	STRUCTURE = """
	const char* expr;
	void*       regexp;
	void*       extra;
	"""

class TReference(ctypes.Structure):

	STRUCTURE = """
	char            type;            // Set to Reference_T, to disambiguate with ParsingElement
	int             id;              // The ID, assigned by the grammar, as the relative distance to the axiom
	char            cardinality;     // Either ONE (default), OPTIONAL, MANY or MANY_OPTIONAL
	const char*     name;            // The name of the reference (optional)
	ParsingElement* element;         // The reference to the parsing element
	Reference*      next;            // The next child reference in the parsing elements
	"""

	def __init__( self, *args, **kwargs ):
		ctypes.Structure.__init__(*args, **kwargs)

class TMatch(ctypes.Structure):

	STRUCTURE = """
	char            status;     // The status of the match (see STATUS_XXX)
	size_t          offset;     // The offset of `iterated_t` matched
	size_t          length;     // The number of `iterated_t` matched
	Element*        element;
	ParsingContext* context;
	void*           data;      // The matched data (usually a subset of the input stream)
	Match*          next;      // A pointer to the next  match (see `References`)
	Match*          child;     // A pointer to the child match (see `References`)
	"""

class TTokenMatch(ctypes.Structure):

	STRUCTURE = """
	int             count;
	const char**    groups;
	"""

class TIterator(ctypes.Structure):

	STRUCTURE = """
	char           status;    // The status of the iterator, one of STATUS_{INIT|PROCESSING|INPUT_ENDED|ENDED}
	char*          buffer;    // The buffer to the read data, note how it is a (void*) and not an `iterated_t`
	iterated_t*    current;   // The for the current offset within the buffer
	iterated_t     separator; // The character for line separator
	size_t         offset;    // Offset in input (in bytes), might be different from `current - buffer` if some input was freed.
	size_t         lines;     // Counter for lines that have been encountered
	size_t         capacity;  // Content capacity (in bytes), might be bigger than the data acquired from the input
	size_t         available; // Available data in buffer (in bytes), always `<= capacity`
	bool           freeBuffer;
	void*          input;     // Pointer to the input source
	IteratorCallback move;
	"""

class TParsingContext(ctypes.Structure):

	STRUCTURE = """
	struct Grammar*       grammar;      // The grammar used to parse
	struct Iterator*      iterator;     // Iterator on the input data
	struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
	struct ParsingOffset* current;      // The current parsing offset
	struct ParsingStats*  stats;
	"""

class TParsingResult(ctypes.Structure):

	STRUCTURE = """
	char            status;
	Match*          match;
	ParsingContext* context;
	"""

class TParsingStats(ctypes.Structure):

	STRUCTURE = """
	size_t  bytesRead;
	double  parseTime;
	size_t  symbolsCount;
	size_t* successBySymbol;
	size_t* failureBySymbol;
	size_t   failureOffset;   // A reference to the deepest failure
	size_t   matchOffset;
	size_t   matchLength;
	Element* failureElement;  // A reference to the failure element
	"""

class TParsingContext(ctypes.Structure):

	STRUCTURE = """
	struct Grammar*              grammar;      // The grammar used to parse
	struct Iterator*             iterator;     // Iterator on the input data
	struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
	struct ParsingOffset* current;      // The current parsing offset
	struct ParsingStats*  stats;
	"""

class TGrammar(ctypes.Structure):

	STRUCTURE = """
	ParsingElement*  axiom;       // The axiom
	ParsingElement*  skip;        // The skipped element
	int              axiomCount;  // The count of parsing elemetns in axiom
	int              skipCount;   // The count of parsing elements in skip
	Element**        elements;    // The set of all elements in the grammar
	bool             isVerbose;
	"""

# -----------------------------------------------------------------------------
#
# PARSING ELEMENTS
#
# -----------------------------------------------------------------------------

class ParsingElement(CObjectWrapper):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	this* ParsingElement_name( ParsingElement* this, const char* name ); // @as setName
	void  ParsingElement_free(ParsingElement* this);
	"""

	@classmethod
	def Wrap( cls, wrapped ):
		"""This classmethod acts as a factory to produce specialized instances
		of `ParsingElement` subclasses based on the element's type."""
		# We return None if it's a reference to a NULL pointer
		if not wrapped: return None
		# Otherwise we access the type and return new specific instances
		element_type = wrapped.contents.type
		if element_type == TYPE_REFERENCE:
			return Reference(wrappedCObject=wrapped)
		elif element_type == TYPE_WORD:
			return Word(wrappedCObject=wrapped)
		elif element_type == TYPE_TOKEN:
			return Token(wrappedCObject=wrapped)
		elif element_type == TYPE_RULE:
			return Rule(wrappedCObject=wrapped)
		elif element_type == TYPE_GROUP:
			return Group(wrappedCObject=wrapped)
		else:
			raise ValueError

	@property
	def name( self ):
		return self._wrapped.contents.name

	@name.setter
	def name( self, value ):
		self._name = C.Unwrap(value)
		self._wrapped.contents.name = self._name
		return self

	def _as( self, name ):
		"""Returns a new Reference wrapping this parsing element."""
		ref = Reference(element=self, name=name)
		return ref

	def one( self ):
		return Reference(element=self, cardinality=CARDINALITY_ONE)

	def optional( self ):
		return Reference(element=self, cardinality=CARDINALITY_OPTIONAL)

	def zeroOrMore( self ):
		return Reference(element=self, cardinality=CARDINALITY_MANY_OPTIONAL)

	def oneOrMore( self ):
		return Reference(element=self, cardinality=CARDINALITY_MANY)

	def __div__( self, a ):
		return self._as(name)

class Reference(CObjectWrapper):

	WRAPPED   = TReference

	FUNCTIONS = """
	Reference* Reference_Ensure(void* element); // @as _Ensure
	Reference* Reference_FromElement(ParsingElement* element); // @as _FromElement
	Reference* Reference_new(void);
	void       Reference_free(Reference* this);
	Reference* Reference_cardinality(Reference* this, char cardinality); // @as setCardinality
	Reference* Reference_name(Reference* this, const char* name); // @as setName
	bool       Reference_hasElement(Reference* this);
	bool       Reference_hasNext(Reference* this);
	"""

	@classmethod
	def Ensure( cls, element ):
		if isinstance( element, ParsingElement):
			return cls.FromElement(element)
		else:
			assert isinstance(element, Reference)
			return element

	@classmethod
	def FromElement( cls, element ):
		assert isinstance( element, ParsingElement)
		res = cls._FromElement(element)
		assert isinstance(res, Reference), "Expected reference, got: {0}".format(res)
		res._mustFree = True
		return res

	def _new( self, element=None, name=None, cardinality=NOTHING ):
		CObjectWrapper._new(self)
		self.element = element
		self.name    = name
		if cardinality in (CARDINALITY_ONE, CARDINALITY_OPTIONAL, CARDINALITY_MANY_OPTIONAL, CARDINALITY_MANY):
			self.cardinality = cardinality

	def one( self ):
		self._wrapped.cardinality = CARDINALITY_ONE
		return self

	def optional( self ):
		self._wrapped.cardinality = CARDINALITY_OPTIONAL
		return self

	def zeroOrMore( self ):
		self._wrapped.cardinality = CARDINALITY_MANY_OPTIONAL
		return self

	def oneOrMore( self ):
		self._wrapped.cardinality = CARDINALITY_MANY
		return self

	def _as( self, name ):
		self.name = name
		return self

class Word(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Word_new(const char* word);
	void Word_free(ParsingElement* this);
	void Word_print(ParsingElement* this); // @as _print
	const char* Word_word(ParsingElement* this);  // @as _getWord
	"""

	def _new( self, word ):
		self.word = C.String(word)
		ParsingElement._new(self, word)

class Token(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Token_new(const char* expr);
	void Token_free(ParsingElement* this);
	void Token_print(ParsingElement* this); // @as _print
	const char* Token_expr(ParsingElement* this);  // @as _getExpr
	"""

	def _new( self, expr ):
		self.expr = C.String(expr)
		print ("NEW TOKEN", self.expr)
		ParsingElement._new(self, self.expr)
		assert self._getExpr() == self.expr
		print ("EXPR", self._getExpr())

class Condition(ParsingElement):
	FUNCTIONS = """
	ParsingElement* Condition_new(ConditionCallback c);
	"""

	def _new( self, callback ):
		callback = C.TYPES["ConditionCallback"](callback)
		return ParsingElement._new(self, callback)

class Procedure(ParsingElement):
	FUNCTIONS = """
	ParsingElement* Procedure_new(ProcedureCallback c);
	"""

	def _new( self, callback ):
		callback = C.TYPES["ProcedureCallback"](callback)
		ParsingElement._new(self, callback)

# -----------------------------------------------------------------------------
#
# COMPOSITE PARSING ELEMENTS
#
# -----------------------------------------------------------------------------

class CompositeElement(ParsingElement):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	this* ParsingElement_add(ParsingElement* this, Reference* child); // @as _add
	this* ParsingElement_clear(ParsingElement* this);
	"""

	# NOTE: This is an attempt at memory management
	# def _init( self ):
	# 	self._children = []

	def _new(self, *args):
		ParsingElement._new(self, None)
		for _ in args:
			self.add(_)

	def add( self, *references ):
		# argument = reference
		for i, reference in enumerate(references):
			assert reference, "{0}.add: no reference given, got {1} as argument #{2}".format(self.__class__.__name__, reference, i)
			assert isinstance(reference, ParsingElement) or isinstance(reference, Reference), "{0}.add: Expected ParsingElement or Reference, got {1} as argument #{2}".format(self.__class__, reference, i)
			reference = Reference.Ensure(reference)
			assert isinstance(reference, Reference)
			self._add(reference)
			# self._children.append((reference, argument))
			assert self.children
		return self

	def set( self, *references ):
		self.clear()
		self.add(*references)
		return self

class Rule(CompositeElement):

	# FIXME: No free method here
	FUNCTIONS = """
	ParsingElement* Rule_new(void* children);
	"""

class Group(CompositeElement):

	# FIXME: No free method here
	FUNCTIONS = """
	ParsingElement* Group_new(void* children);
	"""

# -----------------------------------------------------------------------------
#
# MATCH OBJECTS
#
# -----------------------------------------------------------------------------

class Match(CObjectWrapper):

	WRAPPED   = TMatch
	FUNCTIONS = """
	bool Match_isSuccess(Match* this);
	int Match_getOffset(Match* this);
	int Match_getLength(Match* this);
	void Match_free(Match* this);
	int Match__walk(Match* this, WalkingCallback callback, int step, void* context );
	"""

	@classmethod
	def Wrap( cls, wrapped ):
		"""This classmethod acts as a factory to produce specialized instances
		of `Match` subclasses based on the match's element's type."""
		# We return None if it's a reference to a NULL pointer
		if not wrapped: return None
		# Otherwise we access the type and return new specific instances
		element_type = wrapped.contents.element.contents.type
		if element_type == TYPE_REFERENCE:
			return ReferenceMatch(wrappedCObject=wrapped)
		elif element_type == TYPE_WORD:
			return WordMatch(wrappedCObject=wrapped)
		elif element_type == TYPE_TOKEN:
			return TokenMatch(wrappedCObject=wrapped)
		elif element_type == TYPE_RULE:
			return RuleMatch(wrappedCObject=wrapped)
		elif element_type == TYPE_GROUP:
			return GroupMatch(wrappedCObject=wrapped)
		elif element_type == TYPE_CONDITION:
			return ConditionMatch(wrappedCObject=wrapped)
		elif element_type == TYPE_PROCEDURE:
			return ProcedureMatch(wrappedCObject=wrapped)
		else:
			raise ValueError("Unsupported match type: {0}".format(element_type))

	def _init( self ):
		self._value_ = NOTHING

	def group( self, index=0 ):
		raise NotImplementedError

	def _value( self ):
		raise NotImplementedError

	def children( self ):
		for _ in []: yield _

	@property
	def element( self ):
		"""the parsing element wrapped by the reference"""
		assert not isinstance(self, ReferenceMatch)
		return ctypes.cast(self._wrapped.contents.element, C.TYPES["ParsingElement*"]).contents

	@property
	def name( self ):
		"""The name of the reference."""
		return ctypes.cast(self._wrapped.contents.element, C.TYPES["ParsingElement*"]).contents.name

	@property
	def value( self ):
		"""Value is an accessor around this Match's value, which can
		be transformed by a match processor."""
		if self._value_ != NOTHING:
			return self._value_
		else:
			return self._value()

	@value.setter
	def value( self, value ):
		"""Sets the value in this specific match."""
		self._value_ = value
		return self

	def range( self ):
		"""Returns the range (start, end) of the match."""
		return (self.offset, self.offset + self.length)

	def isReference( self ):
		"""A utility shorthand to know if a match is a reference."""
		return self.getType() == TYPE_REFERENCE

	def __repr__( self ):
		element = ctypes.cast(self._wrapped.contents.element, C.TYPES["ParsingElement*"]).contents
		return "<{0}:{1}#{2}({3}):{4}+{5}>".format(self.__class__.__name__, element.type, element.id, element.name, self.offset, self.length)

class CompositeMatch(Match):

	def group( self, index=0 ):
		return self.getChild(index).group()

	def children( self ):
		"""Iterates throught the children of this composite match."""
		child = self.child
		while child:
			assert isinstance(child, Match)
			yield child
			child = child.next

	def getChild( self, index=0 ):
		for i,_ in enumerate(self.children()):
			if i == index:
				return _
		return None

	def get( self, name=NOTHING ):
		if name is NOTHING:
			return dict((_.name, _) for _ in self.children() if _.name)
		else:
			for _ in self.children():
				if _.name == name:
					return _
			# We don't throw an index error
			return None
			# raise IndexError

	def __iter__( self ):
		for _ in self.children():
			yield _

	def __getitem__( self, index ):
		if isinstance(index, str):
			return self.get(index)
		else:
			return self.getChild(index)

	def __len__( self ):
		return len(list(self.children()))

class ReferenceMatch(CompositeMatch):

	@property
	def reference( self ):
		"""The reference wrapping the parsing element."""
		# if not self._reference:
		# 	self._reference = ctypes.cast(self._wrapped.contents.element, C.TYPES["Reference*"]).contents
		# print "REFERENENCE", self._reference
		# return self._reference
		return ctypes.cast(self._wrapped.contents.element, C.TYPES["Reference*"]).contents

	@property
	def element( self ):
		"""the parsing element wrapped by the reference"""
		#return c.unwrapcast(self.reference().element, c.types["ParsingElement*"]).contents
		return ctypes.cast(self.reference.element, C.TYPES["ParsingElement*"]).contents

	@property
	def name( self ):
		"""The name of the reference."""
		return self.reference.name

	def _value( self ):
		if self.isOne() or self.isOptional():
			return self.child.value
		else:
			return [_.value for _ in self.children()]

	def group( self, index=0 ):
		if self.isOne():
			return self.child.group(0)
		else:
			return self.getChild(index).group()

	def groups( self ):
		return [_.group() for _ in self]

	@property
	def cardinality( self ):
		return self.reference.cardinality

	def isOne( self ):
		return self.cardinality == CARDINALITY_ONE

	def isOptional( self ):
		return self.cardinality == CARDINALITY_OPTIONAL

	def isZeroOrMore( self ):
		return self.cardinality == CARDINALITY_MANY_OPTIONAL

	def isOneOrMore( self ):
		return self.cardinality == CARDINALITY_MANY

	def __repr__( self ):
		return "<{0}:{1}#{2}({3})*{4}>".format(self.__class__.__name__, self.element.type, self.element.id, self.element.name, self.cardinality)

class WordMatch(Match):

	FUNCTIONS = """
	const char* WordMatch_group(Match* this); // @as _group
	"""

	def _value( self ):
		return self._group()

	def group( self, index=0 ):
		"""Returns the word matched"""
		if index != 0: raise IndexError
		assert index == 0
		element = ctypes.cast(self._wrapped.contents.element,   C.TYPES["ParsingElement*"])
		config  = ctypes.cast(element.contents.config, C.TYPES["WordConfig*"])
		return config.contents.word

class TokenMatch(Match):

	FUNCTIONS = """
	const char* TokenMatch_group(Match* this, int index); // @as _group
	int TokenMatch_count(Match* this);
	"""

	def _value( self ):
		return self._group(0)

	def group( self, index=0 ):
		return self._group(index)

	def groups( self ):
		element = ctypes.cast(self._wrapped.contents.element, C.TYPES["ParsingElement*"]).contents
		match   = ctypes.cast(self._wrapped.contents.data,    C.TYPES["TokenMatch*"]).contents
		return [self.group(i) for i in range(match.count)]

class ProcedureMatch(Match):

	def _value( self ):
		return True

class ConditionMatch(Match):

	def _value( self ):
		return True

class RuleMatch(CompositeMatch):

	def _value( self ):
		return [_.value for _ in self.children()]

class GroupMatch(CompositeMatch):

	def _value( self ):
		c = list(self.children())
		assert len(c) <= 1
		return c[0].value

# -----------------------------------------------------------------------------
#
# PARSING RESULTS
#
# -----------------------------------------------------------------------------

class ParsingResult(CObjectWrapper):

	WRAPPED   = TParsingResult
	FUNCTIONS = """
	void  ParsingResult_free(ParsingResult* this);
	bool  ParsingResult_isFailure(ParsingResult* this);
	bool  ParsingResult_isPartial(ParsingResult* this);
	bool  ParsingResult_isSuccess(ParsingResult* this);
	bool  ParsingResult_isComplete(ParsingResult* this);
	int   ParsingResult_textOffset(ParsingResult* this); // @as _textOffset
	"""

	@property
	def line( self ):
		return self.context.iterator.contents.lines

	@property
	def offset( self ):
		return self.context.iterator.contents.offset

	@property
	def text( self ):
		return self.context.iterator.contents.buffer

	@property
	def textOffset( self ):
		return self._textOffset()

	def lastMatchRange( self ):
		o = self.context.stats.contents.matchOffset
		r = self.context.stats.contents.matchLength
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

	# def __del__( self ):
	# 	if self._mustFree:
	# 		self.free()

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

class Grammar(CObjectWrapper):

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

	def _new( self, isVerbose=False, axiom=None ):
		CObjectWrapper._new(self)
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
			return match

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
		assert not isinstance(match, ReferenceMatch)
		if isinstance(match, GroupMatch):
			result = match.value = self._processReferenceMatch(match.child)
		elif isinstance(match, CompositeMatch):
			result = match.value = [self._processReferenceMatch(_) for _ in match.children()]
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
			result  = [self.process(_) for _ in match.children()]
		# print ("_processReferenceMatch: {0}[{1}]#{2}({3}) : {4} -> {5}".format(match.__class__.__name__, match.element.type, match.element.name, match.cardinality, repr(match.value), repr(result)))
		match.value = result
		return result

	def _applyHandler( self, handler, match ):
		"""Applies the given handler to the given match, returning the value
		produces but the handler."""
		# We only bind the arguments listed
		fcode    = handler.func_code
		argnames = fcode.co_varnames[0:fcode.co_argcount]
		assert argnames[0] == "self"
		assert argnames[1] == "match"
		# We skip self and match, which are required
		kwargs   = dict((_,None) for _ in argnames if _ not in ("self", "match"))
		for m in match.children():
			k = m.name
			assert isinstance(m, ReferenceMatch)
			if k and k in argnames:
				kwargs[k] = self._processReferenceMatch(m)
		try:
			value  = match.value
			result = handler(match, **kwargs)
			# print ("_applyHandler: {0}#{1} : {2} --> {3}".format(match.__class__.__name__, match.name, repr(value), repr(result)))
			match.result = result
			return result
		except TypeError as e:
			args = ["match"] + list(kwargs.keys())
			raise Exception(str(e) + " -- arguments of {2}: {0}, given {1}".format(",".join([str(_) for _ in args]), kwargs, handler))
		except Exception as e:
			raise e.__class__("in {2}({3}): {4}".format(e.__class__.__name__, self.__class__.__name__, handler, match, e))

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
# MODULE INITIALIZATION
#
# -----------------------------------------------------------------------------

# We pre-declare the types that are required by the structure declarations.
# It's OK if they're void* instead of the actual structure definition.
C.TYPES.update({
	"iterated_t"        : ctypes.c_char,
	"iterated_t*"       : ctypes.c_char_p,
	"Iterator*"         : ctypes.c_void_p,
	"Element*"          : ctypes.c_void_p,
	"Element**"         : ctypes.POINTER(ctypes.c_void_p),
	"ParsingContext*"   : ctypes.c_void_p,
	"ParsingOffset*"    : ctypes.c_void_p,
	"IteratorCallback"  : ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.POINTER(TIterator), ctypes.c_int),
	"WalkingCallback"   : ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p),
	"ConditionCallback" : ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.POINTER(TParsingElement), ctypes.POINTER(TParsingContext)),
	"ProcedureCallback" : ctypes.CFUNCTYPE(None, ctypes.POINTER(TParsingElement), ctypes.POINTER(TParsingContext)),
})

# We register structure definitions that we want to be accessible
# through C types
C.Register(
	TElement,
	TParsingElement,
	TReference,
	TWordConfig,
	TTokenMatch,
	TTokenConfig,
	TMatch,
	TIterator,
	TParsingContext,
	TParsingStats,
	TParsingResult,
	TGrammar,
)

# Now we load the C API and register the CObjectWrapper, which
# will enrich the ctypes library with typing, while ensuring that
# the prototypes that we have are working. The C_API will now be
# a flat interface to the native C library, but all the registered
# CObjectWrapper subclasses will now offer an object-oriented wrapper.
C_API = CLibrary(
	"_libparsing"
).register(
	Reference,
	Match,
	ParsingResult,
	Grammar,
	Word,      WordMatch,
	Token,     TokenMatch,
	Rule,      #RuleMatch,
	Group,     #GroupMatch,
	Condition, #ConditionMatch,
	Procedure, #ConditionMatch,
)

# We dynamically register shorthand factory methods for parsing elements in
# the Grammar.
Grammar.Register(Word, Token, Group, Rule, Condition, Procedure)

# NOTE: Useful for debugging
# for k in sorted(C.TYPES.keys()):
# 	print "C.TYPES[{0}] = {1}".format(k, C.TYPES[k])

# EOF - vim: ts=4 sw=4 noet
