#!/usr/bin/env python3
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 18-Dec-2014
# Last modification : 22-Feb-2017
# -----------------------------------------------------------------------------

import sys
import os
import re
import inspect
import tempfile
import collections
from cffi import FFI
from os.path import dirname, join, abspath
from . import _buildext

__doc__ = """
The CFFI-based Python wrapper for libparsing.
"""

# TODO: Switch to pre-compilation
# TODO: Use global callbacks http://cffi.readthedocs.io/en/latest/using.html#id3

import logging

try:
    import reporter as rep

    # Wrapper to make reporter compatible with standard logging
    class LogWrapper:
        def info(self, msg, *args, **kwargs):
            rep.info(msg, "libparsing")

        def warning(self, msg, *args, **kwargs):
            rep.warning(msg, "libparsing")

        def error(self, msg, *args, **kwargs):
            rep.error(msg, "libparsing")

        def critical(self, msg, *args, **kwargs):
            rep.critical(msg, "libparsing")

    logging = LogWrapper()
except ImportError:
    import logging

VERSION = "0.9.3"
LICENSE = "http://ffctn.com/doc/licenses/bsd"
PACKAGE_PATH = dirname(abspath(__file__))

MatchTuple = collections.namedtuple("MatchTuple", "offset length id element")

# -----------------------------------------------------------------------------
#
# FFI
#
# -----------------------------------------------------------------------------

ffi = None
lib = None
LIBPARSING_FFI = (
    join(PACKAGE_PATH, "_libparsing.ffi")
    if os.path.exists(join(PACKAGE_PATH, "_libparsing.ffi"))
    else None
)
LIBPARSING_EXT = None
LIBPARSING_SO = None
LIBRARY_EXTS = ("so", "dylib", "dll")

# We check if there is a _libparsing SO/DYLIB/DLL file. If not, we need to
# build it using CFFI.

if (
    len(
        [
            _
            for _ in LIBRARY_EXTS
            if os.path.exists(join(PACKAGE_PATH, _buildext.filename(_)))
        ]
    )
    == 0
):
    logging.info("Building native libparsing Python bindings‥")
    try:
        _buildext.build()
    except Exception as e:
        logging.warning("Could not build Python extension: %s", e)

# Now we look for the actual Python extension (_libparsing
# We need to support different extensions and different prefixes. CFFI
# will build extensions as " _libparsing.cpython-35m-x86_64-linux-gnu.so"
# on Linux.
PREFIX_EXT = _buildext.name() + "."
PREFIX_SO = "libparsing."
for p in os.listdir(PACKAGE_PATH):
    if p.startswith(PREFIX_EXT) and p.rsplit(".", 1)[-1] in LIBRARY_EXTS:
        LIBPARSING_EXT = os.path.join(PACKAGE_PATH, p)
    if p.startswith(PREFIX_SO) and p.rsplit(".", 1)[-1] in LIBRARY_EXTS:
        LIBPARSING_SO = os.path.join(PACKAGE_PATH, p)

# Try to use dlopen mode first
if LIBPARSING_SO and LIBPARSING_FFI:
    try:
        ffi = FFI()
        with open(LIBPARSING_FFI, "r") as f:
            ffi.cdef(f.read())
        lib = ffi.dlopen(LIBPARSING_SO)
    except Exception as e:
        logging.warning("Could not load with FFI, trying alternative: %s", e)
        lib = None
        ffi = None

# Fallback: try to use extension module
if not lib and LIBPARSING_EXT:
    try:
        import importlib

        libparsing_ext = importlib.import_module("libparsing." + _buildext.name())
        lib = libparsing_ext.lib
        ffi = libparsing_ext.ffi
    except Exception as e:
        logging.warning("Could not load extension module: %s", e)
        lib = None
        ffi = None

if not lib:
    raise AssertionError(
        "libparsing: Cannot find libparsing.{{so,dll,dylib}} or _libparsing[.*].{{so,dll,dylib}} in package {0}".format(
            PACKAGE_PATH
        )
    )

# For backwards compatibility, expose ffi and lib as C and LIB
C = ffi
LIB = lib

# symbols points to lib for backwards compatibility
symbols = lib

# Direct function exports for backwards compatibility (only if lib loaded)
if lib is not None:
    # Wrap Reference_FromElement to accept both C objects and Python wrappers
    # and return a Python Reference object
    def Reference_FromElement(element):
        if hasattr(element, "_cobject"):
            cobj = lib.Reference_FromElement(element._cobject)
        else:
            cobj = lib.Reference_FromElement(element)
        return Reference.Wrap(cobj) if cobj != ffi.NULL else None

    def Reference_new():
        return lib.Reference_new()

    def Reference_hasElement(ref):
        if hasattr(ref, "_cobject"):
            return lib.Reference_hasElement(ref._cobject)
        return lib.Reference_hasElement(ref)

    def Reference_hasNext(ref):
        if hasattr(ref, "_cobject"):
            return lib.Reference_hasNext(ref._cobject)
        return lib.Reference_hasNext(ref)

    def Grammar_new():
        return lib.Grammar_new()

    def Grammar_parseString(g, text):
        if hasattr(g, "_cobject"):
            return lib.Grammar_parseString(g._cobject, text)
        return lib.Grammar_parseString(g, text)

    def Word_new(text):
        return lib.Word_new(text)

    def Rule_new(null_ptr):
        if null_ptr is None:
            return lib.Rule_new(ffi.NULL)
        return lib.Rule_new(null_ptr)

    def ParsingElement_add(element, ref):
        if hasattr(element, "_cobject"):
            return lib.ParsingElement_add(element._cobject, ref)
        return lib.ParsingElement_add(element, ref)


# Add TYPES dict for backwards compatibility with ctypes-style tests
if ffi is not None:
    try:
        ffi.TYPES = {
            "Element*": ffi.typeof("Element*"),
            "ParsingElement*": ffi.typeof("ParsingElement*"),
            "ParsingResult*": ffi.typeof("ParsingResult*"),
            "Match*": ffi.typeof("Match*"),
            "Grammar*": ffi.typeof("Grammar*"),
            "Reference*": ffi.typeof("Reference*"),
            "ParsingContext*": ffi.typeof("ParsingContext*"),
        }
    except (AttributeError, TypeError):
        # FFI object from compiled extension may not allow setting attributes
        pass

# -----------------------------------------------------------------------------
#
# GLOBALS
#
# -----------------------------------------------------------------------------

NOTHING = re
CARDINALITY_OPTIONAL = b"?"
CARDINALITY_ONE = b"1"
CARDINALITY_MANY_OPTIONAL = b"*"
CARDINALITY_MANY = b"+"
CARDINALITY_NOT_EMPTY = b"="
TYPE_WORD = b"W"
TYPE_TOKEN = b"T"
TYPE_GROUP = b"G"
TYPE_RULE = b"R"
TYPE_CONDITION = b"c"
TYPE_PROCEDURE = b"p"
TYPE_REFERENCE = b"#"
STATUS_INIT = b"-"
STATUS_PROCESSING = b"~"
STATUS_MATCHED = b"Y"
STATUS_FAILED = b"X"
STATUS_INPUT_ENDED = b"."
STATUS_ENDED = b"E"
ID_BINDING = -1
ID_UNBOUND = -10


def ensure_bytes(v):
    """Makes sure that this returns a byte string."""
    return v.encode("utf8") if isinstance(v, str) else v


def ensure_cstring(v):
    """Makes sure this returns a string that can be passed to C (a bytes string)"""
    return v.encode("utf8") if isinstance(v, str) else v.decode("utf8").encode("utf8")


def ensure_str(v):
    """Ensures the result is a string."""
    return v.decode("utf8") if isinstance(v, bytes) else v


def ensure_unicode(v):
    """Ensures the result is an unicode string(str)"""
    return v.decode("utf8") if isinstance(v, bytes) else v


def ensure_string(v):
    """Ensures the result is the default unicode string type (str)"""
    return ensure_unicode(v)


def is_string(v):
    return isinstance(v, str) or isinstance(v, bytes)


# -----------------------------------------------------------------------------
#
# FAST MATCH (lightweight wrapper for the processing hot path)
#
# -----------------------------------------------------------------------------


