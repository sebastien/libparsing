import ctypes, os

NOTHING = ctypes
API     = None

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
		"size_t"          : ctypes.c_uint,
	}

	@classmethod
	def Unwrap( cls, value ):
		if isinstance(value, CObjectWrapper):
			return value._wrapped
		else:
			return value

	# @classmethod
	# def Wrap( cls cValue)

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
			name, argtypes, rettype = proto
			func = library[name]
			func.argtypes = [_[0] for _ in argtypes]
			func.rettype  = rettype
			res.append((func, proto))
		return res

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

class TParsingContext(ctypes.Structure):

	STRUCTURE = """
		struct Grammar*       grammar;      // The grammar used to parse
		struct Iterator*      iterator;     // Iterator on the input data
		struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
		struct ParsingOffset* current;      // The current parsing offset
		struct ParsingStats*  stats;
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

# -----------------------------------------------------------------------------
#
# C API
#
# -----------------------------------------------------------------------------

class Library:

	PATHS = [
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

	def register( self, *wrapperClasses ):
		"""Register the given `CObjectWrapper` in this library, loading the
		corresponding functions and binding them to the class."""
		for _ in wrapperClasses:
			assert issubclass(_, CObjectWrapper)
			# We load the functions from the library
			functions = C.LoadFunctions(self.lib, _.FUNCTIONS)
			# We bind the functions declared in the wrapper
			_.BindFunctions(functions)
		return self

# -----------------------------------------------------------------------------
#
# OBJECT WRAPPER
#
# -----------------------------------------------------------------------------

class CObjectWrapper(object):

	FUNCTIONS = None

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
			print "CALLING FUNCTION", proto[0], ctypesFunction, "with", args
			args = [c.Unwrap(_) for _ in args]
			print "-->", args
			res  = ctypesFunction(*args)
			return res
		return method

	@classmethod
	def _CreateMethod( cls, ctypesFunction, proto):
		c = C
		def method(self, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			print "CALLING METHOD", proto[0], ctypesFunction, "with", args
			args = [c.Unwrap(self)] + [c.Unwrap(_) for _ in args]
			print "-->", args
			assert args[0], "CObjectWrapper: method {0} `this` is None in {1}".format(proto[0], self)
			res  = ctypesFunction(*args)
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
	def FromWrapped( cls, wrapped ):
		return cls.__init__( wrappedCObject=wrapped )

	def __init__( self, *args, **kwargs ):
		self._wrapped = None
		if "wrappedCObject" in kwargs:
			self._wrapped = kwargs["wrappedCObject"]
			self._created = False
		else:
			self._wrapped = self.new(*args)
			self._created = True

	def __del__( self ):
		if self._wrapped and self._created:
			if hasattr(self, "free"):
				self.free(self._wrapped)

# -----------------------------------------------------------------------------
#
# WRAPPER
#
# -----------------------------------------------------------------------------

class Grammar(CObjectWrapper):

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

	FUNCTIONS = """
	ParsingElement* Word_new(const char* word);
	void Word_free(ParsingElement* this);
	"""


# g = Grammar()
# w = Word("a")
# g.setAxiom(w)
# g.getAxiom()
# print w._wrapped.contents.recognize

def __init__():

	C.TYPES.update({
		"Grammar*"        : ctypes.c_void_p,
		"Iterator*"       : ctypes.c_void_p,
		"Reference*"      : ctypes.c_void_p,
		"ParsingContext*" : ctypes.c_void_p,
		"ParsingOffset*"  : ctypes.c_void_p,
		"ParsingStats*"   : ctypes.c_void_p,
		"ParsingElement*" : ctypes.c_void_p,
		"ParsingResult*"  : ctypes.c_void_p,
		"Match*"          : ctypes.c_void_p,
	})

	C.Register(
		TParsingElement,
		TParsingContext,
	)

	global API
	API = Library(
		"libparsing"
	).register(
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
g.parseFromString("pouet")

# EOF
