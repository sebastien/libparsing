// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 31-Nov-2016
// ----------------------------------------------------------------------------

 /* Enable certain library functions (strdup) on linux.  See feature_test_macros(7) */
#define _XOPEN_SOURCE 500


#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include <errno.h>
#include <time.h>
#include <string.h>
#include <assert.h>
#include <sys/types.h>
#ifdef WITH_PCRE
#include <pcre.h>
#endif
#ifdef WITH_PYTHON
#include <Python.h>
#endif
#include "oo.h"

#ifndef __PARSING_H__
#define __PARSING_H__
#define __PARSING_VERSION__ "0.8.0"

/**
 * #  libparsing
 * ## C & Python Parsing Elements Grammar Library
 *
 * ```
 * Version :  0.7.0
 * URL     :  http://github.com/sebastien/parsing
 * README  :  https://cdn.rawgit.com/sebastien/libparsing/master/README.html
 * ```
 *
 * [START:INTRO]
 *
 * `libparsing` is a parsing element grammar (PEG) library written in C with
 * Python bindings. It offers decent performance while allowing for a
 * lot of flexibility. It is mainly intended to be used to create programming
 * languages and software engineering tools.
 *
 * As opposed to more traditional parsing techniques, the grammar is not compiled
 * but constructed using an API that allows dynamic update of the grammar.
 *
 * The parser does not do any tokeninzation, the instead input stream is
 * consumed and parsing elements are dynamically asked to match the next
 * element of it. Once parsing elements match, the resulting matched input is
 * processed and an action is triggered.
 *
 * `libparsing` supports the following features:
 *
 * - _backtracking_, ie. going back in the input stream if a match is not found
 * - _cherry-picking_, ie. skipping unrecognized input
 * - _contextual rules_, ie. a rule that will match or not depending on external
 *   variables
 *
 * Parsing elements are usually slower than compiled or FSM-based parsers as
 * they trade performance for flexibility. It's probably not a great idea to
 * use `libparsing` if the parsing has to happen as fast as possible (ie. a protocol
 * implementation), but it is a great use for programming languages, as it
 * opens up the door to dynamic syntax plug-ins and multiple language
 * embedding.
 *
 * If you're interested in PEG, you can start reading Brian Ford's original
 * article. Projects such as PEG/LEG by Ian Piumarta <http://piumarta.com/software/peg/>
 * ,OMeta by Alessandro Warth <http://www.tinlizzie.org/ometa/>
 * or Haskell's Parsec library <https://www.haskell.org/haskellwiki/Parsec>
 * are of particular interest in the field.
 *
 * Here is a short example of what creating a simple grammar looks like
 * in Python:
 *
 * ```
 * g = Grammar()
 * s = g.symbols
 * g.token("WS",       "\s+")
 * g.token("NUMBER",   "\d+(\.\d+)?")
 * g.token("VARIABLE", "\w+")
 * g.token("OPERATOR", "[\/\+\-\*]")
 * g.group("Value",     s.NUMBER, s.VARIABLE)
 * g.rule("Suffix",     s.OPERATOR._as("operator"), s.Value._as("value"))
 * g.rule("Expression", s.Value, s.Suffix.zeroOrMore())
 * g.axiom(s.Expression)
 * g.skip(s.WS)
 * match = g.parseString("10 + 20 / 5")
 * ```
 *
 * and the equivalent code in C
 *
 * ```
 * Grammar* g = Grammar_new()
 * SYMBOL(WS,         TOKEN("\\s+"))
 * SYMBOL(NUMBER,     TOKEN("\\d+(\\.\\d+)?"))
 * SYMBOL(VARIABLE,   TOKEN("\\w+"))
 * SYMBOL(OPERATOR,   GROUP("[\\/\\+\\-\\*]"))
 * SYMBOL(Value,      GOUP(_S(NUMBER), _S(VARIABLE)))
 * SYMBOL(Suffix,     RULE(_AS(_S(OPERATOR), "operator"), _AS(_S(Value), "value")))
 * SYMBOL(Expression, RULE(_S(Value), _MO(Suffix))
 * g->axiom = s_Expression;
 * g->skip(s_WS);
 * Grammar_prepare(g);
 * Match* match = Grammar_parseString(g, "10 + 20 / 5")
 * ```
 *
 * [END:INTRO]
 *
 * Installing
 * ==========
 *
 * To install the Python parsing module:
 *
 * ```shell
 * easy_install libparsing    # From Setuptools
 * pip install  libparsing     # From PIP
 * ```
 *
 * Note that for the above to work, you'll need a C compiler and libpcre-dev.
 * On Ubuntu, do `sudo apt install build-essential libprcre-dev`.
 *
 * To compile the C parsing module:
 *
 * ```shell
 * git clone http://github.com/sebastien/libparsing
 * cd libparsing
 * make
 * make install               # You can set PREFIX
 * ```
 *
 * `libparsing` works with GCC4 and Clang and is written following the `c11`
 * standard.
 *
 * C API
 * =====
 *
 * Input data
 * ----------
 *
 * The parsing library is configured at compile-time to iterate on
 * specific elements of input, typically `char`. You can redefine
 * the macro `ITERATION_UNIT` to the type you'd like to iterate on.
 *
 * By default, the `ITERATION_UNIT` is a `char`, which works both
 * for ASCII and UTF8. On the topic of Unicode/UTF8, the parsing
 * library only uses functions that are UTF8-savvy.
*/

