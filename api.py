import ctypes, os

NOTHING = ctypes
C_API   = None

# -----------------------------------------------------------------------------
#
# C INTERFACE
#
# -----------------------------------------------------------------------------

class C:
	"""An interface/helper to the `ctypes` module. The `C.TYPES` mapping maps
	C type names to their corresponding `ctypes` type declaration."""

	TYPES = {
		"void"            : None,
		"bool"            : ctypes.c_byte,
		"char"            : ctypes.c_char,
		"void*"           : ctypes.c_void_p,
		"char*"           : ctypes.c_char_p,
		"const char*"     : ctypes.c_char_p,
		"int"             : ctypes.c_int,
		"float"           : ctypes.c_float,
		"double"          : ctypes.c_double,
		"size_t"          : ctypes.c_uint,
		"size_t*"         : ctypes.POINTER(ctypes.c_uint),
	}

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
			# We bind the fields of the structure
			cls.BindStructure(_)
			# And we register, possibly overriding the already
			# registered type.
			c_name = _.__name__.rsplit(".", 1)[-1]
			assert c_name.startswith("T"), c_name
			c_name = c_name[1:] + "*"
			types[c_name] = ctypes.POINTER(_)
		cls.TYPES.update(types)
		return types

	@classmethod
	def ParsePrototype( cls, prototype ):
		"""Parses a function prototype, returning `(name, argument ctypes, return ctype)`"""
		prototype = prototype.split("//",1)[0].split(";",1)[0]
		ret_name, params = prototype.split("(", 1)
		params           = params.rsplit(")",1)[0]
		ret, name        = ret_name.strip().rsplit(" ", 1)
		params           = [_.strip().rsplit(" ", 1) for _ in params.split(",",) if _.strip()]
		params           = [(cls.TYPES[_[0]],_[1]) for _ in params if _ != ["void"]]
		ret              = cls.TYPES[ret]
		return (name, params, ret)

	@classmethod
	def ParsePrototypes( cls, declarations ):
		for line in (declarations or "").split("\n"):
			line = line.replace("\t", " ").strip()
			if not line: continue
			proto = cls.ParsePrototype(line)
			yield proto

	@classmethod
	def LoadFunctions( cls, library, declarations ):
		"""Binds the declared functions in the given library."""
		res = []
		for proto in cls.ParsePrototypes(declarations):
			name, argtypes, restype = proto
			func = library[name]
			func.argtypes = [_[0] for _ in argtypes]
			func.restype  = restype
			res.append((func, proto))
		return res

# -----------------------------------------------------------------------------
#
# C LIBRARY
#
# -----------------------------------------------------------------------------

class CLibrary:

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
			_._library = self
			assert issubclass(_, CObjectWrapper)
			# We load the functions from the library
			functions = C.LoadFunctions(self.lib, _.FUNCTIONS)
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

# -----------------------------------------------------------------------------
#
# OBJECT WRAPPER
#
# -----------------------------------------------------------------------------

