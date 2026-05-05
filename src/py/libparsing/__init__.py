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

# Sentinel object used to distinguish "optional slot did not match" from
# "slot matched but the handler returned None" (e.g. JSON null).
# Handlers should test `if slot is not UNMATCHED:` instead of `if slot is not None:`
# when the grammar uses optional elements that can legitimately produce None.
UNMATCHED = type(
    "_Unmatched",
    (),
    {"__repr__": lambda self: "UNMATCHED", "__bool__": lambda self: False},
)()

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

# Runtime detection of PCRE support in the compiled C library.
HAS_PCRE = bool(lib.Parsing_hasPCRE()) if lib else False

# Runtime detection of GC (garbage collection) support in the compiled C library.
HAS_GC = bool(lib.Parsing_hasGC()) if lib else False

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
        if isinstance(index, str):
            i = self.indexForKey(index)
            if i >= 0:
                return self[i]
            raise KeyError("Cannot find item #{0} in {1}".format(index, self))
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

    @property
    def offset(self):
        return self._cobject.offset

    @property
    def line(self):
        return self._cobject.line

    @property
    def length(self):
        return self._cobject.length

    @property
    def type(self):
        return lib.Match_getType(self._cobject)

    @property
    def id(self):
        return lib.Match_getElementID(self._cobject)

    @property
    def status(self):
        return self._cobject.status

    @property
    def value(self):
        t = self.type
        if t == TYPE_REFERENCE:
            if self.hasChildren():
                return self[0].value
            return None
        elif t == TYPE_WORD:
            v = lib.WordMatch_group(self._cobject)
            return ensure_unicode(ffi.string(v)) if v != ffi.NULL else None
        elif t == TYPE_TOKEN:
            n = lib.TokenMatch_count(self._cobject)
            if n == 0:
                return None
            g0 = lib.TokenMatch_group(self._cobject, 0)
            return ensure_unicode(ffi.string(g0)) if g0 else None
        return None

    def slots(self):
        return [child for child in self if child.name]

    def indexForKey(self, name):
        for i, child in enumerate(self):
            if child.name == name:
                return i
        return -1

    def hasChildren(self):
        return lib.Match_hasChildren(self._cobject)

    def countChildren(self):
        count = 0
        child = self._cobject.children
        while child != ffi.NULL:
            count += 1
            child = child.next
        return count


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
    "RangeToken",
    "tp",
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
    "UNMATCHED",
    "HAS_PCRE",
    "HAS_GC",
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

    def setCustomRecognize(self, recognizer):
        """Set a custom C recognizer function on this token, bypassing PCRE.
        `recognizer` must be a C function pointer (TokenCustomRecognize)."""
        lib.Token_setCustomRecognize(self._cobject, recognizer)
        return self

    def setJSONStringRecognizer(self):
        """Use hand-coded JSON string recognizer instead of PCRE."""
        lib.Token_setCustomRecognize(self._cobject, lib.Token_recognizeJSONString)
        return self

    def setJSONNumberRecognizer(self):
        """Use hand-coded JSON number recognizer instead of PCRE."""
        lib.Token_setCustomRecognize(self._cobject, lib.Token_recognizeJSONNumber)
        return self


# -----------------------------------------------------------------------------
#
# TOKEN PATTERN (range-based, PCRE-free)
#
# -----------------------------------------------------------------------------


class tp:
    """Token pattern builder for range-based tokens (PCRE-free).

    Usage::

        # \\d+(\\.\\d+)?
        number = tp.seq(tp.many(tp.digit()), tp.optional(tp.seq(tp.char('.'), tp.many(tp.digit()))))
        g.range_token("NUMBER", number)

        # \\s+
        g.range_token("WS", tp.many(tp.space()))

        # [a-zA-Z_][a-zA-Z0-9_]*
        ident = tp.seq(
            tp.alt(tp.alpha(), tp.char('_')),
            tp.many_optional(tp.word())
        )
    """

    @staticmethod
    def char(c):
        """Match exact character."""
        return lib.tp_char(c.encode("utf-8") if isinstance(c, str) else c)

    @staticmethod
    def range(lo, hi):
        """Match byte range [lo..hi]."""
        if isinstance(lo, str):
            lo = lo.encode("utf-8")
        if isinstance(hi, str):
            hi = hi.encode("utf-8")
        return lib.tp_range(lo, hi)

    @staticmethod
    def set(chars):
        """Match any character in the given string."""
        return lib.tp_set(ensure_bytes(chars))

    @staticmethod
    def not_set(chars):
        """Match any character NOT in the given string."""
        return lib.tp_not_set(ensure_bytes(chars))

    @staticmethod
    def any():
        """Match any byte."""
        return lib.tp_any()

    @staticmethod
    def digit():
        """Shorthand for [0-9]."""
        return lib.tp_digit()

    @staticmethod
    def alpha():
        """Shorthand for [a-zA-Z]."""
        return lib.tp_alpha()

    @staticmethod
    def word():
        """Shorthand for [a-zA-Z0-9_]."""
        return lib.tp_word()

    @staticmethod
    def space():
        """Shorthand for [ \\t\\n\\r]."""
        return lib.tp_space()

    @staticmethod
    def seq(*children):
        """Sequence: match all children in order."""
        arr = ffi.new("TokenPattern*[]", list(children) + [ffi.NULL])
        return lib.tp_seq(arr)

    @staticmethod
    def alt(*children):
        """Alternation: match first child that succeeds."""
        arr = ffi.new("TokenPattern*[]", list(children) + [ffi.NULL])
        return lib.tp_alt(arr)

    @staticmethod
    def many(p):
        """One-or-more (+)."""
        return lib.tp_many(p)

    @staticmethod
    def optional(p):
        """Zero-or-one (?)."""
        return lib.tp_optional(p)

    @staticmethod
    def many_optional(p):
        """Zero-or-more (*)."""
        return lib.tp_many_optional(p)

    @staticmethod
    def literal(s):
        """Literal string match."""
        return lib.tp_literal(ensure_bytes(s))