class _FastMatch:
    """Ultra-lightweight Match wrapper for the processing hot path.

    No inheritance, no __dict__, no __del__. Uses __slots__ for minimal
    memory footprint and fast attribute access. Only provides the methods
    that handlers actually need: group() and __getitem__.
    """

    __slots__ = ("_cobject", "_result", "_cached_group")

    def __init__(self, cobject, result_ref):
        self._cobject = cobject
        self._result = result_ref

    def group(self, index=0):
        # Fast path: return cached groups if available (set by _fastHandled)
        try:
            return self._cached_group
        except AttributeError:
            pass
        # Slow path: extract from C
        t = self._cobject.element.type
        if t == b"T":
            n = lib.TokenMatch_count(self._cobject)
            groups = [
                ensure_unicode(ffi.string(lib.TokenMatch_group(self._cobject, i)))
                for i in range(n)
            ]
            self._cached_group = groups
            return groups
        elif t == b"W":
            v = lib.WordMatch_group(self._cobject)
            groups = [ensure_unicode(ffi.string(v))] if v != ffi.NULL else []
            self._cached_group = groups
            return groups
        elif t == b"R" or t == b"G":
            result = []
            child = self._cobject.children
            while child != ffi.NULL:
                child_match = _FastMatch(child, self._result)
                result.extend(child_match.group())
                child = child.next
            return result
        elif t == b"#":
            child = self._cobject.children
            if child != ffi.NULL:
                child_match = _FastMatch(child, self._result)
                return child_match.group()
            return []
        return []

    def __getitem__(self, index):
        if isinstance(index, int):
            if index < 0:
                # Count children first for negative index
                count = 0
                child = self._cobject.children
                while child != ffi.NULL:
                    count += 1
                    child = child.next
                index = count + index
            i = 0
            child = self._cobject.children
            while child != ffi.NULL:
                if i == index:
                    return _FastMatch(child, self._result)
                child = child.next
                i += 1
            raise IndexError("Index {0} out of range".format(index))
        raise TypeError(
            "_FastMatch indices must be integers, not {0}".format(type(index).__name__)
        )

    def __iter__(self):
        child = self._cobject.children
        while child != ffi.NULL:
            yield _FastMatch(child, self._result)
            child = child.next

    @property
    def name(self):
        name = lib.Match_getElementName(self._cobject)
        return ensure_str(ffi.string(name)) if name else None

    @property
    def element(self):
        return self._cobject.element


# -----------------------------------------------------------------------------
#
# C OJBECT ABSTRACTION
#
# -----------------------------------------------------------------------------

__all__ = [
    # Classes
    "Grammar",
    "ParsingElement",
    "Word",
    "Token",
    "Group",
    "Rule",
    "Condition",
    "Procedure",
    "Reference",
    "Match",
    "MatchResult",
    "ParsingContext",
    "ParsingResult",
    "ParsingStats",
    "Processor",
    # Constants
    "VERSION",
    "LICENSE",
    "CARDINALITY_OPTIONAL",
    "CARDINALITY_ONE",
    "CARDINALITY_MANY_OPTIONAL",
    "CARDINALITY_MANY",
    "CARDINALITY_NOT_EMPTY",
    "TYPE_WORD",
    "TYPE_TOKEN",
    "TYPE_GROUP",
    "TYPE_RULE",
    "TYPE_CONDITION",
    "TYPE_PROCEDURE",
    "TYPE_REFERENCE",
    "STATUS_INIT",
    "STATUS_PROCESSING",
    "STATUS_MATCHED",
    "STATUS_FAILED",
    "STATUS_INPUT_ENDED",
    "STATUS_ENDED",
    "NOTHING",
    # Type aliases
    "RuleMatch",
    "TokenMatch",
    "GroupMatch",
    "ReferenceMatch",
    # Functions
    "Reference_FromElement",
]


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

    __slots__ = ("_cobject",)
    _TYPE = None
    _RECYCLER = None
    _RECYCLABLE = False

    @classmethod
    def Wrap(cls, cobject):
        return cls(cobject, wrap=cls.TYPE()) if cobject != ffi.NULL else None

    @classmethod
    def Recycle(cls, wrapped):
        if cls._RECYCLER is None:
            cls._RECYCLER = []
        wrapped._cobject = None
        cls._RECYCLER.append(wrapped)

    @classmethod
    def Reuse(cls, cobject):
        if cls._RECYCLER is None or len(cls._RECYCLER) == 0:
            return None
        else:
            o = cls._RECYCLER.pop()
            return o._repurpose(ffi.cast(cls.TYPE(), cobject))

    @classmethod
    def TYPE(cls):
        if not cls._TYPE:
            cls._TYPE = ffi.typeof(cls.__name__.rsplit(".")[-1] + "*")
        return cls._TYPE

    def __init__(self, *args, **kwargs):
        self._cobject = None
        self._init()
        if "wrap" in kwargs:
            # Allow 'wrap' and optionally 'result' for Match objects
            assert len(kwargs) <= 2, (
                "kwargs must contain 'wrap' and optionally 'result'"
            )
            assert len(args) == 1
            self._wrap(ffi.cast(kwargs["wrap"], args[0]))
        elif "empty" in kwargs:
            pass
        else:
            o = self._new(*args, **kwargs)
            if o is not None:
                self._cobject = ffi.cast(self.TYPE(), o)
            assert self._cobject

    def _init(self):
        pass

    def _new(self):
        raise NotImplementedError

    def _repurpose(self, cobject):
        assert cobject
        return self._wrap(cobject)

    def _wrap(self, cobject):
        assert self._cobject is None
        # assert isinstance(cobject, FFI.CData), "%s: Trying to wrap non CData value: %s" % (self.__class__.__name__, cobject)
        assert cobject != ffi.NULL, "%s: Trying to wrap NULL value: %s" % (
            self.__class__.__name__,
            cobject,
        )
        self._cobject = cobject
        return self

    def __del__(self):
        if self.__class__._RECYCLABLE:
            self.__class__.Recycle(self)


# -----------------------------------------------------------------------------
#
# PARSING ELEMENT
#
# -----------------------------------------------------------------------------


class ParsingElement(CObject):
    __slots__ = ("_name",)
    _TYPE = "ParsingElement*"

    @classmethod
    def IsCType(self, element):
        return isinstance(element, FFI.CData) and lib.ParsingElement_Is(element)

    def isReference(self):
        return False

    @property
    def name(self):
        name = self._cobject.name
        return ensure_str(ffi.string(name)) if name else None

    @name.setter
    def name(self, name):
        self._name = ensure_bytes(name)
        lib.ParsingElement_name(self._cobject, self._name)
        return self

    @property
    def id(self):
        return self._cobject.id

    @property
    def type(self):
        return self._cobject.type

    @property
    def children(self):
        child = self._cobject.children
        while child:
            ref = Reference.Wrap(child)
            yield ref
            child = ref._cobject.next

    def clear(self):
        # FIXME: This does not work
        lib.ParsingElement_clear(self._cobject)
        return self

    def set(self, *children):
        self.clear()
        return self.add(*children)

    def replace(self, index, *children):
        for c in children:
            assert isinstance(c, ParsingElement) or isinstance(c, Reference)
            lib.ParsingElement_replace(
                self._cobject, index, lib.Reference_Ensure(c._cobject)
            )
            index += 1
        return self

    def insert(self, index, *children):
        for c in children:
            assert isinstance(c, ParsingElement) or isinstance(c, Reference)
            lib.ParsingElement_insert(
                self._cobject, index, lib.Reference_Ensure(c._cobject)
            )
            index += 1
        return self

    def add(self, *children):
        for c in children:
            assert isinstance(c, ParsingElement) or isinstance(c, Reference)
            lib.ParsingElement_add(self._cobject, lib.Reference_Ensure(c._cobject))
        return self

    def prepend(self, *children):
        children_list = list(self.children)
        self.clear()
        self.add(*children)
        self.add(*children_list)
        return self

    def _as(self, name):
        self._name = ensure_bytes(name)
        return Reference(self)._as(self._name)

    def optional(self):
        return Reference(self).optional()

    def notEmpty(self):
        return Reference(self).notEmpty()

    def zeroOrMore(self):
        return Reference(self).zeroOrMore()

    def oneOrMore(self):
        return Reference(self).oneOrMore()

    def disableMemoize(self):
        return self

    def disableFailMemoize(self):
        return self

    def skip(self, value=True):
        # TODO: Implement me
        return self

    def noskip(self):
        self.skip(False)
        return self

    def slots(self):
        child = self._cobject.children
        res = []
        while child:
            ref = Reference.Wrap(child)
            name = ref.name
            if name:
                res.append(name)
            child = ref._cobject.next
        return res

    def indexForKey(self, name):
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
                classname, ensure_str(self.type), ensure_str(self.name), self.id
            )