#ifndef ITERATION_UNIT
#define ITERATION_UNIT char
#endif

typedef ITERATION_UNIT iterated_t;

/**
 * Input data is acquired through _iterators_. Iterators wrap an input source
 * (the default input is a `FileInput`) and a `move` callback that updates the
 * iterator's offset. The iterator will build a buffer of the acquired input
 * and maintain a pointer for the current offset within the data acquired from
 * the input stream.
 *
 * You can get an iterator on a file by doing:
 *
 * ```c
 * Iterator* iterator = Iterator_Open("example.txt");
 * ```
 *
*/

// @type Iterator
typedef struct Iterator {
	char           status;    // The status of the iterator, one of STATUS_{INIT|PROCESSING|INPUT_ENDED|ENDED}
	char*          buffer;    // The buffer to the read data, note how it is a (void*) and not an `iterated_t`
	iterated_t*    current;   // The pointer current offset within the buffer
	iterated_t     separator; // The character for line separator, `\n` by default.
	size_t         offset;    // Offset in input (in bytes), might be different from `current - buffer` if some input was freed.
	size_t         lines;     // Counter for lines that have been encountered
	size_t         capacity;  // Content capacity (in bytes), might be bigger than the data acquired from the input
	size_t         available; // Available data in buffer (in bytes), always `<= capacity`
	bool           freeBuffer;
	// FIXME: The head should be freed when the offsets have been parsed, no need to keep in memory stuff we won't need.
	void*          input;     // Pointer to the input source
	bool          (*move) (struct Iterator*, int n); // Plug-in function to move to the previous/next positions
} Iterator;

// @type FileInput
// The file input wraps information about the input file, such
// as the `FILE` object and the `path`.
typedef struct FileInput {
	FILE*        file;
	const char*  path;
} FileInput;

// @shared
// The EOL character used to count lines in an iterator context.
extern iterated_t         EOL;

// @operation
// Returns a new iterator instance with the given open file as input
Iterator* Iterator_Open(const char* path);

// @operation
// Returns a new iterator instance with the text
Iterator* Iterator_FromString(const char* text);

// @constructor
Iterator* Iterator_new(void);

// @destructor
void      Iterator_free(Iterator* this);

// @method
// Makes the given iterator open the file at the given path.
// This will automatically assign a `FileInput` to the iterator
// as an input source.
bool Iterator_open( Iterator* this, const char *path );

// @method
// Tells if the iterator has more available data. This means that there is
// available data after the current offset.
bool Iterator_hasMore( Iterator* this );

// @method
// Returns the number of bytes available from the current iterator's position
// up to the last available data. For dynamic streams, where the length is
// unknown, this should be lesser or equalt to `ITERATOR_BUFFER_AHEAD`.
size_t Iterator_remaining( Iterator* this );

// @method
// Moves the iterator to the given offset
bool Iterator_moveTo ( Iterator* this, size_t offset );

// @method
bool String_move ( Iterator* this, int offset );

// @define
// The number of `iterated_t` that should be loaded after the iterator's
// current position. This limits the numbers of `iterated_t` that a `Token`
// could match.
#define ITERATOR_BUFFER_AHEAD 64000

// @constructor
FileInput* FileInput_new(const char* path );

// @destructor
void       FileInput_free(FileInput* this);

// @method
// Preloads data from the input source so that the buffer
// has up to ITERATOR_BUFFER_AHEAD characters ahead.
size_t FileInput_preload( Iterator* this );

// @method
// Advances/rewinds the given iterator, loading new data from the file input
// whenever there is not `ITERATOR_BUFFER_AHEAD` data elements
// ahead of the iterator's current position.
bool FileInput_move   ( Iterator* this, int n );

/**
 * Grammar
 * -------
 *
 * The `Grammar` is the concrete definition of the language you're going to
 * parse. It is defined by an `axiom` and input data that can be skipped,
 * such as white space.
 *
 * The `axiom` and `skip` properties are both references to _parsing elements_.
*/