class RangeToken(ParsingElement):
    """A range-based token that uses TokenPattern for matching (no PCRE)."""

    __slots__ = ("_pattern",)

    def _new(self, pattern):
        self._pattern = pattern  # prevent GC of the pattern pointer
        return lib.RangeToken_new(pattern)

    def setCustomRecognize(self, recognizer):
        """Set a custom C recognizer function on this token."""
        lib.RangeToken_setCustomRecognize(self._cobject, recognizer)
        return self

    def setJSONStringRecognizer(self):
        """Use hand-coded JSON string recognizer."""
        lib.RangeToken_setCustomRecognize(self._cobject, lib.Token_recognizeJSONString)
        return self

    def setJSONNumberRecognizer(self):
        """Use hand-coded JSON number recognizer."""
        lib.RangeToken_setCustomRecognize(self._cobject, lib.Token_recognizeJSONNumber)
        return self


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

    @classmethod
    def Wrap(cls, cobject):
        if cobject == ffi.NULL:
            return None
        obj = cls.__new__(cls)
        obj._cobject = ffi.cast(cls._TYPE, cobject)
        return obj

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

    def range_token(self, name, pattern):
        """Create a range-based token (PCRE-free) using a TokenPattern.

        Usage::

            g.range_token("WS", tp.many(tp.space()))
            g.range_token("NUMBER", tp.seq(
                tp.many(tp.digit()),
                tp.optional(tp.seq(tp.char('.'), tp.many(tp.digit())))
            ))
        """
        self._prepared = False
        r = RangeToken(pattern)
        r.name = name
        self.symbols[name] = r
        return r

    def arange_token(self, pattern):
        """Create an anonymous range-based token."""
        self._prepared = False
        return self._registerAnonymous(RangeToken(pattern))

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

    def setNoMemo(self, noMemo=True):
        """Disables packrat memoization. Use for grammars that don't benefit
        from memoization (e.g., LL(1)-like grammars without significant backtracking)."""
        e = ffi.cast("Grammar*", self._cobject)
        e.noMemo = 1 if noMemo else 0
        return self

    def setSkipWhitespace(self, value=True):
        """Uses hand-coded ASCII whitespace scanning instead of PCRE for skip.
        Much faster when the skip pattern is simply \\s+."""
        e = ffi.cast("Grammar*", self._cobject)
        e.skipWhitespace = 1 if value else 0
        return self

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
        # Build _elemCache: maps element_id -> (type, handler, fast_handler, is_many, is_passthrough)
        # This consolidates all per-element metadata into a single dict lookup,
        # eliminating multiple FFI field reads and dict lookups per node in _fastProcess.
        # Tuple indices: [0]=type, [1]=handler, [2]=fast_handler, [3]=is_many, [4]=is_passthrough
        self._elemCache = ec = {}
        if self.grammar:
            gc = self.grammar._cobject
            count = gc.axiomCount + gc.skipCount + 1
            elems = gc.elements
            handlerByID = self.handlerByID
            fastByID = self._fastByID
            passthroughIDs = self._passthroughIDs
            for i in range(count):
                elem = elems[i]
                if elem == ffi.NULL:
                    continue
                eid = elem.id
                t = elem.type
                h = handlerByID.get(eid)
                fast = fastByID.get(eid)
                is_many = bool(lib.Reference_IsMany(elem)) if t == b"#" else False
                is_pt = eid in passthroughIDs
                ec[eid] = (t, h, fast, is_many, is_pt)
        # Build _postOrderActionCodes: a C-level char array for
        # Match_flattenPostArraysEx that remaps type bytes to encode
        # handler/passthrough info. This eliminates dict lookups in the
        # processing loop. Also build _postHandlers: a Python list indexed
        # by element ID for O(1) handler lookup.
        #
        # Remapped type bytes:
        #   'w' = Word with handler, 'W' = Word no handler (default)
        #   't' = Token with handler, 'T' = Token no handler (default)
        #   'V' = Token constant: `return True/False/None` (no _FastMatch needed)
        #   'H' = Token group0 transform: `return f(match.group()[0])` (no _FastMatch needed)
        #   'P' = Group passthrough (skipped in C), 'g' = Group with handler, 'G' = Group no handler
        #   'S' = Rule with slots handler, 'r' = Rule handler no slots, 'R' = Rule no handler
        #   'Q' = Rule slot passthrough: single slot, body is `return self.process(slot)`
        #   'K' = Rule slot tuple: body is `return (self.process(s1), self.process(s2))`
        #   'N', 'L' = structural (not remapped)
        handlerInfo = self._handlerInfo
        passthroughIDs = self._passthroughIDs
        max_id = max(ec.keys()) if ec else 0
        self._postMaxID = max_id
        # action_codes: char array for C, indexed by element ID
        action_codes = [0] * (max_id + 1)
        # _postHandlers: list indexed by element ID -> (raw_handler, slots) or None
        post_handlers = [None] * (max_id + 1)
        for eid, (t, h, fast, is_many, is_pt) in ec.items():
            if eid > max_id:
                continue
            raw_info = handlerInfo.get(eid)
            if is_pt:
                # Passthrough group
                action_codes[eid] = ord("P")
            elif raw_info:
                raw_handler, slots = raw_info
                post_handlers[eid] = (raw_handler, slots)
                if t == b"W":
                    action_codes[eid] = ord("w")
                elif t == b"T":
                    token_code = self._detectTokenPattern(raw_handler)
                    action_codes[eid] = token_code
                    if token_code == ord("V"):
                        # Constant handler: post_handlers stores (value,) not (handler, slots)
                        post_handlers[eid] = self._tokenPatternData
                    elif token_code == ord("H"):
                        # Group0 transform: post_handlers stores (transform_fn,) not (handler, slots)
                        post_handlers[eid] = self._tokenPatternData
                elif t == b"G":
                    action_codes[eid] = ord("g")
                elif t == b"R":
                    if slots:
                        # Detect optimizable Rule handler patterns via source analysis
                        rule_code = self._detectRulePattern(raw_handler, slots)
                        action_codes[eid] = rule_code
                        if rule_code == ord("Q"):
                            # Passthrough: just store slot index directly
                            post_handlers[eid] = slots[0][1]  # int
                        elif rule_code == ord("K"):
                            # Tuple: store tuple of slot indices
                            post_handlers[eid] = tuple(si for _, si in slots)
                        elif rule_code == ord("D") or rule_code == ord("A"):
                            # Dict/List collector: store (first_idx, rest_idx)
                            post_handlers[eid] = self._rulePatternData
                    else:
                        action_codes[eid] = ord("r")
            # else: no handler, no passthrough -> action_codes stays 0 (use default type)
        self._postActionCodes = bytes(action_codes)
        self._postHandlers = post_handlers

        # Pre-cache Word values: build list indexed by element ID -> Python string.
        # This eliminates cffi.string() calls in the hot loop for Word nodes (~40% of nodes).
        word_cache = [None] * (max_id + 1)
        for eid, (t, h, fast, is_many, is_pt) in ec.items():
            if t == b"W" and eid <= max_id:
                sym = self.grammar.symbol(eid)
                if sym is not None and hasattr(sym, "_word"):
                    word_cache[eid] = ensure_unicode(sym._word)
        self._wordCache = word_cache

    def _detectTokenPattern(self, handler):
        """Detect optimizable Token handler patterns via source analysis.

        Returns the action code byte (int):
          'V' (86) = constant value: `return True/False/None/0/...`
          'H' (72) = group0 transform: `return f(match.group()[0])`
          't' (116) = general token handler (fallback)

        Sets self._tokenPatternData to pattern-specific data:
          'V': the constant value (as a tuple: (value,))
          'H': the transform function (as a tuple: (fn,))
        """
        import re as _re

        try:
            src = inspect.getsource(handler)
            lines = [
                l.strip()
                for l in src.split("\n")
                if l.strip()
                and not l.strip().startswith(("def ", "@", "#", '"""', "'''"))
            ]
            if len(lines) == 1:
                line = lines[0]
                # Pattern 1: constant return
                # `return True`, `return False`, `return None`
                if line == "return True":
                    self._tokenPatternData = (True,)
                    return ord("V")
                if line == "return False":
                    self._tokenPatternData = (False,)
                    return ord("V")
                if line == "return None":
                    self._tokenPatternData = (None,)
                    return ord("V")
                # Pattern 2: group0 transform
                # `return <func>(match.group()[0])`
                m = _re.match(r"return\s+(\w[\w.]*)\(match\.group\(\)\[0\]\)$", line)
                if m:
                    func_name = m.group(1)
                    # Resolve the function in the handler's globals
                    func = handler.__globals__.get(func_name)
                    if func is None:
                        # Try builtins
                        import builtins

                        func = getattr(builtins, func_name, None)
                    if func is not None and callable(func):
                        self._tokenPatternData = (func,)
                        return ord("H")
        except (OSError, TypeError):
            pass
        return ord("t")

    def _detectRulePattern(self, handler, slots):
        """Detect optimizable Rule handler patterns via source analysis.

        Returns the action code byte (int):
          'Q' (81) = single-slot passthrough: `return self.process(slot)`
          'K' (75) = tuple constructor: return tuple of self.process(slot_i)
          'D' (68) = dict collector: collect first+rest into dict
          'A' (65) = list collector: collect first+rest into list
          'S' (83) = general handler with slots (fallback)
        """
        try:
            src = inspect.getsource(handler)
            lines = [
                l.strip()
                for l in src.split("\n")
                if l.strip()
                and not l.strip().startswith(("def ", "@", "#", '"""', "'''"))
            ]
            if len(lines) == 1:
                line = lines[0]
                # Pattern 1: single-slot passthrough
                # `return self.process(param_name)` where param_name is a slot arg
                if len(slots) == 1:
                    param_name = slots[0][0]
                    if line == "return self.process({0})".format(param_name):
                        return ord("Q")
                # Pattern 2: single-line tuple constructor
                # `return (self.process(s1), self.process(s2))`
                if len(slots) >= 2:
                    parts = ", ".join("self.process({0})".format(s[0]) for s in slots)
                    if line == "return ({0})".format(
                        parts
                    ) or line == "return {0}".format(parts):
                        return ord("K")
            # Pattern 3: multi-line tuple constructor
            # Lines like: `v1 = self.process(param1)` ... `return (v1, v2)`
            # Detect: each slot param has exactly one assignment `var = self.process(param)`
            # and the last line is `return (var1, var2, ...)` or `return var1, var2, ...`
            if len(slots) >= 2 and len(lines) == len(slots) + 1:
                var_map = {}  # param_name -> assigned_var
                ok = True
                for line_idx in range(len(slots)):
                    line = lines[line_idx]
                    param_name = slots[line_idx][0]
                    expected_rhs = "self.process({0})".format(param_name)
                    if " = " in line:
                        var_name, rhs = line.split(" = ", 1)
                        var_name = var_name.strip()
                        rhs = rhs.strip()
                        if rhs == expected_rhs:
                            var_map[param_name] = var_name
                        else:
                            ok = False
                            break
                    else:
                        ok = False
                        break
                if ok and len(var_map) == len(slots):
                    # Check return line
                    ret_line = lines[-1]
                    vars_tuple = ", ".join(var_map[s[0]] for s in slots)
                    if ret_line == "return ({0})".format(
                        vars_tuple
                    ) or ret_line == "return {0}".format(vars_tuple):
                        return ord("K")
            # Pattern 4: collect first+rest into dict/list
            # Detect handlers with exactly 2 slots (first, rest) that collect
            # first + truthy rest into a list, optionally wrapped with dict().
            #
            # Supported handler shapes:
            #
            # Shape A (7 lines, UNMATCHED guard, inline append):
            #   [0] <list> = []
            #   [1] if <first> is not UNMATCHED:
            #   [2] <list>.append(self.process(<first>))
            #   [3] <r> = self.process(<rest>)
            #   [4] if <r>:
            #   [5] <list>.extend(<r>)
            #   [6] return <list> | return dict(<list>)
            #
            # Shape B (8 lines, is not None guard, separate var):
            #   [0] <list> = []
            #   [1] <f> = self.process(<first>)
            #   [2] if <f> is not None:
            #   [3] <list>.append(<f>)
            #   [4] <r> = self.process(<rest>)
            #   [5] if <r>:
            #   [6] <list>.extend(<r>)
            #   [7] return <list> | return dict(<list>)
            #
            # Shape C (9 lines, UNMATCHED guard, separate var + extra filter):
            #   [0] <list> = []
            #   [1] if <first> is not UNMATCHED:
            #   [2] <f> = self.process(<first>)
            #   [3] if <f> is not None:
            #   [4] <list>.append(<f>)
            #   [5] <r> = self.process(<rest>)
            #   [6] if <r>:
            #   [7] <list>.extend(<r>)
            #   [8] return <list> | return dict(<list>)
            if len(slots) == 2:
                first_name = slots[0][0]
                rest_name = slots[1][0]
                ret_line = lines[-1] if lines else ""
                is_dict = ret_line.startswith("return dict(")
                is_list = ret_line.startswith("return ") and "dict" not in ret_line

                detected = False

                # Shape A: 7 lines with UNMATCHED guard, inline append
                if len(lines) == 7 and (is_dict or is_list):
                    if (
                        lines[0].endswith("= []")
                        and "is not UNMATCHED" in lines[1]
                        and ".append(self.process({0}))".format(first_name) in lines[2]
                        and "self.process({0})".format(rest_name) in lines[3]
                        and ".extend(" in lines[5]
                    ):
                        detected = True

                # Shape B: 8 lines with is not None guard, separate var
                if not detected and len(lines) == 8 and (is_dict or is_list):
                    if (
                        lines[0].endswith("= []")
                        and "self.process({0})".format(first_name) in lines[1]
                        and "is not None" in lines[2]
                        and ".append(" in lines[3]
                        and "self.process({0})".format(rest_name) in lines[4]
                        and ".extend(" in lines[6]
                    ):
                        detected = True

                # Shape C: 9 lines with UNMATCHED guard + extra filter
                if not detected and len(lines) == 9 and (is_dict or is_list):
                    if (
                        lines[0].endswith("= []")
                        and "is not UNMATCHED" in lines[1]
                        and "self.process({0})".format(first_name) in lines[2]
                        and ".append(" in lines[4]
                        and "self.process({0})".format(rest_name) in lines[5]
                        and ".extend(" in lines[7]
                    ):
                        detected = True

                if detected:
                    if is_dict:
                        self._rulePatternData = (slots[0][1], slots[1][1])
                        return ord("D")
                    if is_list:
                        self._rulePatternData = (slots[0][1], slots[1][1])
                        return ord("A")
        except (OSError, TypeError):
            pass
        return ord("S")

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
                            else UNMATCHED
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
                            else UNMATCHED
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
                            else UNMATCHED
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else UNMATCHED
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
                            else UNMATCHED
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else UNMATCHED
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
                            else UNMATCHED
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else UNMATCHED
                        )
                        c = children[_idx2]
                        v2 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else UNMATCHED
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
                            else UNMATCHED
                        )
                        c = children[_idx1]
                        v1 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else UNMATCHED
                        )
                        c = children[_idx2]
                        v2 = (
                            self._fastProcess(c, result_ref)
                            if c is not None and c != ffi.NULL
                            else UNMATCHED
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
        # UNMATCHED sentinel: an optional slot that didn't match.
        # Return None to callers — only internal slot dispatch sees UNMATCHED.
        if match is UNMATCHED:
            return None
        self.depth += 1
        match = match.match if isinstance(match, ParsingResult) else match
        if isinstance(match, (Match, _FastMatch)):
            # Top-level: use post-order if at depth 1 (no re-entrancy)
            if self.depth == 1:
                result = self._processPostOrder(match._cobject, match._result)
            else:
                result = self._fastProcess(match._cobject, match._result)
        else:
            result = match
        self.depth -= 1
        if result is UNMATCHED:
            return None
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
    # POST-ORDER STACK-BASED PROCESSING
    # =========================================================================

    def _processPostOrder(self, cobj, result_ref):
        """Process a match tree using a post-order flat buffer from C.

        Uses Match_flattenPostArraysEx to produce separate arrays with type
        bytes remapped to encode handler/passthrough info. This eliminates
        all dict lookups in the processing loop — dispatch is purely on the
        type byte.

        Remapped type codes (from _postActionCodes):
          N = null, L = list, c/p = condition/procedure
          W = word no handler, w = word with handler
          T = token no handler, t = token with handler
          V = token constant handler (return True/False/None)
          H = token group0 transform (return f(match.group()[0]))
          P = group passthrough, G = group no handler, g = group with handler
          R = rule no handler, S = rule with slots, r = rule without slots
        """
        # Get total node count for buffer sizing
        nodeCount = lib.Match_countAll(cobj) + 1
        if nodeCount <= 1:
            return self._fastProcess(cobj, result_ref)

        # Allocate separate arrays for each field
        a_types = ffi.new("char[]", nodeCount)
        a_ids = ffi.new("int[]", nodeCount)
        a_nc = ffi.new("int[]", nodeCount)
        a_words = ffi.new("const char*[]", nodeCount)
        a_matches = ffi.new("Match*[]", nodeCount)

        # Allocate string buffer for zero-alloc token group0 extraction.
        # The total token text can't exceed the input size. We use the input
        # length plus some slack for null terminators.
        if result_ref is not None and result_ref != ffi.NULL:
            try:
                input_len = result_ref._cobject.context.inputLength
            except (AttributeError, TypeError):
                input_len = 0
        else:
            input_len = 0
        strbuf_size = input_len + nodeCount + 1 if input_len > 0 else nodeCount * 64
        a_strbuf = ffi.new("char[]", strbuf_size)
        a_strbuf_used = ffi.new("int[1]")

        actual = lib.Match_flattenPostArraysEx(
            cobj,
            a_types,
            a_ids,
            a_nc,
            a_words,
            a_matches,
            self._postActionCodes,
            self._postMaxID,
            a_strbuf,
            strbuf_size,
            a_strbuf_used,
            nodeCount,
        )
        if actual <= 0:
            return self._fastProcess(cobj, result_ref)

        # Batch-read ALL integer arrays into Python lists.
        # bytes() on ffi.buffer is near-instant; indexing returns int.
        # Python list indexing is ~15% faster than CFFI array indexing.
        types_bytes = bytes(ffi.buffer(a_types, actual))
        ncs = ffi.unpack(a_nc, actual)
        ids = ffi.unpack(a_ids, actual)

        # Bulk-decode all token strings at once.
        # The strbuf contains null-terminated token strings written sequentially
        # during the C flatten. We decode the entire buffer as UTF-8 in one call,
        # then split by null bytes. This is ~5x faster than per-token ffi.string+decode.
        strbuf_used = a_strbuf_used[0]
        if strbuf_used > 0:
            _all_token_strs = (
                bytes(ffi.buffer(a_strbuf, strbuf_used)).decode("utf8").split("\0")
            )
            # Last entry is empty (trailing null), remove it
            if _all_token_strs and _all_token_strs[-1] == "":
                _all_token_strs.pop()
        else:
            _all_token_strs = []
        _n_tok_strs = len(_all_token_strs)

        # Cache lookups as locals for tight loop
        import _cffi_backend

        _fs = _cffi_backend.string  # for rare paths needing raw FFI string extraction
        _NULL = ffi.NULL
        _TMgroup = lib.TokenMatch_group
        _hasPostProcess = self._hasPostProcess
        # Direct handler lookup by ID — O(1) list indexing, no dict
        post_handlers = self._postHandlers

        # Type constants (int, since bytes()[i] returns int)
        # No-handler types (most common paths first):
        _W = 87  # Word, no handler
        _T = 84  # Token, no handler
        _R = 82  # Rule, no handler
        _G = 71  # Group, no handler
        _N = 78  # Null
        _L = 76  # List
        # NOTE: _P (passthrough) is handled in C — skipped entirely, never reaches Python
        _c = 99  # Condition
        _p = 112  # Procedure
        # Handler types:
        _w = 119  # Word with handler
        _t = 116  # Token with handler
        _g = 103  # Group with handler
        _S = 83  # Rule with slots
        _r = 114  # Rule handler, no slots
        _Q = 81  # Rule passthrough (single slot)
        _K = 75  # Rule tuple constructor
        _V = 86  # Token constant value (return True/False/None)
        _H = 72  # Token group0 transform (return f(match.group()[0]))
        _D = 68  # Rule dict collector (first+rest -> dict)
        _A = 65  # Rule list collector (first+rest -> list)

        stack = []
        sa = stack.append
        _FM = _FastMatch
        _wc = self._wordCache
        tok_idx = 0

        for i in range(actual):
            t = types_bytes[i]

            # ---- Ordered by frequency: W(37.5%), H(25%), Q(15.6%), K(9.4%), L(6.3%), S(6.3%) ----

            if t == _W:
                # Word, no handler: use pre-cached Python string
                sa(_wc[ids[i]])
                continue

            if t == _H:
                # Group0 transform token handler: return f(group0_string)
                # post_handlers[id] = (transform_fn,)
                g0 = _all_token_strs[tok_idx] if tok_idx < _n_tok_strs else ""
                tok_idx += 1
                sa(post_handlers[ids[i]][0](g0))
                continue

            if t == _Q:
                # Rule passthrough: single slot, equivalent to returning the slot value
                # post_handlers[id] = slot_index (int)
                nc = ncs[i]
                slot_idx = post_handlers[ids[i]]
                if nc == 1:
                    # Most common case: single child. If slot_idx is 0,
                    # value is already on stack. Otherwise replace.
                    if slot_idx != 0:
                        stack[-1] = None
                elif nc > 1:
                    val = stack[-nc + slot_idx] if slot_idx < nc else None
                    del stack[-nc:]
                    sa(val)
                else:
                    sa(None)
                continue

            if t == _K:
                # Rule tuple constructor: return tuple of slot values
                # post_handlers[id] = tuple of slot indices
                nc = ncs[i]
                slot_indices = post_handlers[ids[i]]
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    n_slots = len(slot_indices)
                    if n_slots == 2:
                        s0, s1 = slot_indices
                        sa(
                            (
                                children[s0] if s0 < nc else None,
                                children[s1] if s1 < nc else None,
                            )
                        )
                    else:
                        sa(
                            tuple(
                                children[si] if si < nc else None for si in slot_indices
                            )
                        )
                else:
                    sa(tuple(None for _ in slot_indices))
                continue

            if t == _L:
                nc = ncs[i]
                if nc == 1:
                    # Single child: wrap in list in-place
                    stack[-1] = [stack[-1]]
                elif nc > 1:
                    items = stack[-nc:]
                    del stack[-nc:]
                    sa(items)
                else:
                    sa([])
                continue

            if t == _D:
                # Dict collector: collect first+rest into dict
                # post_handlers[id] = (first_idx, rest_idx)
                nc = ncs[i]
                first_idx, rest_idx = post_handlers[ids[i]]
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    first = children[first_idx] if first_idx < nc else UNMATCHED
                    rest = children[rest_idx] if rest_idx < nc else UNMATCHED
                else:
                    first = UNMATCHED
                    rest = UNMATCHED
                if first is not UNMATCHED:
                    if rest and rest is not UNMATCHED:
                        sa(dict([first] + rest))
                    else:
                        sa(dict([first]))
                elif rest and rest is not UNMATCHED:
                    sa(dict(rest))
                else:
                    sa({})
                continue

            if t == _A:
                # List collector: collect first+rest into list
                # post_handlers[id] = (first_idx, rest_idx)
                nc = ncs[i]
                first_idx, rest_idx = post_handlers[ids[i]]
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    first = children[first_idx] if first_idx < nc else UNMATCHED
                    rest = children[rest_idx] if rest_idx < nc else UNMATCHED
                else:
                    first = UNMATCHED
                    rest = UNMATCHED
                if first is not UNMATCHED:
                    if rest and rest is not UNMATCHED:
                        sa([first] + rest)
                    else:
                        sa([first])
                elif rest and rest is not UNMATCHED:
                    sa(list(rest))
                else:
                    sa([])
                continue

            if t == _S:
                # Rule with slots handler
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                raw_handler, slots = hi
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                else:
                    children = []
                wrapped = _FM(a_matches[i], result_ref)
                nc_len = len(children)
                args = [children[si] if si < nc_len else UNMATCHED for _, si in slots]
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped, *args)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            # ---- Rare types (< 1% frequency) ----

            if t == _N:
                sa(UNMATCHED)
                continue

            if t == _V:
                # Constant token handler: return pre-computed value
                tok_idx += 1  # skip the token string in strbuf
                sa(post_handlers[ids[i]][0])
                continue

            if t == _c or t == _p:
                sa(True)
                continue

            if t == _t:
                # Token with handler (general, not optimized by V/H)
                g0 = _all_token_strs[tok_idx] if tok_idx < _n_tok_strs else ""
                tok_idx += 1
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                wrapped = _FM(a_matches[i], result_ref)
                wrapped._cached_group = [g0]
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _g:
                # Group with handler (non-passthrough)
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                if nc > 0:
                    del stack[-nc:]
                wrapped = _FM(a_matches[i], result_ref)
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _r:
                # Rule handler, no slots
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                if nc > 0:
                    del stack[-nc:]
                wrapped = _FM(a_matches[i], result_ref)
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _w:
                # Word with handler
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                wrapped = _FM(a_matches[i], result_ref)
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _T:
                # Token, no handler — return groups as list
                n = ncs[i]
                if n > 0:
                    g0 = _all_token_strs[tok_idx] if tok_idx < _n_tok_strs else ""
                    tok_idx += 1
                    if n == 1:
                        sa([g0])
                    else:
                        m = a_matches[i]
                        sa(
                            [g0]
                            + [_fs(_TMgroup(m, j)).decode("utf8") for j in range(1, n)]
                        )
                else:
                    sa([])
                continue

            if t == _R:
                # Rule, no handler — collect children as list
                nc = ncs[i]
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    sa(children)
                else:
                    sa([])
                continue

            if t == _G:
                # Group, no handler — default wrap in list
                nc = ncs[i]
                if nc == 0:
                    sa([None])
                else:
                    stack[-1] = [stack[-1]]
                continue

            if t == _N:
                sa(UNMATCHED)
                continue

            if t == _L:
                nc = ncs[i]
                if nc > 0:
                    items = stack[-nc:]
                    del stack[-nc:]
                    sa(items)
                else:
                    sa([])
                continue

            if t == _c or t == _p:
                sa(True)
                continue

            # ---- Optimized Rule patterns (no handler call needed) ----

            if t == _Q:
                # Rule passthrough: single slot, equivalent to returning the slot value
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                slot_idx = hi[1][0][1]  # slots[0][1] = child index
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    sa(children[slot_idx] if slot_idx < nc else None)
                else:
                    sa(None)
                continue

            if t == _K:
                # Rule tuple constructor: return tuple of slot values
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                slots = hi[1]
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    sa(tuple(children[si] if si < nc else None for _, si in slots))
                else:
                    sa(tuple(None for _ in slots))
                continue

            # ---- Handler paths ----

            # ---- Optimized Token patterns (no _FastMatch creation needed) ----

            if t == _V:
                # Constant token handler: return pre-computed value
                # post_handlers[id] = (constant_value,)
                sa(post_handlers[ids[i]][0])
                continue

            if t == _H:
                # Group0 transform token handler: return f(group0_string)
                # post_handlers[id] = (transform_fn,)
                wv = a_words[i]
                g0 = _fs(wv).decode("utf8") if wv != _NULL else ""
                sa(post_handlers[ids[i]][0](g0))
                continue

            if t == _t:
                # Token with handler
                # Group 0 is pre-extracted by C into a_words[i].
                # Group count is stored in ncs[i] (repurposed from childCount).
                # Only extract group 0 eagerly; other groups extracted lazily
                # if the handler accesses them via match.group().
                wv = a_words[i]
                g0 = _fs(wv).decode("utf8") if wv != _NULL else ""
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                wrapped = _FM(a_matches[i], result_ref)
                wrapped._cached_group = [g0]
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _S:
                # Rule with slots handler
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                raw_handler, slots = hi
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                else:
                    children = []
                wrapped = _FM(a_matches[i], result_ref)
                nc_len = len(children)
                args = [children[si] if si < nc_len else UNMATCHED for _, si in slots]
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped, *args)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _g:
                # Group with handler (non-passthrough)
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                if nc > 0:
                    del stack[-nc:]
                wrapped = _FM(a_matches[i], result_ref)
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _r:
                # Rule handler, no slots
                nc = ncs[i]
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                if nc > 0:
                    del stack[-nc:]
                wrapped = _FM(a_matches[i], result_ref)
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _w:
                # Word with handler
                wv = a_words[i]
                val = _fs(wv).decode("utf8") if wv != _NULL else None
                hi = post_handlers[ids[i]]
                raw_handler = hi[0]
                wrapped = _FM(a_matches[i], result_ref)
                ph = self._handler
                self._handler = raw_handler
                val = raw_handler(wrapped)
                self._handler = ph
                if _hasPostProcess:
                    val = self.postProcess(wrapped, val)
                sa(val)
                continue

            if t == _T:
                # Token, no handler — return groups as list
                # Group 0 is pre-extracted by C into a_words[i].
                # Group count is in ncs[i].
                n = ncs[i]
                if n > 0:
                    wv = a_words[i]
                    g0 = _fs(wv).decode("utf8") if wv != _NULL else ""
                    if n == 1:
                        sa([g0])
                    else:
                        m = a_matches[i]
                        sa(
                            [g0]
                            + [_fs(_TMgroup(m, j)).decode("utf8") for j in range(1, n)]
                        )
                else:
                    sa([])
                continue

            if t == _R:
                # Rule, no handler — collect children as list
                nc = ncs[i]
                if nc > 0:
                    children = stack[-nc:]
                    del stack[-nc:]
                    sa(children)
                else:
                    sa([])
                continue

            if t == _G:
                # Group, no handler — default wrap in list
                nc = ncs[i]
                if nc == 0:
                    sa([None])
                else:
                    stack[-1] = [stack[-1]]
                continue

        return stack[0] if stack else None

    # =========================================================================
    # FAST PATH: Process raw C match pointers without creating Match wrappers
    # =========================================================================

    def _fastProcess(self, cobj, result_ref):
        """Process a raw C match pointer, dispatching by element type.

        Uses _elemCache to consolidate all per-element metadata into a single
        dict lookup, eliminating multiple FFI field reads per node."""
        # Single FFI read + single dict lookup replaces:
        # elem.type, elem.id, Reference_IsMany, handlerByID.get, _fastByID.get, _passthroughIDs check
        elem = cobj.element
        info = self._elemCache[elem.id]
        # info = (type, handler, fast_handler, is_many, is_passthrough)
        t = info[0]

        # Inline reference handling (most common type, ~48% of calls)
        # References never have handlers, so skip handler lookup entirely
        if t == b"#":
            if not info[3]:  # not is_many
                child = cobj.children
                if child != ffi.NULL:
                    return self._fastProcess(child, result_ref)
                return UNMATCHED
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
        if info[4]:  # is_passthrough (only Groups)
            child = cobj.children
            if child != ffi.NULL:
                saved_handler = self._handler
                self._handler = None
                r = self._fastProcess(child, result_ref)
                self._handler = saved_handler
                return r
            return UNMATCHED

        h = info[1]  # handler

        if h and self._handler != h:
            # Handler registered — inline handler dispatch
            ph = self._handler
            self._handler = h
            fast = info[2]  # fast_handler
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