# -----------------------------------------------------------------------------
#
# WORD
#
# -----------------------------------------------------------------------------


class Word(ParsingElement):
    __slots__ = ("_word",)

    def _new(self, word):
        self._word = ensure_bytes(word)
        return lib.Word_new(self._word)


# -----------------------------------------------------------------------------
#
# TOKEN
#
# -----------------------------------------------------------------------------


class Token(ParsingElement):
    __slots__ = ("_token",)

    def _new(self, token):
        self._token = ensure_bytes(token)
        return lib.Token_new(self._token)


# -----------------------------------------------------------------------------
#
# GROUP
#
# -----------------------------------------------------------------------------


class Group(ParsingElement):
    __slots__ = ()

    def _new(self, *children):
        self._cobject = lib.Group_new(ffi.NULL)
        self.add(*children)


# -----------------------------------------------------------------------------
#
# RULE
#
# -----------------------------------------------------------------------------


class Rule(ParsingElement):
    __slots__ = ()

    def _new(self, *children):
        self._cobject = lib.Rule_new(ffi.NULL)
        self.add(*children)


# -----------------------------------------------------------------------------
#
# CONDITION
#
# -----------------------------------------------------------------------------


class Condition(ParsingElement):
    __slots__ = ("_callback",)

    @classmethod
    def WrapCallback(cls, callback):
        # SEE: http://stackoverflow.com/questions/34392109/use-extern-python-style-cffi-callbacks-with-embedded-pypy
        def c(e, ctx):
            return (
                callback(ParsingElement.Wrap(e), ParsingContext.Wrap(ctx))
                if callback
                else 1
            )

        t = "bool(*)(ParsingElement *, ParsingContext *)"
        c = ffi.callback(t, c)
        return c

    def _new(self, callback):
        self._callback = (self.WrapCallback(callback), callback)
        return lib.Condition_new(self._callback[0])


# -----------------------------------------------------------------------------
#
# PROCEDURE
#
# -----------------------------------------------------------------------------


class Procedure(ParsingElement):
    __slots__ = ("_callback",)

    @classmethod
    def WrapCallback(cls, callback):
        def c(e, ctx):
            callback(ParsingElement.Wrap(e), ParsingContext.Wrap(ctx))

        t = "void(*)(ParsingElement *, ParsingContext *)"
        c = ffi.callback(t, c)
        return c

    def _new(self, callback):
        self._callback = (self.WrapCallback(callback), callback)
        return lib.Procedure_new(self._callback[0])


# -----------------------------------------------------------------------------
#
# REFERENCE
#
# -----------------------------------------------------------------------------


class Reference(CObject):
    __slots__ = ("_element", "_name")

    @classmethod
    def IsCType(self, element):
        return isinstance(element, FFI.CData) and lib.Reference_Is(element)

    def _new(self, element):
        assert isinstance(element, ParsingElement)
        assert element._cobject
        r = lib.Reference_FromElement(element._cobject)
        self._element = element
        assert r.element == element._cobject, (
            "Reference element should be {0}, got {1}".format(
                element._cobject, r.element
            )
        )
        return r

    # =========================================================================
    # ACCESSORS
    # =========================================================================

    @property
    def name(self):
        return (
            ensure_str(ffi.string(self._cobject.name))
            if self._cobject.name != ffi.NULL
            else None
        )

    @property
    def id(self):
        return self._cobject.id

    @property
    def element(self):
        return ParsingElement.Wrap(self._cobject.element)

    @property
    def type(self):
        return TYPE_REFERENCE

    # =========================================================================
    # API
    # =========================================================================

    def _as(self, name):
        self._name = ensure_bytes(name)
        lib.Reference_name(self._cobject, self._name)
        return self

    def one(self):
        lib.Reference_cardinality(self._cobject, CARDINALITY_ONE)
        return self

    def optional(self):
        lib.Reference_cardinality(self._cobject, CARDINALITY_OPTIONAL)
        return self

    def zeroOrMore(self):
        lib.Reference_cardinality(self._cobject, CARDINALITY_MANY_OPTIONAL)
        return self

    def oneOrMore(self):
        lib.Reference_cardinality(self._cobject, CARDINALITY_MANY)
        return self

    def notEmpty(self):
        lib.Reference_cardinality(self._cobject, CARDINALITY_NOT_EMPTY)
        return self

    # =========================================================================
    # HELPERS
    # =========================================================================

    def cardinality(self):
        return self._cobject.cardinality

    def isReference(self):
        return True

    def isOne(self):
        return self.cardinality() == CARDINALITY_ONE

    def isZeroOrMore(self):
        return self.cardinality() == CARDINALITY_MANY_OPTIONAL

    def isOneOrMore(self):
        return self.cardinality() == CARDINALITY_MANY

    def isOptional(self):
        return self.cardinality() == CARDINALITY_OPTIONAL

    def isMany(self):
        return self.isZeroOrMore() or self.isOneOrMore()

    def __repr__(self):
        return "<{0} {1}@{2}→{3}>".format(
            self.__class__.__name__.rsplit(".", 1)[-1],
            self.id,
            ensure_str(self.name),
            self.element,
        )

    def __del__(self):
        super().__del__()
        # References are managed by the grammar, you should not create
        # them directly, so we don't need to free them either.
        pass


# -----------------------------------------------------------------------------
#
# MATCH
#
# -----------------------------------------------------------------------------


