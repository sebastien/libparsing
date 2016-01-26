#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : libparsing (Python bindings)
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2016-01-21
# Last modification : 2016-01-26
# -----------------------------------------------------------------------------

VERSION = "0.0.0"
LICENSE = "http://ffctn.com/doc/licenses/bsd"

import ctypes, os, re

NOTHING = ctypes
C_API   = None


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
	def Unwrap( cls, value ):
		# CObjectWrapper might be garbage collected at this time
		if CObjectWrapper and isinstance(value, CObjectWrapper):
			return value._wrapped
		if not CObjectWrapper and hasattr( value, "_wrapped"):
			return value._wrapped
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
	EXT = ["", ".so", ".ld", ".dyld"]

	# FROM: http://goodcode.io/articles/python-dict-object/
	class Symbols(object):
		def __init__(self, d=None):
			self.__dict__ = d or {}

	@classmethod
	def Find( cls, name ):
		"""Tries to find a library with the given name."""
		for path in cls.PATHS:
			path = os.path.abspath(path)
			for ext in cls.EXT:
				p = os.path.join(path, name + ext)
				if os.path.exists(p):
					return p
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
			for name, type in cls.WRAPPED._fields_:
				accessor = cls._CreateAccessor(name, type)
				setattr(cls, name, accessor)

	@classmethod
	def _CreateAccessor( cls, name, type ):
		"""Returns an accessor for the given field from a `ctypes.Structure._fields_`
		definition."""
		c = C
		def getter( self ):
			value = getattr(self._wrapped.contents, name)
			# print "g: ", cls.__name__ + "." + name, type, "=", value
			return self.LIBRARY.wrap(value)
		def setter( self, value ):
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
			# print "F: ", proto[0], args
			args = [cls.LIBRARY.unwrap(_) for _ in args]
			res  = ctypesFunction(*args)
			if not is_constructor:
				# Non-constructors must wrap the result
				res  = cls.LIBRARY.wrap(res)
			# print "F=>", res
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
		print self, args, kwargs
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

class TParsingContext(ctypes.Structure):

	STRUCTURE = """
	struct Grammar*       grammar;      // The grammar used to parse
	struct Iterator*      iterator;     // Iterator on the input data
	struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
	struct ParsingOffset* current;      // The current parsing offset
	struct ParsingStats*  stats;
	"""

class TParsingStats(ctypes.Structure):

	STRUCTURE = """
	size_t  bytesRead;
	double  parseTime;
	size_t  symbolsCount;
	size_t* successBySymbol;
	size_t* failureBySymbol;
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

class Reference(CObjectWrapper):

	WRAPPED   = TReference

	FUNCTIONS = """
	Reference* Reference_Ensure(void* element); // @as _Ensure
	Reference* Reference_FromElement(ParsingElement* element); // @as _FromElement
	Reference* Reference_new(void);
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

	def _new( self, element=None, name=None ):
		CObjectWrapper._new(self)
		self.element = element
		self.name    = name

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

