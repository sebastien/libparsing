// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 12-Dec-2014
// ----------------------------------------------------------------------------

#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include <errno.h>
#include <string.h>
#include <assert.h>
#include <sys/types.h>
#include <regex.h>
#include "oo.h"

#ifndef __PARSING__
#define __PARSING__
#define __PARSING_VERSION__ "0.0.1"

/**
 * == parsing.h
 * -- Parsing Elements Library
 * -- URL: http://github.com/sebastien/parsing
 *
 * `parsing.h` is a library to create grammars based on parsing elements.
 * As opposed to most "classic" parsing libraries, parsing elements don't do
 * tokenizaiton. Instead, an input stream is consumed and parsing elements
 * are run on the input stream. Once parsing elements match, the resulting
 * matched input is processed and an action is triggered.
 *
 * Parsing elements support backtracking, cherry-picking (skipping unrecognized
 * input), context-based rules (a rule that will match or not depending on the
 * current parsing state) and dynamic grammar update (you can change the grammar
 * on the fly).
 *
 * Parsing elements are usually slower than FSM-based parsers as they trade
 * performance for flexibility.
 *
*/


/**
 * Input data
 * ==========
 *
 * The parsing library is configured at compile-time to iterate on
 * specific elements of input, typically `char`. You can redefine
 * the macro `ITERATION_UNIT` to the type you'd like to iterate on.
*/

#ifndef ITERATION_UNIT
#define ITERATION_UNIT char
#endif

typedef ITERATION_UNIT iterated_t;

/**
 * Input data is aquired through _iterators_. Iterators wrap an input source
 * (the default input is a `FileInput`) and a `next` callback that updates the
 * iterator's state. The iterator will build a buffer of the acquired input
 * and maintain a pointer for the current offset within the data acquired from
 * the input stream.
 *
 * You can get an iterator on a file by doing:
 *
 * >	Iterator* iterator = Iterator_Open("example.txt");
*/

// @type Iterator
typedef struct Iterator {
	char           status;
	char*          buffer;
	iterated_t*    current;
	iterated_t     separator;
	size_t         offset;    // Offset (in bytes)
	size_t         lines;     // Counter for lines that have been encountered
	size_t         length;    // Length (in bytes)
	size_t         available; // Available data in buffer (in bytes)
	// FIXME: The head should be freed when the offsets have been parsed,
	// no need to keep in memory stuff we won't need.
	void*          input;
	bool          (*next) (struct Iterator*);
} Iterator;

// @type FileInput
// The file input wraps information about the input file, such
// as the `FILE` object and the `path`.
typedef struct {
	FILE*        file;
	const char*  path;
} FileInput;

// @shared
// The EOL character used to count lines in an iterator context.
iterated_t         EOL              = '\n';

// @classmethod
// Returns a new iterator instance with the given open file as input
Iterator* Iterator_Open(const char* path);

// @constructor
Iterator* Iterator_new(void);

// @destructor
void      Iterator_destroy(Iterator* this);

// @method
// Makes the given iterator open the file at the given path.
// This will automatically assign a `FileInput` to the iterator
// as an input source.
bool Iterator_open( Iterator* this, const char *path );

#ifndef ITERATOR_BUFFER_AHEAD
// @define
// The number of `iterated_t` that should be loaded after the iterator's
// current position. This limits the numbers of `iterated_t` that a `Token`
// could match.
#define ITERATOR_BUFFER_AHEAD 64000
#endif

// @constructor
FileInput* FileInput_new(const char* path );

// @destructor
void       FileInput_destroy(FileInput* this);

// @method
// Preloads data from the input source so that the buffer
// has ITERATOR_BUFFER_AHEAD characters ahead.
inline size_t FileInput_preload( Iterator* this );

// @method
// Iterates `n` time on the file input.
inline bool FileInput_move   ( Iterator* this, size_t n );

// @method
// Advances the given iterator, loading new data from the file input
// whenever there is not `ITERATOR_BUFFER_AHEAD` data elements
// ahead of the iterator's current position.
bool       FileInput_next(Iterator* this);