class Match(CObject):
    __slots__ = ("_result", "_cached_group")
    _TYPE = ffi.typeof("Match*")
    _RECYCLABLE = False

    @classmethod
    def Wrap(cls, cobject, result=None):
        assert cobject.element != ffi.NULL, (
            "Match C object does not have an element: %s %d+%d"
            % (cobject.status, cobject.offset, cobject.length)
        )
        return cls.Reuse(cobject) or Match(cobject, wrap=cls._TYPE, result=result)

    @classmethod
    def _FastWrap(cls, cobject, result_ref):
        """Fast factory for the processing hot path. Skips asserts and kwargs parsing."""
        obj = cls.__new__(cls)
        obj._cobject = cobject
        obj._result = result_ref
        return obj

    def _new(self, o, **kwargs):
        return ffi.cast(self._TYPE, o)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store reference to ParsingResult to prevent garbage collection
        # of the C memory backing this match
        self._result = kwargs.get("result")

    # =========================================================================
    # ACCESSORS
    # =========================================================================

    @property
    def element(self):
        return self._cobject.element

    @property
    def offset(self):
        return self._cobject.offset

    @property
    def line(self):
        return self._cobject.line

    @property
    def type(self):
        return lib.Match_getType(self._cobject)

    @property
    def name(self):
        name = lib.Match_getElementName(self._cobject)
        return ensure_str(ffi.string(name)) if name else None

    @property
    def id(self):
        return lib.Match_getElementID(self._cobject)

    @property
    def length(self):
        return self._cobject.length

    @property
    def status(self):
        return self._cobject.status

    @property
    def value(self):
        t = self.type
        if t == TYPE_REFERENCE:
            # For references, get value from the first child
            if self.hasChildren():
                return self[0].value
            return None
        elif t == TYPE_WORD:
            group_str = lib.WordMatch_group(self._cobject)
            if group_str == ffi.NULL:
                return None
            return ensure_unicode(ffi.string(group_str))
        elif t == TYPE_TOKEN:
            n = lib.TokenMatch_count(self._cobject)
            if n == 0:
                return None
            group_str = lib.TokenMatch_group(self._cobject, 0)
            return ensure_unicode(ffi.string(group_str)) if group_str else None
        return None

    def group(self, index=0):
        # Fast path: return cached groups if available (set by _fastHandled)
        cached = getattr(self, "_cached_group", None)
        if cached is not None:
            return cached
        # Return list of matched values for this element
        # For backwards compatibility, return a list containing just the value
        t = self.type
        if t == TYPE_REFERENCE:
            # For references, recursively get groups from children
            if self.hasChildren():
                result = []
                for child in self:
                    result.extend(child.group())
                return result
            return []
        elif t == TYPE_WORD:
            v = self.value
            return [v] if v else []
        elif t == TYPE_TOKEN:
            n = lib.TokenMatch_count(self._cobject)
            return [
                ensure_unicode(ffi.string(lib.TokenMatch_group(self._cobject, i)))
                for i in range(n)
            ]
        elif t == TYPE_RULE or t == TYPE_GROUP:
            result = []
            for child in self:
                result.extend(child.group())
            return result
        return []

    @property
    def range(self):
        offset = self.offset or 0
        length = self.length or 0
        return offset, offset + length

    def getOffset(self):
        return self.offset

    def getLength(self):
        return self.length

    @property
    def next(self):
        if self._cobject.next == ffi.NULL:
            return None
        return Match.Wrap(self._cobject.next, result=self._result)

    @property
    def children(self):
        return list(self)

    def get(self, key=None):
        if key is None:
            return {s.name: self[s.name] for s in self if s.name}
        else:
            return self[key]

    def slots(self):
        return list(_ for _ in self if _.name)

    def indexForKey(self, name):
        for i, _ in enumerate(self):
            if _.name == name:
                return i
        return -1

    def hasChildren(self):
        return lib.Match_hasChildren(self._cobject)

    def countChildren(self):
        """Returns the number of children."""
        count = 0
        child = self._cobject.children
        while child:
            child = child.next
            count += 1
        return count

    def _toHelper(self, callback):
        (fd, fn) = tempfile.mkstemp()
        callback(self._cobject, fd)
        os.close(fd)
        with open(fn) as f:
            text = f.read()
        os.unlink(fn)
        return text

    def toJSON(self):
        return self._toHelper(lib.Match_writeJSON)

    def toXML(self):
        return self._toHelper(lib.Match_writeXML)

    # =========================================================================
    # SUGAR
    # =========================================================================

    def __iter__(self):
        child = self._cobject.children
        while child:
            yield Match.Wrap(child, result=self._result)
            child = child.next

    def __getitem__(self, index):
        if isinstance(index, int):
            # We correct the index
            if index < 0:
                index = self.countChildren() + index
            # We do a while iteration so that we don't wrap unncessary children
            i = 0
            child = self._cobject.children
            while child:
                if i == index:
                    return Match.Wrap(child, result=self._result)
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
                self.__class__.__name__.rsplit(".", 1)[-1], id(self)
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

    def __del__(self):
        # Matches are managed by ParsingResult (arena allocated), so we don't
        # need to free them. This is intentionally a no-op to avoid the
        # overhead of the parent class recyclable check.
        pass


# -----------------------------------------------------------------------------
#
# MATCH TYPE ALIASES (for backwards compatibility)
# -----------------------------------------------------------------------------

RuleMatch = Match
TokenMatch = Match
GroupMatch = Match
ReferenceMatch = Match

# -----------------------------------------------------------------------------
#
# MATCH RESULT
#
# -----------------------------------------------------------------------------


class MatchResult(object):
    __slots__ = ("value", "match")

    def __init__(self, value, match):
        assert not isinstance(value, MatchResult)
        self.value = value
        self.match = match

    @property
    def name(self):
        return self.match.name

    @property
    def id(self):
        return self.match.id

    def group(self, index=0):
        return self[index]

    def __getitem__(self, index):
        if isinstance(index, int):
            if isinstance(self.value, list) or isinstance(self.value, tuple):
                if index < 0:
                    index += len(self.value)
                for i, c in enumerate(self.value):
                    if i == index:
                        return c
            elif index == 0:
                return self.value
            else:
                raise Exception("MatchResult has non-iterable result: {0}".format(self))
        else:
            i = self.match.indexForKey(index)
            if i == -1:
                raise Exception(
                    "MatchResult does not define slot {1}, options are {2}: {0}".format(
                        self, index, self.match.slots()
                    )
                )
            else:
                return self[i]

    def __repr__(self):
        return "<{0} {1}={2}>".format(
            self.__class__.__name__.rsplit(".", 1)[-1], self.match, self.value
        )


# -----------------------------------------------------------------------------
#
# SYMBOLS
#
# -----------------------------------------------------------------------------


class Symbols:
    def __setitem__(self, key, value):
        setattr(self, key, value)
        return value

    def __getitem__(self, key):
        return getattr(self, key)


# -----------------------------------------------------------------------------
#
# PARSING CONTEXT
#
# -----------------------------------------------------------------------------


class ParsingContext(CObject):
    __slots__ = ()
    _TYPE = ffi.typeof("ParsingContext*")

    def __init__(self, text=None, path=None):
        self._cobject = lib.ParsingContext_new(ffi.NULL, ffi.NULL)
        if self._cobject == ffi.NULL:
            raise Exception("Failed to create ParsingContext")

    @property
    def offset(self):
        return lib.ParsingContext_getOffset(self._cobject)

    @property
    def line(self):
        return self._cobject.iterator.lines

    def getVariableCount(self):
        return lib.ParsingContext_getVariableCount(self._cobject)

    def push(self):
        lib.ParsingContext_push(self._cobject)
        return self

    def pop(self):
        lib.ParsingContext_pop(self._cobject)
        return self

    def set(self, key, value):
        assert isinstance(value, int)
        lib.ParsingContext_setInt(self._cobject, ensure_cstring(key), value)
        return value

    def get(self, key):
        key_bytes = ensure_cstring(key)
        # Check if variable exists using void* get function
        if lib.ParsingContext_get(self._cobject, key_bytes) == ffi.NULL:
            return None
        return lib.ParsingContext_getInt(self._cobject, key_bytes)

    def __getitem__(self, offset):
        return lib.ParsingContext_charAt(self._cobject, offset)

    def __del__(self):
        super().__del__()
        # Parsing contexts are owned by parsing results, so we don't need
        # to free them
        pass


# -----------------------------------------------------------------------------
#
# PARSING RESULT
#
# -----------------------------------------------------------------------------