typedef struct ParsingVariable ParsingVariable;
typedef struct ParsingContext  ParsingContext;
typedef struct ParsingElement  ParsingElement;
typedef struct ParsingResult   ParsingResult;
typedef struct Reference       Reference;
typedef struct Match           Match;
typedef void                   Element;

// typedef struct Element {
// 	char           type;       // Type is used du differentiate ParsingElement from Reference
// 	int            id;         // The ID, assigned by the grammar, as the relative distance to the axiom
// } Element;

// @type Grammar
typedef struct Grammar {
	ParsingElement*  axiom;       // The axiom
	ParsingElement*  skip;        // The skipped element
	int              axiomCount;  // The count of parsing elemetns in axiom
	int              skipCount;   // The count of parsing elements in skip
	Element**        elements;    // The set of all elements in the grammar
	bool             isVerbose;
} Grammar;

// @constructor
Grammar* Grammar_new(void);

// @destructor
void Grammar_free(Grammar* this);

// @method
void Grammar_prepare ( Grammar* this );

// @method
int Grammar_symbolsCount ( Grammar* this );

// @method
ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator );

// @method
ParsingResult* Grammar_parsePath( Grammar* this, const char* path );

// @method
ParsingResult* Grammar_parseString( Grammar* this, const char* text );

// @method
void Grammar_freeElements(Grammar* this);

/**
 * Elements
 * --------
*/

// @callback
typedef int (*WalkingCallback)(Element* this, int step, void* context);

// @method
int Element_walk( Element* this, WalkingCallback callback, void* context);

// @method
int Element__walk( Element* this, WalkingCallback callback, int step, void* context);

/**
 * ### Parsing Elements
 *
 * Parsing elements are the core elements that recognize and process input
 * data. There are 4 basic types: `Work`, `Token`, `Group` and `Rule`.
 *
 * Parsing elements offer two main operations: `recognize` and `process`.
 * The `recognize` method generates a `Match` object (that might be the `FAILURE`
 * singleton if the data was not recognized). The `process` method tranforms
 * corresponds to a user-defined action that transforms the `Match` object
 * and returns the generated value.
 *
 * Parsing element are assigned an `id` that corresponds to their breadth-first distance
 * to the axiom. Before parsing, the grammar will re-assign the parsing element's
 * id accordingly.
 *
*/

// @type Match
typedef struct Match {
	// TODO: We might need to put offset there
	char            status;     // The status of the match (see STATUS_XXX)
	size_t          offset;     // The offset of `iterated_t` matched
	size_t          length;     // The number of `iterated_t` matched
	Element*        element;
	ParsingContext* context;
	void*           data;      // The matched data (usually a subset of the input stream)
	struct Match*   next;      // A pointer to the next  match (see `References`)
	struct Match*   children;  // A pointer to the child match (see `References`)
	void*           result;    // A pointer to the result of the match
} Match;

// @define
// The different values for a match (or iterator)'s status
#define STATUS_INIT        '-'
// @define
#define STATUS_PROCESSING  '~'
// @define
#define STATUS_MATCHED     'M'
// @define
#define STATUS_SUCCESS     'S'
// @define
#define STATUS_PARTIAL     's'
// @define
#define STATUS_FAILED      'X'
// @define
#define STATUS_INPUT_ENDED '.'
// @define
#define STATUS_ENDED       'E'

// @define
#define TYPE_ELEMENT    'E'
// @define
#define TYPE_WORD       'W'
// @define
#define TYPE_TOKEN      'T'
// @define
#define TYPE_GROUP      'G'
// @define
#define TYPE_RULE       'R'
// @define
#define TYPE_CONDITION  'c'
// @define
#define TYPE_PROCEDURE  'p'
// @define
#define TYPE_REFERENCE  '#'

// @define
// A parsing element that is not bound to a grammar will have ID_UNBOUND
// by default.
#define ID_UNBOUND      -10

// @define
// A parsing element that being bound to a grammar (see `Grammar_prepare`)
// will have an id of `ID_BINDING` temporarily.
#define ID_BINDING       -1

// @singleton FAILURE_S
// A specific match that indicates a failure
extern Match FAILURE_S;

// @shared FAILURE
extern Match* FAILURE;

// @operation
// Creates new empty (successful) match
Match* Match_Empty(Element* element, ParsingContext* context);

// @operation
// Creates a new successful match of the given length
Match* Match_Success(size_t length, Element* element, ParsingContext* context);

// @constructor
Match* Match_new(void);

