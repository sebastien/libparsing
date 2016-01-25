import ctypes, os, re

NOTHING = ctypes
C_API   = None

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
		"bool"            : ctypes.c_char,
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
		if type is ctypes.c_char:
			if value is True:
				return chr(1)
			elif value is False:
				return chr(0)
			else:
				return chr(value)
		else:
			return ctypes.cast(value, type)

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
			print ("C:Register: type {0} from {1}".format(c_name, _))
			cls.TYPES[c_name]       = types[c_name]
			cls.TYPES[c_name + "*"] = types[c_name + "*"]
		for _ in ctypeClasses:
			# We bind the fields of the structure
			cls.BindStructure(_)
		return types

	@classmethod
	def GetType( cls, name, selfType=None ):
		if name == "this*":
			return selfType
		else:
			return cls.TYPES[name]

	@classmethod
	def ParsePrototype( cls, prototype, selfType=None ):
		"""Parses a function prototype, returning `(name, argument ctypes, return ctype)`"""
		print "C:Parsing prototype", prototype
		as_name   = cls.RE_AS.search(prototype)
		prototype = prototype.replace(" *", "* ")
		prototype = prototype.split("//",1)[0].split(";",1)[0]
		ret_name, params = prototype.split("(", 1)
		params           = params.rsplit(")",1)[0]
		ret, name        = ret_name.strip().rsplit(" ", 1)
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
	def LoadFunctions( cls, library, declarations, selfType=None ):
		"""Binds the declared functions in the given library."""
		res = []
		for proto in cls.ParsePrototypes(declarations, selfType):
			name, argtypes, restype = proto
			name, alias             = name
			print ("C:Loading function {0} with {1} -> {2}".format( name, argtypes, restype))
			func = library[name]
			func.argtypes = [_[0] for _ in argtypes]
			func.restype  = restype[0]
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
		self.lib = self.Load(path)
		self._wraps = [] + self.WRAPS

	def register( self, *wrapperClasses ):
		"""Register the given `CObjectWrapper` in this library, loading the
		corresponding functions and binding them to the class."""
		for _ in wrapperClasses:
			_.LIBRARY = self
			assert issubclass(_, CObjectWrapper)
			# We load the functions from the library
			functions = C.LoadFunctions(self.lib, _.GetFunctions(), _.WRAPPED)
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
		# for t,f in self._wraps:
		# 	if isinstance(cValue, t): return f(cValue)
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
			print "g: ", cls.__name__ + "." + name, type, "=", value
			return self.LIBRARY.wrap(value)
		def setter( self, value ):
			value = self.LIBRARY.unwrapCast(value, type)
			print "s: ", cls.__name__ + "." + name, type, "<=", value
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
		is_constructor = proto[0][0].endswith("_name")
		def function(cls, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			print "F: ", proto[0], args
			args = [cls.LIBRARY.unwrap(_) for _ in args]
			res  = ctypesFunction(*args)
			if not is_constructor:
				# Non-constructors must wrap the result
				res  = cls.LIBRARY.wrap(res)
			print "F=>", res
			return res
		return function

	@classmethod
	def _CreateMethod( cls, ctypesFunction, proto):
		c = C
		returns_this = proto[2][2] == "this*"
		def method(self, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			print "M: ", proto[0], args
			args = [self.LIBRARY.unwrap(self)] + [self.LIBRARY.unwrap(_) for _ in args]
			print "   ", args
			assert args[0], "CObjectWrapper: method {0} `this` is None in {1}".format(proto[0], self)
			try:
				res  = ctypesFunction(*args)
			except ctypes.ArgumentError as e:
				raise ValueError("{1} failed with {2}: {3}".format(cls.__name__, proto[0][0], args, e))
			res  = self if returns_this else self.LIBRARY.wrap(res)
			print "M=>", res
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
		print ("O:{1} bound as {3} {0}.{2}".format(cls.__name__, proto[0][0], name, "method" if is_method else "function"))
		setattr(cls, name, method)
		assert hasattr(cls, name)
		return (name, method)

	@classmethod
	def Wrap( cls, wrapped ):
		"""Wraps the given object in this CObjectWrapper. The given
		object must be a ctypes value, usually a pointer to a struct."""
		assert None
		return cls( wrappedCObject=wrapped )

	@classmethod
	def _Create( cls, *args ):
		return cls._constructor(*args)

	def __init__( self, *args, **kwargs ):
		self._wrapped = None
		if "wrappedCObject" in kwargs:
			assert not self._wrapped
			self._wrapped = kwargs["wrappedCObject"]
			assert self._wrapped
			assert isinstance(self._wrapped, ctypes.POINTER(self.WRAPPED))
			self._mustFree = False
		else:
			# We ensure that the _wrapped value returned by the creator is
			# unwrapped. In fact, we might want to implement a special case
			# for new that returns directly an unwrapped value.
			instance       = self.__class__._Create(*args)
			assert isinstance( instance, ctypes.POINTER(self.WRAPPED))
			assert not self._wrapped
			self._wrapped  = instance
			self._mustFree = True

	# FIXME: We experience many problems with destructors, ie. segfaults in GC.
	# Thsi needs to be sorted out.
	# def __del__( self ):
	# 	if self._wrapped and self._created:
	# 		# FIXME: There are some issues with the __DEL__ when other stuff is not available
	# 		# if hasattr(self, "free") and getattr(self, "free"):
	# 		# 	self.free(self._wrapped)
	# 		pass
	# 	object.__del__(self)

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

class TReference(ctypes.Structure):

	STRUCTURE = """
	char            type;            // Set to Reference_T, to disambiguate with ParsingElement
	int             id;              // The ID, assigned by the grammar, as the relative distance to the axiom
	char            cardinality;     // Either ONE (default), OPTIONAL, MANY or MANY_OPTIONAL
	const char*     name;            // The name of the reference (optional)
	struct ParsingElement* element;  // The reference to the parsing element
	struct Reference*      next;     // The next child reference in the parsing elements
	"""

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

class Reference(CObjectWrapper):

	WRAPPED   = TReference

	FUNCTIONS = """
	Reference* Reference_Ensure(void* elementOrReference);     // @as _Ensure
	Reference* Reference_FromElement(ParsingElement* element); // @as _FromElement
	Reference* Reference_new(void);
	Reference* Reference_cardinality(Reference* this, char cardinality); // @as setCardinality
	Reference* Reference_name(Reference* this, const char* name); // @as setName
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
		assert isinstance(res, Reference)
		res._mustFree = True
		return res

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

class CompositeParsingElement(ParsingElement):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	this* ParsingElement_add(ParsingElement* this, Reference* child); // @as _add
	"""

	def add( self, reference ):
		#reference = Reference.Ensure(reference)
		#assert isinstance(reference, Reference)
		# FIXME: Somehow, using _add does not work! This is potentially a
		# major source of problems down the road.
		#self._add(reference)
		print "REFERENCE", reference, reference._wrapped
		reference = self.LIBRARY.lib.Reference_Ensure(reference._wrapped)
		print ("REFERENCE", reference)
		self._add(reference)
		# self.LIBRARY.lib.ParsingElement_add(self._wrapped, reference)
		assert self.children
		return self

class Rule(CompositeParsingElement):

	# FIXME: No free method here
	FUNCTIONS = """
	ParsingElement* Rule_new(Reference** children);
	"""

# -----------------------------------------------------------------------------
#
# PARSING RESULTS
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

class ParsingResult(CObjectWrapper):

	WRAPPED   = TParsingResult
	FUNCTIONS = """
	void ParsingResult_free(ParsingResult* this);
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
	"ParsingStats*"   : ctypes.c_void_p,
	"WalkingCallback" : ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p),
})

# We register structure definitions that we want to be accessible
# through C types
C.Register(
	TParsingElement,
	TReference,
	TTokenMatch,
	TMatch,
	#TParsingContext,
	#TParsingStats,
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
	Rule,
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
# for k in C.TYPES:
# 	print "C.TYPES[{0}] = {1}".format(k, C.TYPES[k])

# -----------------------------------------------------------------------------
#
# TEST
#
# -----------------------------------------------------------------------------

import unittest

class Test(unittest.TestCase):

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

	def testCompositeGrammar( self ):
		pass

# -----------------------------------------------------------------------------
#
# DIRECTIVES
#
# -----------------------------------------------------------------------------

g       = Grammar()
text    = "abab"
a       = Word("a")
b       = Word("b")
ab      = Rule(None)
ab.add(a)
ab.add(b)
g.axiom = ab
g.isVerbose = True
r = g.parseFromString(text)

# if __name__ == "__main__":
# 	unittest.main()

# EOF