class ParsingResult(CObject):
    __slots__ = ("_text", "_path", "_grammar", "_context")
    _TYPE = ffi.typeof("ParsingResult*")

    @classmethod
    def Wrap(cls, cobject, text=None, path=None, grammar=None, context=None):
        res = super(ParsingResult, cls).Wrap(cobject)
        # NOTE: We keep refernces to the text, path, grammar and context,
        # in order for them not to be garbage-collected too early.
        if res:
            res._text = text
            res._path = path
            res._grammar = grammar
            res._context = context
        return res

    @property
    def status(self):
        return self._cobject.status

    @property
    def match(self):
        return Match.Wrap(self._cobject.match, result=self)

    @property
    def lastMatch(self):
        return MatchTuple(
            offset=self.lastMatchOffset,
            length=self.lastMatchLength,
            id=self.lastMatchElementID,
            element=self._grammar.symbol(self.lastMatchElementID)
            if self.lastMatchElementID != -1
            else None,
        )

    @property
    def lastMatchOffset(self):
        return self._cobject.context.lastMatchOffset

    @property
    def lastMatchLength(self):
        return self._cobject.context.lastMatchLength

    @property
    def lastMatchElementID(self):
        return self._cobject.context.lastMatchElementID

    @property
    def stats(self):
        return ParsingStats.Wrap(self._cobject.context.stats)

    @property
    def line(self):
        return self._cobject.context.iterator.lines

    @property
    def offset(self):
        return self._cobject.context.iterator.offset

    @property
    def remaining(self):
        return lib.ParsingResult_remaining(self._cobject)

    @property
    def textOffset(self):
        return lib.ParsingResult_textOffset(self._cobject)

    @property
    def text(self):
        return ensure_str(ffi.string(self._cobject.context.iterator.buffer))

    # =========================================================================
    # METHODS
    # =========================================================================

    def isSuccess(self):
        # For backwards compatibility, consider both SUCCESS and PARTIAL as success
        # This matches the old ctypes behavior where partial matches were considered successful
        return self.status == b"S" or self.status == b"p"

    def isFailure(self):
        return True if lib.ParsingResult_isFailure(self._cobject) != 0 else False

    def isPartial(self):
        return True if lib.ParsingResult_isPartial(self._cobject) != 0 else False

    def isComplete(self):
        # Complete means we parsed everything (not partial, not failure)
        return self.isSuccess() and not self.isPartial()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def lastMatchRange(self):
        match = self.lastMatch
        if match:
            offset = match.offset
            length = match.length
            return (offset, offset + length)
        else:
            return (self.textOffset, self.textOffset)

    def getContext(self, start=None, end=None, before=3, after=3):
        """Returns a triple `(before:[Line], current:Line, after:[Line])`
        around the start/end offsets"""
        if start is None or end is None:
            start, end = self.lastMatchRange()
        s = start
        e = end
        t = ensure_str(self.text)
        bt = t[0:s].rsplit("\n", before + 1)[-before - 1 :]
        at = t[e:].split("\n", after + 1)[: after + 1]
        c = bt[-1] + t[s:e] + at[0]
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
            lineLength=max(0, e - s),
        )

    def _asSpaces(self, line, char=" "):
        r = []
        for c in line:
            r.append(c if c in "\t" else char)
        return "".join(r)

    def formatContext(self, context):
        red = "[0m[01;31m"
        yellow = "[0m[01;33m"
        orange = "[0m[00;33m"
        reset = "[0m[00;00m"
        before = "\n│ " + "\n│ ".join(context["before"])
        after = "\n│ " + "\n│ ".join(context["after"])
        line = "\n└┐" + yellow + context["line"] + reset
        error = "\n┌┘" + (
            orange
            + self._asSpaces(context["lineBefore"], "▸")
            + red
            + self._asSpaces(context["lineMatch"], "▲")
            + reset
            + self._asSpaces(context["lineAfter"])
        )
        return "".join([before, line, error, after])

    def describe(self, context=3, color=True):
        """Returns a nicely formatted description of the error"""
        if self.isSuccess():
            return "Parsing successful"
        else:
            # m     = self.lastMatch
            # s,e   = self.lastMatchRange ()
            # l     = m.line
            # print ("LAST MATCH {0} line={1}, start={2}-{3}".format(m,l,s,e))
            m = self.lastMatch
            s, e = self.lastMatchRange()
            t = self.formatContext(self.getContext(before=context, after=context))
            lines = self.text[:s].split("\n")
            line = len(lines) - 1
            char = len(lines[-1])
            sym = (
                ", symbol " + str(self._grammar.symbol(m.id))
                if m and m.id and m.id >= 0
                else ""
            )
            return "Parsing failed at line {0} character {1}, offset {2}→{3}{4}:{5}".format(
                line, char, s, e, sym, "\n".join([_ for _ in t.split("\n")])
            )

    def toJSON(self):
        return self.match.toJSON()

    def toXML(self):
        return self.match.toXML()

    def __repr__(self):
        return "<{0}(status={2}, line={3}, char={4}, offset={5}, remaining={6}) at {1:02x}>".format(
            self.__class__.__name__,
            id(self),
            self.status,
            self.line,
            -1,
            self.offset,
            0,
        )

    def __del__(self):
        super().__del__()
        # The parsing result is the only one we really need to free
        # along with the grammar
        lib.ParsingResult_free(self._cobject)


# -----------------------------------------------------------------------------
#
# PARSING STATS
#
# -----------------------------------------------------------------------------


class ParsingStats(CObject):
    __slots__ = ()

    def bytesRead(self):
        return self._cobject.bytesRead

    def parseTime(self):
        return self._cobject.parseTime

    def totalSuccess(self):
        return sum(
            self._cobject.successBySymbol[i] for i in range(self._cobject.symbolsCount)
        )

    def totalFailures(self):
        return sum(
            self._cobject.failureBySymbol[i] for i in range(self._cobject.symbolsCount)
        )

    def symbolsCount(self):
        return self._cobject.symbolsCount

    def symbols(self):
        return [
            (i, self._cobject.successBySymbol[i], self._cobject.failureBySymbol[i])
            for i in range(self.symbolsCount())
        ]

    def report(self, grammar=None, output=sys.stdout):
        br = self.bytesRead()
        pt = self.parseTime()
        ts = self.totalSuccess()
        tf = self.totalFailures()

        def write(s):
            output.write(s)
            output.write("\n")

        write("Bytes read :  {0}".format(br))
        write("Parse time :  {0}s".format(pt))
        write("Throughput :  {0}Mb/s".format(br / 1024.0 / 1024.0 / pt))
        write("-" * 80)
        write("Sucesses   :  {0}".format(ts))
        write("Failures   :  {0}".format(tf))
        write("Throughput :  {0}op/s".format((ts + tf) / pt))
        write("Op time    : ~{0}/op".format(pt / (ts + tf)))
        write("Op/byte    :  {0}".format((ts + tf) / br))
        write("-" * 80)
        write("   SYMBOL   NAME                               SUCCESSES       FAILURES")
        s = sorted(self.symbols(), key=lambda x: -(x[1] + x[2]))
        c = 0
        ct = 0
        for sid, s, f in s:
            ct += 1
            if s == 0 and f == 0:
                continue
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
    __slots__ = ("name", "symbols", "_prepared", "_anonymous")
    _TYPE = ffi.typeof("Grammar*")

    def _new(self, name=None, isVerbose=False, axiom=None):
        self.name = name
        self.symbols = Symbols()
        g = lib.Grammar_new()
        self._cobject = ffi.cast(self.TYPE(), g)
        g.isVerbose = 1 if isVerbose else 0
        self._prepared = False
        self._anonymous = []
        # Set axiom after _cobject is initialized
        if axiom is not None:
            self.axiom = axiom
        return g

    # =========================================================================
    # PARSING
    # =========================================================================

    def parsePath(self, path):
        self._prepare()
        _path = ensure_cstring(ensure_unicode(path))
        return ParsingResult.Wrap(
            lib.Grammar_parsePath(self._cobject, _path),
            path=(path, _path),
            grammar=self,
        )

    def parseStream(self, stream):
        return self.parseString(stream.read())

    def parseString(self, text):
        self._prepare()
        _text = ensure_cstring(ensure_unicode(text))
        return ParsingResult.Wrap(
            lib.Grammar_parseString(self._cobject, _text),
            text=(text, _text),
            grammar=self,
        )

    # =========================================================================
    # AXIOM AND SKIPPING
    # =========================================================================

    @property
    def axiom(self):
        return self._cobject.axiom

    @axiom.setter
    def axiom(self, axiom):
        self._prepared = False
        if isinstance(axiom, Reference):
            axiom = axiom._cobject.element
            assert axiom
        assert isinstance(axiom, ParsingElement)
        self._cobject.axiom = axiom._cobject
        return self

    @property
    def skip(self):
        return self._cobject.skip

    @skip.setter
    def skip(self, skip):
        self._prepared = False
        assert isinstance(skip, ParsingElement)
        self._cobject.skip = skip._cobject
        return self

    # =========================================================================
    # FACTORY METHODS
    # =========================================================================

    def word(self, name, word):
        self._prepared = False
        r = Word(word)
        r.name = name
        self.symbols[name] = r
        return r

    def aword(self, word):
        self._prepared = False
        return self._registerAnonymous(Word(word))

    def token(self, name, token):
        self._prepared = False
        r = Token(token)
        r.name = name
        self.symbols[name] = r
        return r

    def atoken(self, token):
        self._prepared = False
        return self._registerAnonymous(Token(token))

    def procedure(self, name, callback):
        self._prepared = False
        r = Procedure(callback)
        r.name = name
        self.symbols[name] = r
        return r

    def aprocedure(self, callback):
        self._prepared = False
        return self._registerAnonymous(Procedure(callback))

    def condition(self, name, callback=None):
        self._prepared = False
        r = Condition(callback)
        r.name = name
        self.symbols[name] = r
        return r

    def acondition(self, callback=None):
        self._prepared = False
        return self._registerAnonymous(Condition(callback))

    def group(self, name, *children):
        self._prepared = False
        r = Group(*children)
        r.name = name
        self.symbols[name] = r
        return r

    def agroup(self, *children):
        self._prepared = False
        return self._registerAnonymous(Group(*children))

    def rule(self, name, *children):
        self._prepared = False
        r = Rule(*children)
        r.name = name
        self.symbols[name] = r
        return r

    def arule(self, *children):
        self._prepared = False
        return self._registerAnonymous(Rule(*children))

    def _registerAnonymous(self, element):
        """Forces the grammar to keep references to anonymous symbols it
        created."""
        self._anonymous.append(element)
        return element

    # =========================================================================
    # META / HELPERS
    # =========================================================================

    def setVerbose(self, verbose=True):
        # FIXME: That cast should not be necessary
        e = ffi.cast("Grammar*", self._cobject)
        e.isVerbose = 1 if verbose else 0
        return self

    @property
    def isVerbose(self):
        # FIXME: That cast should not be necessary
        e = ffi.cast("Grammar*", self._cobject)
        return e.isVerbose == 1

    @isVerbose.setter
    def isVerbose(self, value):
        e = ffi.cast("Grammar*", self._cobject)
        e.isVerbose = 1 if value else 0

    def symbol(self, id):
        if type(id) is int:
            e = ffi.cast("Reference*", self._cobject.elements[id])
            if e.type == TYPE_REFERENCE:
                return Reference.Wrap(e)
            else:
                return ParsingElement.Wrap(e)
        else:
            return getattr(self.symbols, id)

    def list(self):
        """Lists the symbols defined in the grammar."""
        res = []
        for k in dir(self.symbols):
            if k.startswith("__"):
                continue
            res.append((k, getattr(self.symbols, k)))
        return res

    def _prepare(self):
        """Ensures the grammar is prepared."""
        if not self._prepared:
            self.prepare()

    def prepare(self):
        lib.Grammar_prepare(self._cobject)
        self._prepared = True

    def __del__(self):
        super().__del__()
        # The parsing result is the only one we really need to free
        # along with the grammar
        if lib is not None and self._cobject is not None:
            lib.Grammar_free(self._cobject)


# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------


class Processor:
    LAZY = 0
    EAGER = 1

    def __init__(self, grammar=None, strict=True):
        self.depth = 0
        self._handler = None
        self.isStrict = strict
        self.strategy = self.LAZY
        # Check if postProcess is overridden (if not, we can skip calling it)
        self._hasPostProcess = type(self).postProcess is not Processor.postProcess
        self.setGrammar(self.ensureGrammar(grammar))
        self._defaults = dict(
            (k, getattr(self, v) if hasattr(self, v) else None)
            for (k, v) in {
                TYPE_WORD: "processWord",
                TYPE_TOKEN: "processToken",
                TYPE_GROUP: "processGroup",
                TYPE_RULE: "processRule",
                TYPE_CONDITION: "processCondition",
                TYPE_PROCEDURE: "processProcedure",
            }.items()
        )

    def on(self, symbol, handler):
        self.handlerByID[symbol.id] = handler
        return self

    def asEager(self):
        self.strategy = self.EAGER
        return self

    def asLazy(self):
        self.strategy = self.LAZY
        return self

    def ensureGrammar(self, grammar):
        return grammar or self.createGrammar()

    def createGrammar(self):
        raise NotImplementedError

    def setGrammar(self, grammar):
        self.symbols = grammar.list() if grammar else []
        self.symbolByName = {}
        self.symbolByID = {}
        self.handlerByID = {}
        self.grammar = grammar
        if self.grammar:
            # We prepare the grammar
            self.grammar.prepare()
        self._bindSymbols()
        self._bindHandlers()

    def _bindSymbols(self):
        for name, s in self.symbols:
            if not s:
                rep.error("Name without symbol: %s" % (name))
                continue
            self.symbolByName[name] = s
            if s.id in self.symbolByID:
                if s.id >= 0:
                    raise Exception(
                        "Duplicate symbol id: %d, has %s already while trying to assign %s"
                        % (s.id, self.symbolByID[s.id].name, s.name)
                    )
                elif self.isStrict:
                    logging.warn("Unused symbol: %s" % (repr(s)))
            self.symbolByID[s.id] = s

    def _bindHandlers(self):
        self._handlerInfo = {}  # {element_id: (raw_handler, slots_tuple)}
        self._fastByID = {}  # {element_id: fast_wrapper} for handlers with kwargs
        self._passthroughIDs = (
            set()
        )  # IDs of Group handlers that are pure pass-throughs
        for k in dir(self):
            if not k.startswith("on"):
                continue
            name = k[2:]
            if not name:
                continue
            assert not self.isStrict or name in self.symbolByName, (
                "Handler does not match any symbol: {0}, symbols are {1}".format(
                    k, ", ".join(self.symbolByName.keys())
                )
            )
            symbol = self.symbolByName.get(name)
            if symbol:
                raw_handler = getattr(self, k)
                # Store raw handler + slot info for flat buffer processing
                sig = inspect.getfullargspec(raw_handler)
                params = sig.args[0 : -len(sig.defaults)] if sig.defaults else sig.args
                params = params[1:] if params[0] == "self" else params
                slots = tuple((_, symbol.indexForKey(_)) for _ in params[1:])
                valid = tuple(_ for _ in slots if _[1] >= 0)
                self._handlerInfo[symbol.id] = (raw_handler, valid)
                # Detect pass-through Group handlers: signature (self, match) with
                # body that just returns self.process(match[0])
                if symbol.type == TYPE_GROUP and len(params) == 1:
                    try:
                        src = inspect.getsource(raw_handler)
                        # Strip decorators and def line, check body
                        lines = [
                            l.strip()
                            for l in src.split("\n")
                            if l.strip()
                            and not l.strip().startswith(
                                ("def ", "@", "#", '"""', "'''")
                            )
                        ]
                        if len(lines) == 1 and "self.process(match[0])" in lines[0]:
                            self._passthroughIDs.add(symbol.id)
                    except (OSError, TypeError):
                        pass
                h = self._createHandler(raw_handler, symbol)
                self.handlerByID[symbol.id] = h
                # Pre-extract fast wrapper for handlers with kwargs
                fast = getattr(h, "_fast", None)
                if fast is not None:
                    self._fastByID[symbol.id] = fast

    def _createHandler(self, handler, symbol):
        # We only bind the arguments listed
        sig = inspect.getfullargspec(handler)
        params = sig.args[0 : -len(sig.defaults)] if sig.defaults else sig.args
        params = params[1:] if params[0] == "self" else params
        slots = tuple((_, symbol.indexForKey(_)) for _ in params[1:])
        missing = tuple(_ for _ in slots if _[1] < 0)
        valid = tuple(_ for _ in slots if _[1] >= 0)
        if missing:
            raise Exception(
                "Handler {0} for {1} arguments do not match grammar: {2} should be a subset of {3}".format(
                    handler, symbol, missing, symbol.slots()
                )
            )
        elif valid:
            # Fast path: extract children from C pointer directly
            _pp = self._hasPostProcess

            def wrapper(match):
                kwargs = dict(
                    (name, self.process(match[index])) for (name, index) in valid
                )
                res = handler(match, **kwargs)
                return self.postProcess(match, res) if _pp else res

            # Also store a fast wrapper that can work on raw C pointers
            max_index = max(idx for _, idx in valid)

            # Generate a specialized positional-arg caller to avoid kwargs dict creation.
            # For handler(match, key, value) with valid=((key,0),(value,2)), we generate:
            #   handler(wrapped, children_values[0], children_values[2])
            # using compile/exec to create a direct positional call.
            _indices = tuple(idx for _, idx in valid)
            _n_valid = len(valid)

            if _n_valid == 1:
                _idx0 = _indices[0]

                if _pp:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        c = children[_idx0]
                        v0 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        wrapped = _FastMatch(cobj, result_ref)
                        return self.postProcess(wrapped, handler(wrapped, v0))
                else:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        c = children[_idx0]
                        v0 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        wrapped = _FastMatch(cobj, result_ref)
                        return handler(wrapped, v0)

            elif _n_valid == 2:
                _idx0 = _indices[0]
                _idx1 = _indices[1]

                if _pp:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        c = children[_idx0]
                        v0 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        wrapped = _FastMatch(cobj, result_ref)
                        return self.postProcess(wrapped, handler(wrapped, v0, v1))
                else:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        c = children[_idx0]
                        v0 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        wrapped = _FastMatch(cobj, result_ref)
                        return handler(wrapped, v0, v1)

            elif _n_valid == 3:
                _idx0 = _indices[0]
                _idx1 = _indices[1]
                _idx2 = _indices[2]

                if _pp:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        c = children[_idx0]
                        v0 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        c = children[_idx2]
                        v2 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        wrapped = _FastMatch(cobj, result_ref)
                        return self.postProcess(wrapped, handler(wrapped, v0, v1, v2))
                else:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        c = children[_idx0]
                        v0 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        c = children[_idx2]
                        v2 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else None
                        )
                        wrapped = _FastMatch(cobj, result_ref)
                        return handler(wrapped, v0, v1, v2)

            else:
                # Generic fallback for 4+ kwargs (rare)
                if _pp:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        vals = []
                        for _, index in valid:
                            c = children[index]
                            if c is not None and c != ffi.NULL:
                                vals.append(self._fastProcess(c, result_ref))
                            else:
                                vals.append(None)
                        wrapped = _FastMatch(cobj, result_ref)
                        return self.postProcess(wrapped, handler(wrapped, *vals))
                else:

                    def fast_wrapper(cobj, result_ref):
                        children = [None] * (max_index + 1)
                        child = cobj.children
                        ci = 0
                        while child != ffi.NULL and ci <= max_index:
                            children[ci] = child
                            child = child.next
                            ci += 1
                        vals = []
                        for _, index in valid:
                            c = children[index]
                            if c is not None and c != ffi.NULL:
                                vals.append(self._fastProcess(c, result_ref))
                            else:
                                vals.append(None)
                        wrapped = _FastMatch(cobj, result_ref)
                        return handler(wrapped, *vals)

            wrapper._fast = fast_wrapper
            # Store metadata for flat buffer processing
            wrapper._raw_handler = handler
            wrapper._slots = valid
            return wrapper
        else:
            return handler

    def process(self, match):
        # Fast path: already-processed primitive values (most common case when
        # handlers call self.process(value) on pre-processed kwargs).
        # Avoids isinstance checks, depth tracking, and MatchResult check.
        if match is None or type(match) in (str, int, float, bool, dict, list, tuple):
            return match
        self.depth += 1
        match = match.match if isinstance(match, ParsingResult) else match
        if isinstance(match, (Match, _FastMatch)):
            result = self._fastProcess(match._cobject, match._result)
        else:
            result = match
        self.depth -= 1
        return result.value if isinstance(result, MatchResult) else result

    def postProcess(self, match, result):
        return result

    # =========================================================================
    # FLAT BUFFER PROCESSING
    # =========================================================================

    def _processFlatBuffer(self, cobj, result_ref):
        """Process a match tree using a flat buffer from C, minimizing FFI crossings.

        Flattens the C match tree into a contiguous array via a single C call,
        reads all node metadata into Python lists (batch FFI), then iteratively
        processes the pre-order traversal WITHOUT any further FFI struct access.

        Handlers are called with pre-processed children values using positional
        args, avoiding kwargs dict creation and handler re-entry overhead.
        """
        # Get the total node count (Match_countAll returns N-1, so add 1)
        nodeCount = lib.Match_countAll(cobj) + 1
        if nodeCount <= 1:
            return self._fastProcess(cobj, result_ref)

        # Allocate flat buffer and fill in one C call
        buf = ffi.new("MatchFlatNode[]", nodeCount)
        actual = lib.Match_flatten(cobj, buf, nodeCount)

        # Batch-read all node data into Python lists (one FFI crossing per field)
        types = [None] * actual
        ids = [None] * actual
        nchildren = [None] * actual
        isMany = [None] * actual
        wordValues = [None] * actual
        matches = [None] * actual

        _NULL = ffi.NULL
        for i in range(actual):
            node = buf[i]
            types[i] = node.type
            ids[i] = node.id
            nchildren[i] = node.numChildren
            isMany[i] = node.isMany != b"\x00"
            wordValues[i] = node.wordValue
            matches[i] = node.match

        # Pre-extract token groups for all Token nodes (batch the FFI calls)
        _TMcount = lib.TokenMatch_count
        _TMgroup = lib.TokenMatch_group
        _eu = ensure_unicode
        _fs = ffi.string
        token_groups = [None] * actual
        for i in range(actual):
            if types[i] == b"T":
                m = matches[i]
                n = _TMcount(m)
                if n > 0:
                    token_groups[i] = [_eu(_fs(_TMgroup(m, j))) for j in range(n)]

        # Pre-extract word values for all Word nodes
        word_strs = [None] * actual
        for i in range(actual):
            if types[i] == b"W":
                wv = wordValues[i]
                if wv != _NULL:
                    word_strs[i] = _eu(_fs(wv))

        # Cache lookups
        handlerInfo = self._handlerInfo
        passthroughIDs = self._passthroughIDs
        _hasPostProcess = self._hasPostProcess

        def process_node(idx):
            """Process node at index idx, return (result, next_index)."""
            t = types[idx]
            nc = nchildren[idx]

            if t == b"#":
                # Reference — unwrap (never has handlers)
                if nc == 0:
                    return None, idx + 1
                if not isMany[idx]:
                    return process_node(idx + 1)
                else:
                    result = []
                    ci = idx + 1
                    for _ in range(nc):
                        r, ci = process_node(ci)
                        result.append(r)
                    return result, ci

            nid = ids[idx]

            if t == b"W":
                r = word_strs[idx]
                info = handlerInfo.get(nid)
                if info:
                    raw_handler, slots = info
                    wrapped = _FastMatch(matches[idx], result_ref)
                    ph = self._handler
                    self._handler = raw_handler
                    r = raw_handler(wrapped)
                    self._handler = ph
                return r, idx + 1

            if t == b"T":
                r = token_groups[idx]
                info = handlerInfo.get(nid)
                if info:
                    raw_handler, slots = info
                    wrapped = _FastMatch(matches[idx], result_ref)
                    wrapped._cached_group = r if r else []
                    ph = self._handler
                    self._handler = raw_handler
                    r = raw_handler(wrapped)
                    self._handler = ph
                return r, idx + 1

            if t == b"c" or t == b"p":
                return True, idx + 1

            if t == b"G":
                # Group — process the single child first
                if nc == 0:
                    child_r = None
                    next_idx = idx + 1
                else:
                    child_r, next_idx = process_node(idx + 1)

                # Check for pass-through group (e.g., onValue)
                if nid in passthroughIDs:
                    return child_r, next_idx

                info = handlerInfo.get(nid)
                if info:
                    raw_handler, slots = info
                    wrapped = _FastMatch(matches[idx], result_ref)
                    ph = self._handler
                    self._handler = raw_handler
                    r = raw_handler(wrapped)
                    self._handler = ph
                    return r, next_idx
                return [child_r], next_idx

            if t == b"R":
                # Rule — process all children first, then call handler with
                # pre-processed values as positional args
                child_results = []
                ci = idx + 1
                for _ in range(nc):
                    child_r, ci = process_node(ci)
                    child_results.append(child_r)

                info = handlerInfo.get(nid)
                if info:
                    raw_handler, slots = info
                    wrapped = _FastMatch(matches[idx], result_ref)
                    ph = self._handler
                    self._handler = raw_handler
                    if slots:
                        # Handler with kwargs — extract slot values from children
                        # and pass as positional args
                        args = []
                        for param_name, slot_idx in slots:
                            if slot_idx < len(child_results):
                                args.append(child_results[slot_idx])
                            else:
                                args.append(None)
                        if _hasPostProcess:
                            r = self.postProcess(wrapped, raw_handler(wrapped, *args))
                        else:
                            r = raw_handler(wrapped, *args)
                    else:
                        # Simple handler (no kwargs)
                        r = raw_handler(wrapped)
                    self._handler = ph
                    return r, ci
                return child_results, ci

            raise Exception("Unsupported match type: {0}".format(t))

        result, _ = process_node(0)
        return result

    # =========================================================================
    # FAST PATH: Process raw C match pointers without creating Match wrappers
    # =========================================================================

    def _fastProcess(self, cobj, result_ref):
        """Process a raw C match pointer, dispatching by element type."""
        elem = cobj.element
        t = elem.type

        # Inline reference handling (most common type, ~47% of calls)
        # References never have handlers, so skip handler lookup entirely
        if t == b"#":
            if not lib.Reference_IsMany(elem):
                child = cobj.children
                if child != ffi.NULL:
                    return self._fastProcess(child, result_ref)
                return None
            else:
                result = []
                child = cobj.children
                _fp = self._fastProcess
                while child != ffi.NULL:
                    result.append(_fp(child, result_ref))
                    child = child.next
                return result

        # For Groups detected as pass-throughs, skip handler entirely
        # and return child result directly (same as what the handler does).
        # Clear _handler to allow nested handlers of the same type to fire.
        if t == b"G" and elem.id in self._passthroughIDs:
            child = cobj.children
            if child != ffi.NULL:
                saved_handler = self._handler
                self._handler = None
                r = self._fastProcess(child, result_ref)
                self._handler = saved_handler
                return r
            return None

        h = self.handlerByID.get(elem.id)

        if h and self._handler != h:
            # Handler registered — inline handler dispatch
            ph = self._handler
            self._handler = h
            fast = self._fastByID.get(elem.id)
            if fast is not None:
                res = fast(cobj, result_ref)
            else:
                # Simple handler (no kwargs) — wrap and call directly
                wrapped = _FastMatch(cobj, result_ref)
                # For TOKEN matches, pre-cache the group() result
                if t == b"T":
                    n = lib.TokenMatch_count(cobj)
                    if n > 0:
                        groups = [
                            ensure_unicode(ffi.string(lib.TokenMatch_group(cobj, i)))
                            for i in range(n)
                        ]
                    else:
                        groups = []
                    wrapped._cached_group = groups
                res = h(wrapped)
            self._handler = ph
            return res

        # No handler — inline the eager processing logic
        if t == b"W":
            return ensure_unicode(ffi.string(lib.WordMatch_group(cobj)))
        elif t == b"T":
            n = lib.TokenMatch_count(cobj)
            if n == 0:
                return None
            _tmg = lib.TokenMatch_group
            _eu = ensure_unicode
            _fs = ffi.string
            return [_eu(_fs(_tmg(cobj, i))) for i in range(n)]
        elif t == b"c" or t == b"p":
            return True
        elif t == b"G":
            child = cobj.children
            if child == ffi.NULL:
                return [None]
            return [self._fastProcess(child, result_ref)]
        elif t == b"R":
            result = []
            child = cobj.children
            _fp = self._fastProcess
            while child != ffi.NULL:
                result.append(_fp(child, result_ref))
                child = child.next
            return result
        else:
            raise Exception("Unsupported match type: {0}".format(t))

    def _fastHandled(self, cobj, t, h, result_ref):
        """Process a match that has a registered handler."""
        ph = self._handler
        self._handler = h
        # Check if handler has a fast wrapper (for handlers with kwargs)
        fast = getattr(h, "_fast", None)
        if fast is not None:
            res = fast(cobj, result_ref)
        else:
            # Simple handler (no kwargs) — wrap and call directly
            wrapped = _FastMatch(cobj, result_ref)
            # For TOKEN matches, pre-cache the group() result to avoid
            # redundant FFI calls when the handler accesses match.group()
            if t == b"T":
                n = lib.TokenMatch_count(cobj)
                if n > 0:
                    groups = [
                        ensure_unicode(ffi.string(lib.TokenMatch_group(cobj, i)))
                        for i in range(n)
                    ]
                else:
                    groups = []
                wrapped._cached_group = groups
            res = h(wrapped)
        self._handler = ph
        return res

    def _fastWord(self, cobj):
        group_str = lib.WordMatch_group(cobj)
        return ensure_unicode(ffi.string(group_str))

    def _fastToken(self, cobj):
        n = lib.TokenMatch_count(cobj)
        if n == 0:
            return None
        return [
            ensure_unicode(ffi.string(lib.TokenMatch_group(cobj, i))) for i in range(n)
        ]

    def _fastGroup(self, cobj, result_ref):
        child = cobj.children
        if child == ffi.NULL:
            return [None]
        return [self._fastProcess(child, result_ref)]

    def _fastRule(self, cobj, result_ref):
        result = []
        child = cobj.children
        while child != ffi.NULL:
            result.append(self._fastProcess(child, result_ref))
            child = child.next
        return result

    def _fastReference(self, cobj, result_ref):
        element = cobj.element
        if not lib.Reference_IsMany(element):
            child = cobj.children
            if child != ffi.NULL:
                return self._fastProcess(child, result_ref)
            return None
        else:
            result = []
            child = cobj.children
            while child != ffi.NULL:
                result.append(self._fastProcess(child, result_ref))
                child = child.next
            return result

    def _processMatch(self, match):
        if self.strategy == self.EAGER:
            return self._processEager(match)
        else:
            return self._processLazy(match)

    def _processEager(self, match, handler=True, default=True):
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
        h = (
            self.handlerByID.get(i)
            if handler
            else (self._defaults.get(t) if default else None)
        )
        r = h(MatchResult(r, match)) if h else r
        return r.value if isinstance(r, MatchResult) else r

    def _processLazy(self, match):
        """Processes a match element."""
        t = match.type
        i = match.id
        h = self.handlerByID.get(i)
        if not h or self._handler == h:
            # If there's no handler defined,then we apply the eager method. We only
            # use the default handler if there is no current handler matching the element
            return self._processEager(match, handler=False, default=not h)
        else:
            # If there is a handler defined
            ph = self._handler
            self._handler = h
            if (
                t == TYPE_WORD
                or t == TYPE_TOKEN
                or t == TYPE_CONDITION
                or t == TYPE_PROCEDURE
            ):
                res = h(match)
            else:
                res = h(match)
            self._handler = ph
            return res

    def _processWord(self, match):
        return ensure_unicode(ffi.string(lib.WordMatch_group(match._cobject)))

    def _processToken(self, match):
        n = lib.TokenMatch_count(match._cobject)
        if n == 0:
            return None
        else:
            return list(
                ensure_unicode(ffi.string(lib.TokenMatch_group(match._cobject, i)))
                for i in range(n)
            )

    def _processCondition(self, match):
        return True

    def _processProcedure(self, match):
        return True

    def _processGroup(self, match):
        # NOTE: We need to wrap this in a list so that proces(match[0]) work
        # for groups.
        return [self._processMatch(match[0])]

    def _processRule(self, match):
        return list(self._processMatch(_) for _ in match)

    def _processReference(self, match):
        if not lib.Reference_IsMany(match.element):
            res = self._processMatch(match[0]) if match.hasChildren() else None
            return res
        else:
            return list(self._processMatch(_) for _ in match)