// @destructor
// Frees the given match. If the match is `FAILURE`, then it won't
// be feed. This means that most of the times you won't need to free
// a failed match, as it's likely to be the `FAILURE` singleton.
void Match_free(Match* this);

// @method
bool Match_isSuccess(Match* this);

// @method
int Match_getOffset(Match* this);

// @method
int Match_getLength(Match* this);

// @method
// Calls `callback` with `(Match, step, context)` as arguments, doing
// the same for all descendants (depth-first traversal), stopping the
// traversal when `callbacks` return 0 or less.
int Match__walk(Match* this, WalkingCallback callback, int step, void* context );

// @method
int Match_countAll(Match* this);

// @type ParsingElement
typedef struct ParsingElement {
	char           type;       // Type is used du differentiate ParsingElement from Reference
	int            id;         // The ID, assigned by the grammar, as the relative distance to the axiom
	const char*    name;       // The parsing element's name, for debugging
	void*          config;     // The configuration of the parsing element
	struct Reference*     children;   // The parsing element's children, if any
	struct Match*         (*recognize) (struct ParsingElement*, ParsingContext*);
	struct Match*         (*process)   (struct ParsingElement*, ParsingContext*, Match*);
	void                  (*freeMatch) (Match*);
} ParsingElement;

// @operation
// Tells if the given pointer is a pointer to a ParsingElement.
bool         ParsingElement_Is(void *);

// @constructor
// Creates a new parsing element and adds the given referenced
// parsing elements as children. Note that this is an internal
// constructor, and you should use the specialized versions instead.
ParsingElement* ParsingElement_new(Reference* children[]);

// @destructor
void ParsingElement_free(ParsingElement* this);

// @method
// Adds a new reference as child of this parsing element. This will only
// be effective for composite parsing elements such as `Rule` or `Token`.
ParsingElement* ParsingElement_add(ParsingElement *this, Reference *child);

// @method
ParsingElement* ParsingElement_clear(ParsingElement *this);

// @method
// Returns the match for this parsing element for the given iterator's state.
// inline Match* ParsingElement_recognize( ParsingElement* this, ParsingContext* context );

// @method
// Processes the given match once the parsing element has fully succeeded. This
// is where user-bound actions will be applied, and where you're most likely
// to do things such as construct an AST.
Match* ParsingElement_process( ParsingElement* this, Match* match );

// FIXME: Maybe should inline
// @method
// Transparently sets the name of the element
ParsingElement* ParsingElement_name( ParsingElement* this, const char* name );

/**
 * ### Word
 *
 * Words recognize a static string at the current iterator location.
 *
*/

// @type WordConfig
// The parsing element configuration information that is used by the
// `Token` methods.
typedef struct WordConfig {
	const char* word;
	size_t      length;
} WordConfig;

// @constructor
ParsingElement* Word_new(const char* word);

// @destructor
void Word_free(ParsingElement* this);

// @method
// The specialized match function for token parsing elements.
Match*          Word_recognize(ParsingElement* this, ParsingContext* context);

// @method
const char* Word_word(ParsingElement* this);

// @method
const char* WordMatch_group(Match* match);

/**
 * ### Tokens
 *
 * Tokens are regular expression based parsing elements. They do not have
 * any children and test if the regular expression matches exactly at the
 * iterator's current location.
 *
*/

// @type TokenConfig
// The parsing element configuration information that is used by the
// `Token` methods.
typedef struct TokenConfig {
	const char* expr;
#ifdef WITH_PCRE
	pcre*       regexp;
	pcre_extra* extra;
#endif
} TokenConfig;

// @type
typedef struct TokenMatch {
	int             count;
	const char**    groups;
} TokenMatch;


// @method
// Creates a new token with the given POSIX extended regular expression
ParsingElement* Token_new(const char* expr);

// @destructor
void Token_free(ParsingElement*);

// @method
// The specialized match function for token parsing elements.
Match*          Token_recognize(ParsingElement* this, ParsingContext* context);

// @method
const char* Token_expr(ParsingElement* this);

// @method
// Frees the `TokenMatch` created in `Token_recognize`
void TokenMatch_free(Match* match);

// @method
const char* TokenMatch_group(Match* match, int index);

// @method
int TokenMatch_count(Match* match);

