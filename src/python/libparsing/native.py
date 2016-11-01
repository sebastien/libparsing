#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : libparsing (Python bindings)
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2016-01-21
# Last modification : 2016-02-08
# -----------------------------------------------------------------------------

import ctypes, os, re, sys, weakref, types, inspect
from   copy import copy

IS_PYTHON3 = sys.version_info[0] >= 3

__doc__ = """
An abstraction of `ctypes` that allows for the development of object-oriented
bindings to C code written in an object-oriented style (à la glib).
"""

C_FUNCTION_TYPE = type(ctypes.CFUNCTYPE(None))
C_POINTER_TYPE  = type(ctypes.POINTER(None))

# -----------------------------------------------------------------------------
#
# C NATIVE INTERFACE
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
		"PyObject*"       : ctypes.py_object,
	}

	# NOTE: Performance can be gained by keeping C objects for longer
	COBJECTS = weakref.WeakValueDictionary()

	@classmethod
	def Cast( cls, type, value ):
		if isinstance(type, str): type = cls.TYPES[type]
		return ctypes.cast(value, type)

	@classmethod
	def String( cls, value ):
		"""Ensures that the given value is a CString"""
		if IS_PYTHON3:
			# In Python3, ctypes requires bytes instead of str and does not
			# do any automatic casting. So we need to store it.
			wrapped = value.encode("utf-8") if isinstance(value, str) else value
			assert isinstance(wrapped, bytes)
			# FIXME: The problem here is that the wrapped string MUST be
			# kept as reference.
			return wrapped
		else:
			# In Python2, strings are bytes from the get-go so they're
			# simply passed as-is
			return value

	@classmethod
	def Unwrap( cls, value, cast=None ):
		assert not isinstance(value, ctypes.Structure), "C.Unwrap: ctypes structures must be wrapped in CObjects {0}".format(value)
		if CObject and isinstance(value, CObject) or isinstance(value, object) and hasattr(value, "_cobjectPointer"):
			# We pass the cobject structure by reference, CObject might be garbage collected at this time
			return value._cobjectPointer
		elif isinstance(value, str) and IS_PYTHON3:
			c_value = cls.String(value)
		elif type(cast) is C_FUNCTION_TYPE:
			# A Python function must be wrapped in the callback
			c_value = cast(value) if value else None
		else:
			# Otherwise, CTypes will do the argument checking anyway
			c_value = value
		return c_value

	@classmethod
	def RegisterCObject( cls, cobject ):
		"""Registers the given CObject to be bound to the given data structure."""
		address = ctypes.addressof(cobject._cobject)
		# NOTE: This assertion does a slowdown, and is really just helpful
		# for development.
		#assert address not in cls.COBJECTS
		cls.COBJECTS[address] = cobject
		return cobject

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
			# It's important to update the type directly here
			# print ("C:Register: type {0} from {1}".format(c_name, _))
			for t in (cls.TYPES, types):
				pointer         = ctypes.POINTER(_)
				t[c_name]       = pointer
				t[c_name + "*"] = ctypes.POINTER(pointer)
				t[_]            = pointer
				t[pointer]      = _
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
	`CObject` subclasses register themselves."""

	PATHS   = [
		__file__,
		os.path.join(__file__, ".."),
		os.path.join(__file__, "..", ".."),
		".",
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
		path = cls.Find(name)
		assert path, "Cannot find native library `{0}`".format(name)
		return ctypes.cdll.LoadLibrary(path)

	def __init__( self, path ):
		self._cdll   = self.Load(path)
		self.symbols = CLibrary.Symbols()
		self.ctypeToCObject = {}

	def register( self, *wrapperClasses ):
		"""Register the given `CObject` in this library, loading the
		corresponding functions and binding them to the class."""
		for _ in wrapperClasses:
			_.LIBRARY = self
			assert issubclass(_, CObject)
			# We load the functions from the library
			functions = C.LoadFunctions(self._cdll, _.GetFunctions(), _.WRAPPED)
			for func, proto in functions:
				name = proto[0][0]
				# print ("L:Library: binding symbol {0} with {1} → {2}".format(name, func.argtypes, func.restype))
				self.symbols.__dict__[name] = func
			# We bind the functions declared in the wrapper
			_.BindFunctions(functions)
			_.BindFields()
			self.ctypeToCObject[_.WRAPPED] = _
		return self

	def wrap( self, cValue ):
		"""Wraps the given C value in a Python object."""
		raise NotImplementedError

	def unwrap( self, wrapped, type=None ):
		"""Returns a C value corresponding to the given (wrapped) value."""
		return C.Unwrap(wrapped, type)

# -----------------------------------------------------------------------------
#
# OBJECT WRAPPER
#
# -----------------------------------------------------------------------------

class CObject(object):
	"""The CObject class wrap pointers to `ctypes.Structure` objects
	(ie. abstractions of underlying C structures) in an object-oriented API. This
	class seamlessly integrates with the `Library` class to dynamically load
	and type functions from the underlying C library and manage the
	conversion of values to and from C types.

	Each class defines static properties:

	- `WRAPPED` references the `ctypes.Structure` type wrapped by this CObject

	- `FUNCTIONS` is a string containing the `.h` declaration of the proptotypes
	   in the form `ClassName_methodName`. Special return value `this*` returns
	   the object reference, and special first argument `this*` indicates
	   a method as opposed to a function.

	- `ACCESSORS` is a map of property setter/getters created from the wrapped
	   structure `_fields_` property (see `ctypes` documentation for that)

	- `LIBRARY` wil be automatically set to the `CLibrary` instance in which
	  the `CObject` is registered. This reference should be used to access
	  symbols and wrap/unwrap functions.
	"""

	WRAPPED    = None
	FUNCTIONS  = None
	LIBRARY    = None
	ACCESSORS  = None
	PROTOTYPES = None

	# =========================================================================
	# PROPERTIES / C STRUCTURE FIELDS
	# =========================================================================

	@classmethod
	def BindFields( cls ):
		"""Binds the fields in this wrapped object. Fields that have a
		corresponding entry in the class's dict won't be bound, but all Will
		be registered in the `ACCESSORS` dictionary."""
		if cls.WRAPPED:
			# We explicitely refer to the DICT to bypass the inheritance
			# mechanism and get the class's own accessors.
			if "ACCESSORS" not in cls.__dict__: setattr(cls, "ACCESSORS", {})
			accessors = cls.ACCESSORS
			for name, type in cls.WRAPPED._fields_:
				accessor = cls._CreateAccessor(name, type)
				assert name not in accessors, "Accessor registered twice: {0}".format(name)
				# We register the accessors in the accessors map
				accessors[name] = accessor
				if not hasattr(cls, name):
					# and only set the attribute if we're not redefining it.
					setattr(cls, name, accessor)

	@classmethod
	def _CreateAccessor( cls, name, type ):
		"""Returns an accessor for the given field from a `ctypes.Structure._fields_`
		definition. Note that once you set the value from Python, it will be stored
		in cache, and will override the native object's value."""
		c = C
		def getter( self ):
			# The getter queries the cobjectCache first.
			if name in self._cobjectCache:
				return self._cobjectCache[name][0]
			else:
				c_value = getattr(self._cobject, name)
				value   = self.LIBRARY.wrap(c_value)
				# print "g: ", cls.__name__ + "." + name, type, "=", value
				#self._cobjectCache[name] = (value, c_value)
				return value
		def setter( self, value ):
			# This is required for Python3
			c_value = self.LIBRARY.unwrap(value)
			self._cobjectCache[name] = (value, c_value)
			# print "s: ", cls.__name__ + "." + name, type, "<=", value
			setattr(self._cobject, name, c_value)
		return property(getter, setter)

	# =========================================================================
	# FUNCTIONS
	# =========================================================================

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
	def BindFunctions( cls, functions ):
		"""Invoked by the library when the Wrapper is registered. Will update
		the class with definition of methods declared in the `FUNCTIONS`
		class property."""
		res = []
		for f, proto in functions:
			res.append(cls.BindFunction(f, proto))
		cls.PROTOTYPES = dict((_[0], _) for _ in res)
		return res

	@classmethod
	def BindFunction( cls, ctypesFunction, proto ):
		class_name = cls.__name__.rsplit(".",1)[-1]
		# We need to keep a reference to C as otherwise it might
		# be freed before we invoke self.LIBRARY.unwrap.
		method         = None
		name           = proto[0][1] or proto[0][0].split("_", 1)[1]
		slot           = name
		is_method      = len(proto[1]) >= 1 and proto[1][0][1] == "this"
		is_constructor = name == "new"
		# Factory methods
		if is_constructor:
			method = cls._CreateConstructor(name, ctypesFunction, proto)
			slot   = "_constructor"
		elif is_method:
			method = cls._CreateMethod(name, ctypesFunction, proto)
		else:
			assert proto[0][0][0].upper() == proto[0][0][0], "Class functions must start be CamelCase: {0}".format(proto[0][0])
			method = cls._CreateFunction(name, ctypesFunction, proto)
			method = classmethod(method)
		# Binding to the class
		# print ("O:{1} bound as {3} {0}.{2}".format(cls.__name__, proto[0][0], name, "method" if is_method else "function"))
		setattr(cls, slot, method)
		return (name, method, ctypesFunction, proto)

	@classmethod
	def _CreateConstructor( cls, name, ctypesFunction, proto):
		# Constructors do not wrap the result
		return cls._CreateFunction(name, ctypesFunction, proto, addThis=False, cacheArgs=True, wrapResult=False)

	@classmethod
	def _CreateMethod( cls, name, ctypesFunction, proto):
		# Methods add the this argument automatically
		return cls._CreateFunction(name, ctypesFunction, proto, addThis=True)

	@classmethod
	def _CreateFunction( cls, name, ctypesFunction, proto, addThis=False, cacheArgs=False, wrapResult=True):
		def function(self, *args):
			# We unwrap the arguments, meaning that the arguments are now
			# pure C types values
			c_args = [self.LIBRARY.unwrap(_, proto[1][i][0]) for i,_ in enumerate(args)]
			if cacheArgs:
				self._cobjectCache[name] = (args, c_args)
			if addThis:   c_args.insert(0, self._cobject)
			# print ("F: {0}({1}) → {2}".format( ".".join(_ for _ in proto[0] if _), ", ".join(repr(_) for _ in args), ", ".join(repr(_) for _ in args)))
			try:
				res  = ctypesFunction(*c_args)
			except ctypes.ArgumentError as e:
				raise ValueError("Bad arguments for {0}.{1}: {2}→{3} -- {4}".format(cls.__name__, name, args, c_args, e))
			# Non-constructors must wrap the result
			res  = self.LIBRARY.wrap(res) if wrapResult else res
			# TODO: We could check that the "this" returns the same object
			# print ("F=>{0}:{1}".format(repr(res), type(res)))
			return res
		return function

	# =========================================================================
	# OBJECT CREATION
	# =========================================================================

	@classmethod
	def Wrap( cls, cobject ):
		assert cobject
		return cls(wrappedCObject=cobject)

	def __init__( self, *args, **kwargs ):
		"""Creates a new CObject or wraps this CObject if `wrappedCObject`
		is given as keyword argument."""
		self._cobject        = None
		self._cobjectPointer = None
		self._cobjectCache   = {}
		self._init()
		if "wrappedCObject" in kwargs:
			assert not args and len(kwargs) == 1, "Additional arguments other than `wrappedCObject` were given: {0} {1}".format(args, kwargs)
			self._fromCObject(kwargs["wrappedCObject"])
		else:
			self._new(*args, **kwargs)

	def _fromCObject( self, cValue ):
		"""This CObject will wrap the given cValue."""
		assert not self._cobject
		assert isinstance(cValue, ctypes.POINTER(self.WRAPPED))
		assert cValue
		self._cobjectPointer = cValue
		self._cobject        = cValue.contents
		assert self._cobject != None, "{0}(wrappedCObject): wrappedCObject expected, got: {1}".format(self.__class__.__name__, self._cobject)
		self._mustFree = False
		C.RegisterCObject(self)

	# =========================================================================
	# OBJECT CREATION
	# =========================================================================

	def _new( self, *args ):
		"""Creates a new allocated instance of this object."""
		argtypes = self.PROTOTYPES["new"][2]
		# We ensure that the _cobject value returned by the creator is
		# unwrapped. In fact, we might want to implement a special case
		# for new that returns directly an unwrapped value.
		instance       = self._constructor(*args)
		assert isinstance( instance, ctypes.POINTER(self.WRAPPED)), "{0}(): {1} pointer expected, got {2}".format(self.__class__.__name__, self.WRAPPED, instance)
		assert not self._cobject
		assert instance != None, "{0}(): created instance seems to have no value: {1}".format(self.__class__.__name__, self._cobject)
		self._cobjectPointer = instance
		self._cobject        = instance.contents
		self._mustFree       = True
		C.RegisterCObject(self)

	def _init ( self ):
		"""Called before the object is assigned a wrapped value."""
		pass

	# FIXME: We experience many problems with destructors, ie. segfaults in GC.
	# This needs to be sorted out.
	def __del__( self ):
		if hasattr(self, "_cobjectPointer") and self._cobjectPointer and self._mustFree:
			# FIXME: There are some issues with the __DEL__ when other stuff is not available
			if hasattr(self, "free") and getattr(self, "free"):
				# We call the function directly, as the C class might be
				# freed already.
				self.PROTOTYPES["free"][2](self._cobjectPointer)