class Word(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Word_new(const char* word);
	void Word_free(ParsingElement* this);
	"""

class Token(ParsingElement):

	FUNCTIONS = """
	ParsingElement* Token_new(const char* expr);
	void Token_free(ParsingElement* this);
	"""

# -----------------------------------------------------------------------------
#
# COMPOSITE PARSING ELEMENTS
#
# -----------------------------------------------------------------------------

class CompositeElement(ParsingElement):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	this* ParsingElement_add(ParsingElement* this, Reference* child); // @as _add
	"""

	# NOTE: This is an attempt at memory management
	# def _init( self ):
	# 	self._children = []

	def _new(self, *args):
		ParsingElement._new(self, None)
		for _ in args:
			self.add(_)

	def add( self, reference ):
		# argument = reference
		assert reference
		assert isinstance(reference, ParsingElement) or isinstance(reference, Reference), "{0}.add: Expected ParsingElement or Reference, got {1}".format(self.__class__, reference)
		reference = Reference.Ensure(reference)
		assert isinstance(reference, Reference)
		self._add(reference)
		# self._children.append((reference, argument))
		assert self.children
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
		else:
			raise ValueError

	def group( self, index=0 ):
		raise NotImplementedError

	def type( self ):
		return self._wrapped.contents.element.contents.type

	def range( self ):
		"""Returns the range (start, end) of the match."""
		return (self.offset, self.offset + self.length)

	def isReference( self ):
		"""A utility shorthand to know if a match is a reference."""
		return self.getType() == TYPE_REFERENCE

class CompositeMatch(Match):

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
		raise IndexError

	def get( self, name=NOTHING ):
		if name is NOTHING:
			return dict((_.name(), _) for _ in self.children() if _.name())
		else:
			for _ in self.children():
				if _.name() == name:
					return _
			raise IndexError

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

	def reference( self ):
		"""The reference wrapping the parsing element."""
		# if not self._reference:
		# 	self._reference = ctypes.cast(self._wrapped.contents.element, C.TYPES["Reference*"]).contents
		# print "REFERENENCE", self._reference
		# return self._reference
		return ctypes.cast(self._wrapped.contents.element, C.TYPES["Reference*"]).contents

	def element( self ):
		"""The parsing element wrapped by the reference"""
		return self.reference().element

	def name( self ):
		"""The name of the reference."""
		return self.reference().name

	def group( self, index=0 ):
		if self.isOne():
			return self.child.group(0)
		else:
			return self.getChild(index).group()

	def groups( self ):
		return [_.group() for _ in self]

	def cardinality( self ):
		return self.reference().cardinality

	def isOne( self ):
		return self.cardinality() == CARDINALITY_ONE

	def isOptional( self ):
		return self.cardinality() == CARDINALITY_OPTIONAL

	def isZeroOrMore( self ):
		return self.cardinality() == CARDINALITY_MANY_OPTIONAL

	def isOneOrMore( self ):
		return self.cardinality() == CARDINALITY_MANY

class WordMatch(Match):

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

	def group( self, index=0 ):
		return self._group(index)

	def groups( self ):
		element = ctypes.cast(self._wrapped.contents.element, C.TYPES["ParsingElement*"]).contents
		match   = ctypes.cast(self._wrapped.contents.data,    C.TYPES["TokenMatch*"]).contents
		return [self.group(i) for i in range(match.count)]

class RuleMatch(CompositeMatch):
	pass

class GroupMatch(CompositeMatch):

	pass

# -----------------------------------------------------------------------------
#
# PARSING RESULTS
#
# -----------------------------------------------------------------------------

class ParsingResult(CObjectWrapper):

	WRAPPED   = TParsingResult
	FUNCTIONS = """
	void ParsingResult_free(ParsingResult* this);
	bool ParsingResult_isFailure(ParsingResult* this);
	bool ParsingResult_isPartial(ParsingResult* this);
	bool ParsingResult_isSuccess(ParsingResult* this);
	bool ParsingResult_isComplete(ParsingResult* this);
	"""

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
	ParsingResult* Grammar_parseFromIterator( Grammar* this, Iterator* iterator );
	ParsingResult* Grammar_parseFromPath( Grammar* this, const char* path );
	ParsingResult* Grammar_parseFromString( Grammar* this, const char* text );
	"""

	PROPERTIES = lambda:dict(
		axiom = Word
	)

	def _new( self, isVerbose=False, axiom=None ):
		CObjectWrapper._new(self)
		self.isVerbose = isVerbose and 1 or 0
		self.axiom     = axiom

# -----------------------------------------------------------------------------
#
# PROCESS
#
# -----------------------------------------------------------------------------

class AbstractProcessor( object ):
	"""The main entry point when using `libparsing` form Python. Subclass
	the processor and define parsing element handlers using the convention
	`on<ParsingElement's name`. For instance, if your grammar has a `NAME`
	symbol defined, then `onNAME` will be invoked with its match element.

	Note that symbol handlers (`onXXX` methods) take the `match` object
	as first argument as well as the named elements defined in the symbol,
	if it is a composite symbol (rule, group, etc). The named elements
	are the ones you declare using `_as`."""

# -----------------------------------------------------------------------------
#
# MODULE INITIALIZATION
#
# -----------------------------------------------------------------------------

# We pre-declare the types that are required by the structure declarations.
# It's OK if they're void* instead of the actual structure definition.
C.TYPES.update({
	"Iterator*"       : ctypes.c_void_p,
	"Element*"        : ctypes.c_void_p,
	"Element**"       : ctypes.POINTER(ctypes.c_void_p),
	"ParsingContext*" : ctypes.c_void_p,
	"ParsingOffset*"  : ctypes.c_void_p,
	"WalkingCallback" : ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p),
})

# We register structure definitions that we want to be accessible
# through C types
C.Register(
	TElement,
	TParsingElement,
	TReference,
	TWordConfig,
	TTokenMatch,
	TMatch,
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
	"libparsing"
).register(
	Reference,
	Match,
	ParsingResult,
	Grammar,
	Word,
	Token,
	TokenMatch,
	Rule,
	Group,
)

# We dynamically register shorthand factory methods for parsing elements in
# the Grammar.
for _ in [Word]:
	name = _.__name__.rsplit(".", 1)[-1]
	name = name.lower()
	def creator( self, *args, **kwargs ):
		element = _(*args, **kwargs)
	def named_creator( self, name, *args, **kwargs ):
		element = _(*args, **kwargs)
		element.name = name
	setattr(Grammar, name,       named_creator)
	setattr(Grammar, "a" + name, creator)

# NOTE: Useful for debugging
# for k in sorted(C.TYPES.keys()):
# 	print "C.TYPES[{0}] = {1}".format(k, C.TYPES[k])

# -----------------------------------------------------------------------------
#
# TEST
#
# -----------------------------------------------------------------------------

import unittest

class Test():#(unittest.TestCase):

	def testCTypesBehaviour():
		"""A few assertions about what to expect from CTypes."""
		# We retrieve the TReference type
		ref = C.TYPES["Reference*"]
		assert ref.__name__.endswith("LP_TReference")
		# We create a new reference pointer, which is a NULL pointer
		r = ref()
		# NULL pointers have a False boolean value
		assert not r
		assert not bool(r)
		assert r is not False
		assert r is not None
		# And raise a ValueError when accessed
		was_null = False
		try:
			r.contents
		except ValueError as e:
			assert "NULL pointer access" in str(e)
			was_null = True
		assert was_null

	def testReference():
		# We're trying to assert that Reference objects created from C
		# work as expected.
		libparsing = C_API.symbols
		r = libparsing.Reference_new()
		assert not libparsing.Reference_hasElement(r)
		assert not libparsing.Reference_hasNext(r)
		assert r.contents._b_needsfree_ is 0
		# SEE: https://docs.python.org/2.5/lib/ctypes-data-types.html
		assert r.contents.name == "_"
		assert r.contents.id   == -1, r.contents.id
		# So that's the surprising stuff about ctypes. Our C code assigns
		# NULL to element and next. If we had declared TReference with
		# `next` and `element` as returning `void*`, then we would
		# get None. But because they're ParsingElement* and Reference*
		# they return these pointers pointing to NULL.
		assert not r.contents.element
		assert not r.contents.next
		assert r.contents.element is not None
		assert r.contents.next    is not None
		# r.contents.element = 0
		# r.contents.next    = 0
		assert isinstance(r.contents.element, C.TYPES["ParsingElement*"])
		assert isinstance(r.contents.next,    C.TYPES["Reference*"])
		# And the C addresses of the element and next (which are NULL pointers)
		# is not 0. This is because `addressof` returns the object of the Python
		# pointer instance, not the address of its contents.
		assert ctypes.addressof(r.contents.element) != 0
		assert ctypes.addressof(r.contents.next)    != 0
		# Anyhow, we now creat an empty rule
		ab = libparsing.Rule_new(None)
		assert ab.contents._b_needsfree_ is 0
		# And we add it the reference
		C_API._cdll["ParsingElement_add"](ab, r)
		# DEBUG: This is where we experienced problems, basically due to
		# incorrect signature.
		print "Invocation throught symbols"
		libparsing.ParsingElement_add(ab, r)

	def testSimpleGrammar( self ):
		g       = Grammar()
		text    = "pouet"
		w       = Word(text)
		g.axiom = w
		g.isVerbose = False
		r       = g.parseFromString(text)
		assert r
		m       = r.match
		assert m
		self.assertEqual(m.status, "M")
		self.assertEqual(m.offset,  m.getOffset())
		self.assertEqual(m.length,  m.getLength())
		self.assertEqual(m.offset,  0)
		self.assertEqual(m.length,   len(text))
		self.assertIsNone(m.next)
		self.assertIsNone(m.child)

	def testRuleFlat():
		libparsing = C_API.symbols
		g  = libparsing.Grammar_new()
		a  = libparsing.Word_new("a")
		b  = libparsing.Word_new("b")
		ab = libparsing.Rule_new(None)
		ra = libparsing.Reference_Ensure(a)
		rb = libparsing.Reference_Ensure(b)
		libparsing.ParsingElement_add(ab, ra)
		libparsing.ParsingElement_add(ab, rb)
		g.contents.axiom     = ab
		g.contents.isVerbose = 1
		libparsing.Grammar_parseFromString(g, "abab")


	def testRuleOO():
		g       = Grammar()
		text    = "abab"
		a       = Word("a")
		b       = Word("b")
		ab      = Rule(None)
		ra      = Reference.Ensure(a)
		rb      = Reference.Ensure(b)
		assert a._wrapped._b
		ab.add(ra)
		ab.add(rb)
		g.axiom = ab
		g.isVerbose = True
		r = g.parseFromString(text)

	def testMemory( self ):
		# In this case Word and Grammar should all be freed upon deletion.
		a = Word("a")
		b = Word("b")
		g = Grammar(
			isVerbose = True,
			axiom     = Rule(a, b)
		)
		self.assertEquals(g._wrapped.contents._b_needsfree_, 0)
		self.assertTrue(g._mustFree)
		self.assertEquals(a._wrapped.contents._b_needsfree_, 0)
		self.assertTrue(a._mustFree)
		self.assertEquals(a._wrapped.contents._b_needsfree_, 0)
		self.assertTrue(a._mustFree)

	def testMatch(self):
		# We use the fancier shorthands
		g = Grammar(
			isVerbose = False,
			axiom     = Rule(Word("a"), Word("b"))
		)
		r = g.parseFromString("abab")
		# We test the parsing result
		assert isinstance(r, ParsingResult)
		assert not r.isFailure()
		assert r.isSuccess()
		assert r.isPartial()
		assert not r.isComplete()
		# We ensure that the over offset matches
		assert isinstance(r.match, RuleMatch)
		assert r.match.offset  == 0
		assert r.match.length  == 2
		assert r.match.range() == (0, 2)
		assert len(r.match) == 2
		self.assertEquals([_.group() for _ in r.match], ["a", "b"])
		# We test child 1
		ma = r.match[0]
		# NOTE: The following assertions will fail for now
		# print ma.element()
		# assert isinstance(ma.element(), Word)
		self.assertEquals(ma.group(), "a")
		self.assertEquals(ma.range(), (0,1))
		mb = r.match[1]
		self.assertEquals(mb.group(), "b")
		self.assertEquals(mb.range(), (1,2))
		# NOTE: The following creates core dump... ahem
		#for i,m in enumerate(r.match.children()):
		#	print "Match", i, "=", m, m.name(), m.element(), m.cardinality(), list(m.children()), m.group(), m.range()


class Test(unittest.TestCase):

	def testGrammar(self):
		NUMBER     = Token("\d+")
		VARIABLE   = Token("\w+")
		OPERATOR   = Token("[\+\-*\/]")
		Value      = Group(NUMBER, VARIABLE)
		Operation  = Rule(
			Value._as("left"), OPERATOR._as("op"), Value._as("right")
		)
		g = Grammar(
			isVerbose = False,
			axiom     = Operation
		)
		# We parse, and make sure it completes
		r = g.parseFromString("1+10")
		self.assertTrue(r.isSuccess())
		self.assertTrue(r.isComplete())

		# The individual retrieval of object is slower than the one shot
		left  = r.match.get("left")
		op    = r.match.get("op")
		right = r.match.get("right")

		# We have reference matches first
		assert isinstance(left,     ReferenceMatch)
		assert isinstance(op,       ReferenceMatch)
		assert isinstance(right,    ReferenceMatch)

		# Which themselves hold group matches
		assert isinstance(left[0],  GroupMatch)
		assert isinstance(op[0],    TokenMatch)
		assert isinstance(right[0], GroupMatch)


		print left.groups()
		print op.groups()
		print right.groups()

		# We decompose the operator
		self.assertEquals(op[0].group(), "+")
		self.assertEquals(op.group(),    "+")
		self.assertEquals(op.groups(),  ["+"])

		v     = r.match.get()
		assert "left"  in v
		assert "op"    in v
		assert "right" in v


if __name__ == "__main__":
	unittest.main()

# EOF - vim: ts=4 sw=4 noet