/**
 * ### References
 *
 * We've seen that parsing elements can have `children`. However, a parsing
 * element's children are not directly parsing elements but rather
 * parsing elements' `Reference`s. This is why the `ParsingElement_add` takes
 * a `Reference` object as parameter.
 *
 * References allow to share a single parsing element between many different
 * composite parsing elements, while decorating them with additional information
 * such as their cardinality (`ONE`, `OPTIONAL`, `MANY` and `MANY_OPTIONAL`)
 * and a `name` that will allow `process` actions to easily access specific
 * parts of the parsing element.
*/
// @type Reference
typedef struct Reference {
	char            type;            // Set to Reference_T, to disambiguate with ParsingElement
	int             id;              // The ID, assigned by the grammar, as the relative distance to the axiom
	char            cardinality;     // Either ONE (default), OPTIONAL, MANY or MANY_OPTIONAL
	const char*     name;            // The name of the reference (optional)
	struct ParsingElement* element;  // The reference to the parsing element
	struct Reference*      next;     // The next child reference in the parsing elements
} Reference;

// @define
// The different values for the `Reference` cardinality.
#define CARDINALITY_OPTIONAL      '?'
// @define
#define CARDINALITY_ONE           '1'
// @define
#define CARDINALITY_MANY_OPTIONAL '*'
// @define
#define CARDINALITY_MANY          '+'

//
// @operation
// Tells if the given pointer is a pointer to Reference
bool Reference_Is(void * this);

// @operation
// Ensures that the given element (or reference) is a reference.
Reference* Reference_Ensure(void* elementOrReference);

// @operation
// Returns a new reference wrapping the given parsing element
Reference* Reference_FromElement(ParsingElement* element);

// @constructor
// References are typically owned by their single parent composite element.
Reference* Reference_new(void);

// @destructor
void Reference_free(Reference* this);

// @method
// Sets the cardinality of this reference, returning it transprently.
Reference* Reference_cardinality(Reference* this, char cardinality);

// @method
Reference* Reference_name(Reference* this, const char* name);

// @method
bool Reference_hasNext(Reference* this);

// @method
bool Reference_hasElement(Reference* this);

// @method
int Reference__walk( Reference* this, WalkingCallback callback, int step, void* nothing );

// @method
// Returns the matched value corresponding to the first match of this reference.
// `OPTIONAL` references might return `EMPTY`, `ONE` references will return
// a match with a `next=NULL` while `MANY` may return a match with a `next`
// pointing to the next match.
Match* Reference_recognize(Reference* this, ParsingContext* context);

/**
 * ### Groups
 *
 * Groups are composite parsing elements that will return the first matching reference's
 * match. Think of it as a logical `or`.
*/

// @constructor
ParsingElement* Group_new(Reference* children[]);

// @method
Match*          Group_recognize(ParsingElement* this, ParsingContext* context);

/**
 * ### Rules
 *
 * Groups are composite parsing elements that only succeed if all their
 * matching reference's.
*/

// @constructor
ParsingElement* Rule_new(Reference* children[]);

// @method
Match*          Rule_recognize(ParsingElement* this, ParsingContext* context);

/**
 * ### Procedures
 *
 * Procedures are parsing elements that do not consume any input, always
 * succeed and usually have a side effect, such as setting a variable
 * in the parsing context.
*/

// @callback
typedef void (*ProcedureCallback)(ParsingElement* this, ParsingContext* context);

// @callback
typedef void (*MatchCallback)(Match* m);

// @constructor
ParsingElement* Procedure_new(ProcedureCallback c);

// @method
Match*          Procedure_recognize(ParsingElement* this, ParsingContext* context);

/*
 * ### Conditions
 *
 * Conditions, like procedures, execute arbitrary code when executed, but
 * they might return a FAILURE.
*/

// @callback
typedef Match* (*ConditionCallback)(ParsingElement*, ParsingContext*);

// @constructor
ParsingElement* Condition_new(ConditionCallback c);

// @method
Match*          Condition_recognize(ParsingElement* this, ParsingContext* context);

/**
 * The parsing process
 * -------------------
 *
 * The parsing itself is the process of taking a `grammar` and applying it
 * to an input stream of data, represented by the `iterator`.
 *
 * The grammar's `axiom` will be matched against the `iterator`'s current
 * position, and if necessary, the grammar's `skip` parsing element
 * will be applied to advance the iterator.
*/

typedef struct ParsingStep    ParsingStep;
typedef struct ParsingOffset  ParsingOffset;

// @type
typedef struct ParsingStats {
	size_t   bytesRead;
	double   parseTime;
	size_t   symbolsCount;
	size_t*  successBySymbol;
	size_t*  failureBySymbol;
	size_t   failureOffset;   // A reference to the deepest failure
	size_t   matchOffset;
	size_t   matchLength;
	Element* failureElement;  // A reference to the failure element
} ParsingStats;

// @constructor
ParsingStats* ParsingStats_new(void);

// @destructor
void ParsingStats_free(ParsingStats* this);