class TreeWriter(Processor):
    """A special processor that outputs the named parsing elements
    registered in the parse tree. It is quite useful for debugging grammars."""

    def __init__(self, grammar=None, output=sys.stdout):
        Processor.__init__(self, grammar)
        self.output = output
        self.reset()

    def reset(self):
        self.indent = 0
        self.count = 0

    def defaultProcess(self, match):
        named = (
            isinstance(match.element(), ParsingElement)
            and match.element().name() != "_"
        )
        if named:
            self.output.write(
                "{0:04d}|{1}{2}\n".format(
                    self.count, self.indent * "    " + "|---", match.element().name()
                )
            )
            self.indent += 1
        self.count += 1
        r = Processor.defaultProcess(self, match)
        if named:
            self.indent -= 1
        return r


class Indentation(object):
    VALUES = {
        " ": 1,
        "\t": 4,
    }

    @classmethod
    def Indent(self, element, context):
        indent = context.get("indent") or 0
        context.set("indent", indent + 1)

    @classmethod
    def Dedent(self, element, context):
        indent = context.get("indent") or 0
        context.set("indent", indent - 1)

    @classmethod
    def CheckIndent(self, element, context, min=False):
        indent = context.get("indent") or 0
        o = context.offset or 0
        so = max(o - indent, 0)
        eo = o
        tabs = 0
        # This is a fix
        if so == eo and so > 0:
            so = eo
        for i in range(so, eo):
            if context[i] == b"\t":
                tabs += 1
        return tabs == indent

    def __init__(self, allows="\t ", step=1, values=None):
        self.allows = allows
        self.values = values
        self.step = step

    def withTabs(self):
        self.allows = "\t"
        self.values = {"\t": 1}
        self.step = 1


def __init__():
    pass


# EOF - vim: ts=4 sw=4 noet