/**
 * Grammar
 * =======
 *
 * The `Grammar` is the concrete definition of the language you're going to
 * parse. It is defined by an `axiom` and input data that can be skipped,
 * such as white space.
 *
 * The `axiom` and `skip` properties are both references to _parsing elements_.
*/

typedef struct ParsingContext ParsingContext;
typedef struct ParsingElement ParsingElement;
typedef struct Reference      Reference;
typedef struct Match          Match;

// @type Grammar
typedef struct {
	ParsingElement*  axiom;       // The axiom
	ParsingElement*  skip;        // The skipped element
} Grammar;

Match* Grammar_parseFromIterator( Grammar* this, Iterator* iterator );

/**
 * Parsing Elements
 * ----------------
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
	char            status;     // The status of the match (see STATUS_XXX)
	size_t          length;     // The number of `iterated_t` matched
	void            *data;      // The matched data (usually a subset of the input stream)
	struct Match    *next;      // A pointer to the next match (see `References`)
} Match;


// @define
// The different values for a match (or iterator)'s status
#define STATUS_INIT        '-'
#define STATUS_PROCESSING  '~'
#define STATUS_MATCHED     'Y'
#define STATUS_FAILED      'X'
#define STATUS_INPUT_ENDED '.'
#define STATUS_ENDED       'E'

// @singleton FAILURE_S
// A specific match that indicates a failure
static Match FAILURE_S = {
	.status = STATUS_FAILED,
	.length = 0,
	.data   = NULL,
	.next   = NULL    // NOTE: next should *always* be NULL for FAILURE
};

// @shared FAILURE
static Match* FAILURE = &FAILURE_S;

// @operation
// Creates new empty (successful) match
Match* Match_Empty();

// @operation
// Creates a new successful match of the given length
Match* Match_Success(size_t length);

// @constructor
Match* Match_new();

// @destructor
void Match_destroy(Match* this);

// @type ParsingElement
typedef struct ParsingElement {
	char           type;       // Type is used du differentiate ParsingElement from Reference
	unsigned short id;         // The ID, assigned by the grammar, as the relative distance to the axiom
	const char*    name;       // The parsing element's name, for debugging
	void*          config;     // The configuration of the parsing element
	Reference*     children;   // The parsing element's children, if any
	Match*         (*recognize) (struct ParsingElement*, ParsingContext*);
	Match*         (*process)   (struct ParsingElement*, ParsingContext*, Match*);
} ParsingElement;


// @classmethod
// Tells if the given pointer is a pointer to a ParsingElement.
bool         ParsingElement_Is(void *);
const char   ParsingElement_T = 'P';

// @constructor
// Creates a new parsing element and adds the given referenced
// parsing elements as children. Note that this is an internal
// constructor, and you should use the specialized versions instead.
ParsingElement* ParsingElement_new(Reference* children[]);

// @destructor
void ParsingElement_destroy(ParsingElement* this);

// @method
// Adds a new reference as child of this parsing element. This will only
// be effective for composite parsing elements such as `Rule` or `Token`.
ParsingElement* ParsingElement_add(ParsingElement *this, Reference *child);

// @method
// Returns the match for this parsing element for the given iterator's state.
inline Match* ParsingElement_recognize( ParsingElement* this, ParsingContext* context );

// @method
// Processes the given match once the parsing element has fully succeeded. This
// is where user-bound actions will be applied, and where you're most likely
// to do things such as construct an AST.
inline Match* ParsingElement_process( ParsingElement* this, Match* match );

// FIXME: Maybe should inline
// @method
// Transparently sets the name of the element
inline ParsingElement* ParsingElement_name( ParsingElement* this, const char* name );

/**
 * Word
 * ------
 *
 * Words recognize a static string at the current iterator location.
 *
*/

// @type Word
// The parsing element configuration information that is used by the
// `Token` methods.
typedef struct {
	const char* word;
	size_t      length;
} Word;

// @constructor
ParsingElement* Word_new(const char* word);

// @method
// The specialized match function for token parsing elements.
Match*          Word_recognize(ParsingElement* this, ParsingContext* context);

/**
 * Tokens
 * ------
 *
 * Tokens are regular expression based parsing elements. They do not have
 * any children and test if the regular expression matches exactly at the
 * iterator's current location.
 *
*/