// @method
void ParsingStats_setSymbolsCount(ParsingStats* this, size_t t);

// @method
Match* ParsingStats_registerMatch(ParsingStats* this, Element* e, Match* m);

/**
 * 1. Parsing variables
 * --------------------
 *
 * Parsing variables for a type of hierarchical list that can store
 * named values within a parsing element subtrees. It basically allows
 * for the storing of contextual values during parse time. The parsing
 * variables are not handled directly, but are instead accessed through
 * the `ParsingContext` object.
*/

// @type
typedef struct ParsingVariable {
	const char* key;
	void* value;
	struct ParsingVariable* previous;
	struct ParsingVariable* parent;
} ParsingVariable;

// @constructor
ParsingVariable* ParsingVariable_new(const char* key, void* value);

// @destructor
void ParsingVariable_free(ParsingVariable* this);

// @destructor
void ParsingVariable_freeAll(ParsingVariable* this);


// @method
bool ParsingVariable_is(ParsingVariable* this, const char* key);

// @method
ParsingVariable* ParsingVariable_set(ParsingVariable* this, const char* name, void* value);

// @method
void* ParsingVariable_get(ParsingVariable* this, const char* name);

// @method
ParsingVariable* ParsingVariable_find(ParsingVariable* this, const char* key, bool local);

// @method
int ParsingVariable_getDepth(ParsingVariable* this);

// @method
const char* ParsingVariable_getName(ParsingVariable* this);

// @method
int  ParsingVariable_count(ParsingVariable* this);

/**
 * 2. Parsing context
 * --------------------
 *
 *
*/

// @callback
typedef void (*ContextCallback)(ParsingContext* context, char op );

// @type
typedef struct ParsingContext {
	struct Grammar*         grammar;      // The grammar used to parse
	struct Iterator*        iterator;     // Iterator on the input data
	struct ParsingOffset*   offsets;      // The parsing offsets, starting at 0
	struct ParsingOffset*   current;      // The current parsing offset
	struct ParsingStats*    stats;
	struct ParsingVariable* variables;
	struct Match*           lastMatch;
	ContextCallback         callback;
} ParsingContext;


// @constructor
ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator );

// @method
iterated_t* ParsingContext_text( ParsingContext* this );

// @method
size_t ParsingContext_getOffset( ParsingContext* this );

// @destructor
void ParsingContext_free( ParsingContext* this );

// @method
// Pushes a new context for the variabless
void ParsingContext_push ( ParsingContext* this );

// @method
// Pops the current context for the variables, rewinding to the parent
// one, if any.
void ParsingContext_pop ( ParsingContext* this );

// @method
// Retrieves the value bound to the given `name` in the variables.
void*  ParsingContext_get(ParsingContext*  this, const char* name);

// @method
void  ParsingContext_set(ParsingContext*  this, const char* name, void* value);


// @method
void ParsingContext_on(ParsingContext* this, ContextCallback callback);

// @method
int  ParsingContext_getVariableCount(ParsingContext* this);

// @method
Match* ParsingContext_registerMatch(ParsingContext* this, Element* e, Match* m);

// @type
typedef struct ParsingResult {
	char            status;
	Match*          match;
	ParsingContext* context;
} ParsingResult;

// @constructor
ParsingResult* ParsingResult_new(Match* match, ParsingContext* context);

// @method
// Frees this parsing result instance as well as all the matches it referes to.
void ParsingResult_free(ParsingResult* this);

// @method
bool ParsingResult_isFailure(ParsingResult* this);

// @method
bool ParsingResult_isPartial(ParsingResult* this);

// @method
bool ParsingResult_isComplete(ParsingResult* this);

// @method
iterated_t* ParsingResult_text(ParsingResult* this);

// @method
int ParsingResult_textOffset(ParsingResult* this);

// @method
size_t ParsingResult_remaining(ParsingResult* this);

/*
 * The result of _recognizing_ parsing elements at given offsets within the
 * input stream is stored in `ParsingOffset`. Each parsing offset is a stack
 * of `ParsingStep`, corresponding to successive attempts at matching
 * parsing elements at the current position.
 *
 * FIXME: Not sure about the following two paragraphs
 *
 * The parsing offset is a stack of parsing steps, where the tail is the most
 * specific parsing step. By following the tail's previous parsing step,
 * you can unwind the stack.
 *
 * The parsing steps each have an offset within the iterated stream. Offsets
 * where data has been fully extracted (ie, a leaf parsing element has matched
 * and processing returned a NOTHING) can be freed as they are not necessary
 * any more.
*/