# -----------------------------------------------------------------------------
#
# DECORATORS
#
# -----------------------------------------------------------------------------

def cproperty( method, readonly=False ):
	"""Wraps a method that retrieves the current value of the underlying
	C data structure property as in a Python object. A reference to
	the Python object will be kept in cache and served upon later accesses.

	What this does in essence is execute the given method if there is no
	value found in cache for the given property, and store its results
	in cache. From then on,  it's up to the CObject to ensure consistency
	between the object's `_cobjectCache` and the underlying `_cobject`
	properties."""
	name = method.__name__
	def getter( self ):
		if name not in self._cobjectCache:
			value = method(self)
			value = self.LIBRARY.wrap(getattr(self._cobject, name)) if value is cproperty else value
			self._cobjectCache[name] = (value, None)
		return self._cobjectCache[name][0]
	def setter_ro( self, value ):
		raise ValueError("{0}.{1} is a read-only property".format(self, name))
	def setter_rw( self, value ):
		c_value = self.LIBRARY.unwrap(value)
		self._cobjectCache[name] = (value, c_value)
		setattr(self._cobject, name, c_value)
	return property(getter, setter_ro if readonly else setter_rw)

def caccessor( method, readonly=True ):
	"""A variant of `cproperty` that does not allow to set the value."""
	return cproperty(method, readonly=True)

# EOF - vim: ts=4 sw=4 noet
