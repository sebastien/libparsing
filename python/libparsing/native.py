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

import ctypes, os, re, sys, weakref

IS_PYTHON3 = sys.version_info[0] >= 3

__doc__ = """
An abstraction of `ctypes` that allows for the development of object-oriented
bindings to C code written in an object-oriented style (à la glib).
"""

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
	}

	CACHE = weakref.WeakValueDictionary()

	@classmethod
	def String( cls, value ):
		"""Ensures that the given value is a CString"""
		if IS_PYTHON3:
			# In Python3, ctypes requires bytes instead of str and does not
			# do any automatic casting. So we need to store it.
			wrapped = value.encode("utf-8") if isinstance(value, str) else value
			assert isinstance(wrapped, bytes)
			return wrapped
		else:
			# In Python2, strings are bytes from the get-go so they're
			# simply passed as-is
			return value

	@classmethod
	def Unwrap( cls, value ):
		# CObject might be garbage collected at this time
		if CObject and isinstance(value, CObject):
			return value._wrapped
		if not CObject and hasattr( value, "_wrapped"):
			return value._wrapped
		if isinstance(value, str):
			return cls.String(value)
		else:
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
	`CObject` subclasses register themselves."""

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
		self._cdll   = self.Load(path)
		self.symbols = CLibrary.Symbols()

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
		return self

	def wrap( self, cValue ):
		"""Wraps the given C value in a Python object."""
		return C.Wrap(cValue)

	def unwrap( self, wrapped):
		"""Returns a C value corresponding to the given (wrapped) value."""
		return C.Unwrap(wrapped)


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
			value = self.LIBRARY.unwrap(value)
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
			# print ("F: ", proto[0], args, "→", u_args, ":", ctypesFunction.argtypes, "→", ctypesFunction.restype)
			res  = ctypesFunction(*u_args)
			if not is_constructor:
				# Non-constructors must wrap the result
				res  = cls.LIBRARY.wrap(res)
			# print ("F=>", res)
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
			assert args[0], "CObject: method {0} `this` is None in {1}".format(proto[0], self)
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
		"""Wraps the given object in this CObject. The given
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

# EOF - vim: ts=4 sw=4 noet