// @type Token
// The parsing element configuration information that is used by the
// `Token` methods.
typedef struct {
	regex_t regex;
} Token;

// @method
// Creates a new token with the given POSIX extended regular expression
ParsingElement* Token_new(const char* expr);

// @method
// The specialized match function for token parsing elements.
Match*          Token_recognize(ParsingElement* this, ParsingContext* context);

/**
 * References
 * ----------
 *
 * We've seen that parsing elements can have `children`. However, a parsing
 * element's children are not directly parsing elements but rather
 * parsing elements' `Reference`s. This is why the `ParsingElement_add` takes
 * a `Reference` object as parameter.
 *
 * References allow to share a single parsing element between many different
 * composite parsing elements, while decorating them with additional information
 * such as their cardinality (`SINGLE`, `OPTIONAL`, `MANY` and `MANY_OPTIONAL`)
 * and a `name` that will allow `process` actions to easily access specific
 * parts of the parsing element.
*/
// @type Reference
typedef struct Reference {
	char            type;            // Set to Reference_T, to disambiguate with ParsingElement
	char            cardinality;     // Either SINGLE (default), OPTIONAL, MANY or MANY_OPTIONAL
	const char*     name;            // The name of the reference (optional)
	ParsingElement* element;         // The reference to the parsing element
	Reference*      next;            // The next child reference in the parsing elements
} Reference;

// @define
// The different values for the `Reference` cardinality.
#define CARDINALITY_OPTIONAL      '?'
#define CARDINALITY_SINGLE        '1'
#define CARDINALITY_MANY_OPTIONAL '*'
#define CARDINALITY_MANY          '+'

//
// @classmethod
// Tells if the given pointer is a pointer to Reference
bool         Reference_Is(void *);
const char   Reference_T = 'R';

// @classmethod
Reference* Reference_New(ParsingElement *);

// @constructor
// References are typically owned by their single parent composite element.
Reference* Reference_new();

// @method
// Sets the cardinality of this reference, returning it transprently.
inline Reference* Reference_cardinality(Reference* this, char cardinality);

// @method
// Returns the matched value corresponding to the first match of this reference.
// `OPTIONAL` references might return `EMPTY`, `SINGLE` references will return
// a match with a `next=NULL` while `MANY` may return a match with a `next`
// pointing to the next match.
inline Match* Reference_recognize(Reference* this, ParsingContext* context);

/**
 * Groups
 * ------
 *
 * Groups are composite parsing elements that will return the first matching reference's
 * match. Think of it as a logical `or`.
*/

// @constructor
ParsingElement* Group_new(Reference* children[]);

// @method
Match*          Group_recognize(ParsingElement* this, ParsingContext* context);

/**
 * Rules
 * -----
 *
 * Groups are composite parsing elements that only succeed if all their
 * matching reference's.
*/

// @constructor
ParsingElement* Rule_new(Reference* children[]);

// @method
Match*          Rule_recognize(ParsingElement* this, ParsingContext* context);

/**
 * The parsing process
 * ===================
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

// @type ParsingContext
typedef struct ParsingContext {
	Grammar*              grammar;      // The grammar used to parse
	Iterator*             iterator;     // Iterator on the input data
	struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
	struct ParsingOffset* current;      // The current parsing offset
} ParsingContext;

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
void ParsingOffset_destroy( ParsingOffset* this );

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
void ParsingStep_destroy( ParsingStep* this );

/**
 * Syntax Sugar
 * ============
 *
 * The parsing library provides a set of macros that make defining grammars
 * a much easier task.
*/
#define ONE(v)            Reference_cardinality(Reference_New(v), CARDINALITY_SINGLE)
#define OPTIONAL(v)       Reference_cardinality(Reference_New(v), CARDINALITY_OPTIONAL)
#define MANY(v)           Reference_cardinality(Reference_New(v), CARDINALITY_MANY)
#define MANY_OPTIONAL(v)  Reference_cardinality(Reference_New(v), CARDINALITY_MANY_OPTIONAL)
#define NAME(n,e)         ParsingElement_name(e,n)

#endif
// EOF