// @type ParsingOffset
typedef struct ParsingOffset {
	size_t                offset; // The offset matched in the input stream
	ParsingStep*          last;   // The last matched parsing step (ie. corresponding to the most specialized parsing element)
	struct ParsingOffset* next;   // The link to the next offset (if any)
} ParsingOffset;

// @constructor
ParsingOffset* ParsingOffset_new( size_t offset );

// @destructor
void ParsingOffset_free( ParsingOffset* this );

/**
 * The parsing step allows to memoize the state of a parsing element at a given
 * offset. This is the data structure that will be manipulated and created/destroyed
 * the most during the parsing process.
*/
typedef struct ParsingStep {
	ParsingElement*     element;       // The parsing elemnt we're matching
	char                step;          // The step corresponds to current child's index (0 for token/word)
	unsigned int        iteration;     // The current iteration (on the step)
	char                status;        // Match status `STATUS_{INIT|PROCESSING|FAILED}`
	Match*              match;         // The corresponding match, if any.
	struct ParsingStep* previous;      // The previous parsing step on the parsing offset's stack
} ParsingStep;

// @constructor
ParsingStep* ParsingStep_new( ParsingElement* element );

// @destructor
void ParsingStep_free( ParsingStep* this );

/**
 * Processor
 * ---------
*/

typedef struct Processor Processor;

// @callback
typedef void (*ProcessorCallback)(Processor* processor, Match* match);

typedef struct Processor {
	ProcessorCallback   fallback;
	ProcessorCallback*  callbacks;
	int                 callbacksCount;
} Processor;


// @constructor
Processor* Processor_new( );

// @method
void Processor_free(Processor* this);

// @method
void Processor_register (Processor* this, int symbolID, ProcessorCallback callback) ;

// @method
int Processor_process (Processor* this, Match* match, int step);

/**
 * Utilities
 * ---------
*/

// @method
void Utilities_indent( ParsingElement* this, ParsingContext* context );

// @method
void Utilities_dedent( ParsingElement* this, ParsingContext* context );

// @method
Match* Utilites_checkIndent( ParsingElement *this, ParsingContext* context );

/**
 * Syntax Sugar
 * ------------
 *
 * The parsing library provides a set of macros that make defining grammars
 * a much easier task. A grammar is usually defined in the following way:
 *
 * - leaf symbols (words & tokens) are defined ;
 * - compound symbolds (rules & groups) are defined.
 *
 * Let's take as simple grammar and define it with the straight API:
 *
 * ```
 * // Leaf symbols
 * ParsingElement* s_NUMBER   = Token_new("\\d+");
 * ParsingElement* s_VARIABLE = Token_new("\\w+");
 * ParsingElement* s_OPERATOR = Token_new("[\\+\\-\\*\\/]");
 *
 * // We also attach names to the symbols so that debugging will be easier
 * ParsingElement_name(s_NUMBER,   "NUMBER");
 * ParsingElement_name(s_VARIABLE, "VARIABLE");
 * ParsingElement_name(s_OPERATOR, "OPERATOR");
 *
 * // Now we defined the compound symbols
 * ParsingElement* s_Value    = Group_new((Reference*[3]),{
 *     Reference_cardinality(Reference_Ensure(s_NUMBER),   CARDINALITY_ONE),
 *     Reference_cardinality(Reference_Ensure(s_VARIABLE), CARDINALITY_ONE)
 *     NULL
 * });
 * ParsingElement* s_Suffix    = Rule_new((Reference*[3]),{
 *     Reference_cardinality(Reference_Ensure(s_OPERATOR),  CARDINALITY_ONE),
 *     Reference_cardinality(Reference_Ensure(s_Value),     CARDINALITY_ONE)
 *     NULL
 * });
 * * ParsingElement* s_Expr    = Rule_new((Reference*[3]),{
 *     Reference_cardinality(Reference_Ensure(s_Value),  CARDINALITY_ONE),
 *     Reference_cardinality(Reference_Ensure(s_Suffix), CARDINALITY_MANY_OPTIONAL)
 *     NULL
 * });
 *
 * // We define the names as well
 * ParsingElement_name(s_Value,  "Value");
 * ParsingElement_name(s_Suffix, "Suffix");
 * ParsingElement_name(s_Expr, "Expr");
 * ```
 *
 * As you can see, this is quite verbose and makes reading the grammar declaration
 * a difficult task. Let's introduce a set of macros that will make expressing
 * grammars much easier.
 *
 * Symbol declaration & creation
 * -----------------------------
*/

// @macro
// Declares a symbol of name `n` as being parsing element `e`.
#define SYMBOL(n,e)       ParsingElement* s_ ## n = ParsingElement_name(e, #n);

// @macro
// Creates a `Word` parsing element with the given regular expression
#define WORD(v)           Word_new(v)