class CObjectWrapper(object):

	WRAPPED   = None
	FUNCTIONS = None

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
			print "G:", cls.__name__ + "." + name, type
			return getattr(self._wrapped.contents, name)
		def setter( self, value ):
			value = c.UnwrapCast(value, type)
			print "S:", cls.__name__ + "." + name, type, "=", value, "|", c.Unwrap(value)
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
		def method(self, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			print "F:", proto[0], args,
			args = [c.Unwrap(_) for _ in args]
			res  = ctypesFunction(*args)
			res  = self._library.wrap(res)
			print "|", args, "-->", res
			return res
		return method

	@classmethod
	def _CreateMethod( cls, ctypesFunction, proto):
		c = C
		def method(self, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			print "M:", proto[0], args,
			args = [c.Unwrap(self)] + [c.Unwrap(_) for _ in args]
			assert args[0], "CObjectWrapper: method {0} `this` is None in {1}".format(proto[0], self)
			res  = ctypesFunction(*args)
			res  = self._library.wrap(res)
			print "|", args, "-->", res
			return res
		return method

	@classmethod
	def BindFunction( cls, ctypesFunction, proto ):
		class_name = cls.__name__.rsplit(".",1)[-1]
		# We need to keep a reference to C as otherwise it might
		# be freed before we invoke c.Unwrap.
		method = None
		if len(proto[1]) >= 1 and proto[1][0][1] == "this":
			method = cls._CreateMethod(ctypesFunction, proto)
		else:
			method = cls._CreateFunction(ctypesFunction, proto)
		# We assume the convention is <Classname>_methodName
		assert proto[0].startswith(class_name + "_")
		name = proto[0].split("_", 1)[1]
		setattr(cls, name, method)
		assert hasattr(cls, name)
		return (name, method)

	@classmethod
	def Wrap( cls, wrapped ):
		"""Wraps the given object in this CObjectWrapper. The given
		object must be a ctypes value, usually a pointer to a struct."""
		return cls( wrappedCObject=wrapped )

	def __init__( self, *args, **kwargs ):
		self._wrapped = None
		if "wrappedCObject" in kwargs:
			self._wrapped = kwargs["wrappedCObject"]
			assert self._wrapped
			assert isinstance(self._wrapped, ctypes.POINTER(self.WRAPPED))
			self._created = False
		else:
			# We ensure that the _wrapped value returned by the creator is
			# unwrapped. In fact, we might want to implement a special case
			# for new that returns directly an unwrapped value.
			self._wrapped = C.Unwrap(self.new(*args))
			self._created = True

	def __del__( self ):
		if self._wrapped and self._created:
			# FIXME: There are some issues with the __DEL__ when other stuff is not available
			# if hasattr(self, "free") and getattr(self, "free"):
			# 	self.free(self._wrapped)
			pass

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

class TGrammar(ctypes.Structure):

	STRUCTURE = """
	ParsingElement*  axiom;       // The axiom
	ParsingElement*  skip;        // The skipped element
	int              axiomCount;  // The count of parsing elemetns in axiom
	int              skipCount;   // The count of parsing elements in skip
	Element**        elements;    // The set of all elements in the grammar
	bool             isVerbose;
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

	# def setAxiom( self, value ):
	# 	g._wrapped.axiom = value._wrapped

	# def getAxiom( self ):
	# 	return Word.FromWrapped(g._wrapped.axiom)

class Word(CObjectWrapper):

	WRAPPED   = TParsingElement
	FUNCTIONS = """
	ParsingElement* Word_new(const char* word);
	void Word_free(ParsingElement* this);
	"""

class ParsingResult(CObjectWrapper):

	WRAPPED   = TParsingResult
	FUNCTIONS = """
	void ParsingResult_free(ParsingResult* this);
	"""

# -----------------------------------------------------------------------------
#
# MODULE INITIALIZATION
#
# -----------------------------------------------------------------------------

def __init__():

	# We pre-declare the types that are required by the structure declarations.
	# It's OK if they're void* instead of the actual structure definition.
	C.TYPES.update({
		"Grammar*"        : ctypes.c_void_p,
		"Iterator*"       : ctypes.c_void_p,
		"Reference*"      : ctypes.c_void_p,
		"Element*"        : ctypes.c_void_p,
		"Element**"       : ctypes.POINTER(ctypes.c_void_p),
		"ParsingContext*" : ctypes.c_void_p,
		"ParsingOffset*"  : ctypes.c_void_p,
		"ParsingStats*"   : ctypes.c_void_p,
		"ParsingElement*" : ctypes.c_void_p,
		"ParsingResult*"  : ctypes.c_void_p,
		"Match*"          : ctypes.c_void_p,
	})

	# We register structure definitions that we want to be accessible
	# through C types
	C.Register(
		TParsingElement,
		#TMatch,
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
	global C_API
	C_API = CLibrary(
		"libparsing"
	).register(
		ParsingResult,
		Grammar,
		Word
	)

# -----------------------------------------------------------------------------
#
# TEST
#
# -----------------------------------------------------------------------------

__init__()

g = Grammar()
w = Word("pouet")
g.axiom = w

print "=" * 80
#print "WRAPPED", g._wrapped.contents.axiom
r = g.parseFromString("pouet")
print r.match
print "=" * 80

# EOF
