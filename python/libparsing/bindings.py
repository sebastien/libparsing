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

from __future__ import print_function
from   libparsing.native import C, CObject, CLibrary, ctypes, cproperty, caccessor, C_POINTER_TYPE

__doc__ = """
Low-level bindings to the libparsing C API.
"""

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

class TProcessor(ctypes.Structure):

	STRUCTURE = """
	ProcessorCallback   fallback;
	ProcessorCallback*  callbacks;
	int                 callbacksCount;
	"""

# -----------------------------------------------------------------------------
#
# C LIB PARSING
#
# -----------------------------------------------------------------------------

C.TYPES.update({
	"iterated_t"         : ctypes.c_char,
	"iterated_t*"        : ctypes.c_char_p,
	"Iterator*"          : ctypes.c_void_p,
	"Element*"           : ctypes.c_void_p,
	"Element**"          : ctypes.POINTER(ctypes.c_void_p),
	"Processor*"         : ctypes.c_void_p,
	"ParsingContext*"    : ctypes.c_void_p,
	"ParsingOffset*"     : ctypes.c_void_p,
	"IteratorCallback"   : ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.POINTER(TIterator), ctypes.c_int),
	"WalkingCallback"    : ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p),
	"ConditionCallback"  : ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.POINTER(TParsingElement), ctypes.POINTER(TParsingContext)),
	"ProcedureCallback"  : ctypes.CFUNCTYPE(None, ctypes.POINTER(TParsingElement), ctypes.POINTER(TParsingContext)),
	"ProcessorCallback"  : ctypes.CFUNCTYPE(None, ctypes.POINTER(TProcessor), ctypes.POINTER(TMatch)),
})
C.TYPES["ProcessorCallback*"] = ctypes.POINTER(C.TYPES["ProcessorCallback"])

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
	TProcessor,
	TGrammar,
)

# EOF - vim: ts=4 sw=4 noet