// @macro
// Creates a `Token` parsing element with the given regular expression
#define TOKEN(v)          Token_new(v)

// @macro
// Creates a `Rule` parsing element with the references or parsing elements
// as children.
#define RULE(...)         Rule_new((Reference*[(VA_ARGS_COUNT(__VA_ARGS__)+1)]){__VA_ARGS__,NULL})

// @macro
// Creates a `Group` parsing element with the references or parsing elements
// as children.
#define GROUP(...)        Group_new((Reference*[(VA_ARGS_COUNT(__VA_ARGS__)+1)]){__VA_ARGS__,NULL})

// @macro
// Creates a `Procedure` parsing element
#define PROCEDURE(f)      Procedure_new(f)

// @macro
// Creates a `Condition` parsing element
#define CONDITION(f)      Condition_new(f)

/*
 * Symbol reference & cardinality
 * ------------------------------
*/

// @macro
// Refers to symbol `n`, wrapping it in a `CARDINALITY_ONE` reference
#define _S(n)             ONE(s_ ## n)

// @macro
// Refers to symbol `n`, wrapping it in a `CARDINALITY_OPTIONAL` reference
#define _O(n)             OPTIONAL(s_ ## n)

// @macro
// Refers to symbol `n`, wrapping it in a `CARDINALITY_MANY` reference
#define _M(n)             MANY(s_ ## n)

// @macro
// Refers to symbol `n`, wrapping it in a `CARDINALITY_MANY_OPTIONAL` reference
#define _MO(n)            MANY_OPTIONAL(s_ ## n)

// @macro
// Sets the name of reference `r` to be v
#define _AS(r,v)          Reference_name(Reference_Ensure(r), v)

/*
 * Supporting macros
 * -----------------
 *
 * The following set of macros is mostly used by the set of macros above.
 * You probably won't need to use them directly.
*/


// @macro
// Sets the name of the given parsing element `e` to be the name `n`.
#define NAME(n,e)         ParsingElement_name(e,n)

// @macro
// Sets the given reference or parsing element's reference to CARDINALITY_ONE
// If a parsing element is given, it will be automatically wrapped in a reference.
#define ONE(v)            Reference_cardinality(Reference_Ensure(v), CARDINALITY_ONE)

// @macro
// Sets the given reference or parsing element's reference to CARDINALITY_OPTIONAL
// If a parsing element is given, it will be automatically wrapped in a reference.
#define OPTIONAL(v)       Reference_cardinality(Reference_Ensure(v), CARDINALITY_OPTIONAL)

// @macro
// Sets the given reference or parsing element's reference to CARDINALITY_MANY
// If a parsing element is given, it will be automatically wrapped in a reference.
#define MANY(v)           Reference_cardinality(Reference_Ensure(v), CARDINALITY_MANY)

// @macro
// Sets the given reference or parsing element's reference to CARDINALITY_MANY_OPTIONAL
// If a parsing element is given, it will be automatically wrapped in a reference.
#define MANY_OPTIONAL(v)  Reference_cardinality(Reference_Ensure(v), CARDINALITY_MANY_OPTIONAL)

/*
 * Grammar declaration with macros
 * -------------------------------
 *
 * The same grammar that we defined previously can now be expressed in the
 * following way:
 *
 * ```
 * SYMBOL(NUMBER,   TOKEN("\\d+"))
 * SYMBOL(VAR,      TOKEN("\\w+"))
 * SYMBOL(OPERATOR, TOKEN("[\\+\\-\\*\\/]"))
 *
 * SYMBOL(Value,  GROUP( _S(NUMBER),   _S(VAR)     ))
 * SYMBOL(Suffix, RULE(  _S(OPERATOR), _S(Value)   ))
 * SYMBOL(Expr,   RULE(  _S(Value),    _MO(Suffix) ))
 * ```
 *
 * All symbols will be define as `s_XXX`, so that you can do:
 *
 * ```
 * ParsingGrammar* g = Grammar_new();
 * g->axiom = s_Expr;
 * ```
 *
 * License
 * =======
 *
 * Revised BSD License Copyright (c) 2014, FFunction inc (1165373771 Quebec
 * inc) All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * Redistributions of source code must retain the above copyright notice, this
 * list of conditions and the following disclaimer. Redistributions in binary
 * form must reproduce the above copyright notice, this list of conditions and
 * the following disclaimer in the documentation and/or other materials
 * provided with the distribution. Neither the name of the FFunction inc
 * (CANADA) nor the names of its contributors may be used to endorse or promote
 * products derived from this software without specific prior written
 * permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 * [END]
*/

#endif
// EOF
