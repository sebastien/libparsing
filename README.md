
#  libparsing
## C & Python Parsing Elements Grammar Library

```
Version :  0.7.0
URL     :  http://github.com/sebastien/parsing
README  :  https://cdn.rawgit.com/sebastien/libparsing/master/README.html
```


`libparsing` is a parsing element grammar (PEG) library written in C with
Python bindings. It offers decent performance while allowing for a
lot of flexibility. It is mainly intended to be used to create programming
languages and software engineering tools.

As opposed to more traditional parsing techniques, the grammar is not compiled
but constructed using an API that allows dynamic update of the grammar.

The parser does not do any tokeninzation, the instead input stream is
consumed and parsing elements are dynamically asked to match the next
element of it. Once parsing elements match, the resulting matched input is
processed and an action is triggered.

`libparsing` supports the following features:

- _backtracking_, ie. going back in the input stream if a match is not found
- _cherry-picking_, ie. skipping unrecognized input
- _contextual rules_, ie. a rule that will match or not depending on external
variables

Parsing elements are usually slower than compiled or FSM-based parsers as
they trade performance for flexibility. It's probably not a great idea to
use `libparsing` if the parsing has to happen as fast as possible (ie. a protocol
implementation), but it is a great use for programming languages, as it
opens up the door to dynamic syntax plug-ins and multiple language
embedding.

If you're interested in PEG, you can start reading Brian Ford's original
article. Projects such as PEG/LEG by Ian Piumarta <http://piumarta.com/software/peg/>
,OMeta by Alessandro Warth <http://www.tinlizzie.org/ometa/>
or Haskell's Parsec library <https://www.haskell.org/haskellwiki/Parsec>
are of particular interest in the field.

Here is a short example of what creating a simple grammar looks like
in Python:

```
g = Grammar()
s = g.symbols
g.token("WS",       "\s+")
g.token("NUMBER",   "\d+(\.\d+)?")
g.token("VARIABLE", "\w+")
g.token("OPERATOR", "[\/\+\-\*]")
g.group("Value",     s.NUMBER, s.VARIABLE)
g.rule("Suffix",     s.OPERATOR._as("operator"), s.Value._as("value"))
g.rule("Expression", s.Value, s.Suffix.zeroOrMore())
g.axiom(s.Expression)
g.skip(s.WS)
match = g.parseString("10 + 20 / 5")
```

and the equivalent code in C

```
Grammar* g = Grammar_new()
SYMBOL(WS,         TOKEN("\\s+"))
SYMBOL(NUMBER,     TOKEN("\\d+(\\.\\d+)?"))
SYMBOL(VARIABLE,   TOKEN("\\w+"))
SYMBOL(OPERATOR,   GROUP("[\\/\\+\\-\\*]"))
SYMBOL(Value,      GOUP(_S(NUMBER), _S(VARIABLE)))
SYMBOL(Suffix,     RULE(_AS(_S(OPERATOR), "operator"), _AS(_S(Value), "value")))
SYMBOL(Expression, RULE(_S(Value), _MO(Suffix))
g->axiom = s_Expression;
g->skip(s_WS);
Grammar_prepare(g);
Match* match = Grammar_parseString(g, "10 + 20 / 5")
```


Installing
==========

To install the Python parsing module:

```shell
easy_install libparsing    # From Setuptools
pip install  libparsing     # From PIP
```

Note that for the above to work, you'll need a C compiler and libpcre-dev.
On Ubuntu, do `sudo apt install build-essential libprcre-dev`.

To compile the C parsing module:

```shell
git clone http://github.com/sebastien/libparsing
cd libparsing
make
make install               # You can set PREFIX
```

`libparsing` works with GCC4 and Clang and is written following the `c11`
standard.

C API
=====

Input data
----------

The parsing library is configured at compile-time to iterate on
specific elements of input, typically `char`. You can redefine
the macro `ITERATION_UNIT` to the type you'd like to iterate on.

By default, the `ITERATION_UNIT` is a `char`, which works both
for ASCII and UTF8. On the topic of Unicode/UTF8, the parsing
library only uses functions that are UTF8-savvy.

```c
#ifndef ITERATION_UNIT
#define ITERATION_UNIT char
#endif

typedef ITERATION_UNIT iterated_t;
```


Input data is acquired through _iterators_. Iterators wrap an input source
(the default input is a `FileInput`) and a `move` callback that updates the
iterator's offset. The iterator will build a buffer of the acquired input
and maintain a pointer for the current offset within the data acquired from
the input stream.

You can get an iterator on a file by doing:

```c
Iterator* iterator = Iterator_Open("example.txt");
```


#### <a name="Iterator_type"><span class="classifier">type</span> `Iterator`</a>


```c
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
	void*          input;     // Pointer to the input source
	bool          (*move) (struct Iterator*, int n); // Plug-in function to move to the previous/next positions
} Iterator;
```


#### <a name="FileInput_type"><span class="classifier">type</span> `FileInput`</a>

 The file input wraps information about the input file, such
	 as the `FILE` object and the `path`.

```c
typedef struct FileInput {
	FILE*        file;
	const char*  path;
} FileInput;
```


#### <a name="EOL_shared"><span class="classifier">shared</span> `EOL`</a>

 The EOL character used to count lines in an iterator context.

```c
extern iterated_t         EOL;
```


#### <a name="Iterator_Open_operation"><span class="classifier">operation</span> `Iterator_Open`</a>

 Returns a new iterator instance with the given open file as input

```c
Iterator* Iterator_Open(const char* path);
```


#### <a name="Iterator_FromString_operation"><span class="classifier">operation</span> `Iterator_FromString`</a>

 Returns a new iterator instance with the text

```c
Iterator* Iterator_FromString(const char* text);
```


#### <a name="Iterator_constructor"><span class="classifier">constructor</span> `Iterator`</a>


```c
Iterator* Iterator_new(void);
```


#### <a name="Iterator_free_destructor"><span class="classifier">destructor</span> `Iterator_free`</a>


```c
void      Iterator_free(Iterator* this);
```


#### <a name="Iterator_open_method"><span class="classifier">method</span> `Iterator_open`</a>

 Makes the given iterator open the file at the given path.
	 This will automatically assign a `FileInput` to the iterator
	 as an input source.

```c
bool Iterator_open( Iterator* this, const char *path );
```


#### <a name="Iterator_hasMore_method"><span class="classifier">method</span> `Iterator_hasMore`</a>

 Tells if the iterator has more available data. This means that there is
	 available data after the current offset.

```c
bool Iterator_hasMore( Iterator* this );
```


#### <a name="Iterator_remaining_method"><span class="classifier">method</span> `Iterator_remaining`</a>

 Returns the number of bytes available from the current iterator's position
	 up to the last available data. For dynamic streams, where the length is
	 unknown, this should be lesser or equalt to `ITERATOR_BUFFER_AHEAD`.

```c
size_t Iterator_remaining( Iterator* this );
```


#### <a name="Iterator_moveTo_method"><span class="classifier">method</span> `Iterator_moveTo`</a>

 Moves the iterator to the given offset

```c
bool Iterator_moveTo ( Iterator* this, size_t offset );
```


#### <a name="String_move_method"><span class="classifier">method</span> `String_move`</a>


```c
bool String_move ( Iterator* this, int offset );
```


#### <a name="ITERATOR_BUFFER_AHEAD_define"><span class="classifier">define</span> `ITERATOR_BUFFER_AHEAD`</a>

 The number of `iterated_t` that should be loaded after the iterator's
	 current position. This limits the numbers of `iterated_t` that a `Token`
	 could match.

```c
#define ITERATOR_BUFFER_AHEAD 64000
```


#### <a name="FileInput_constructor"><span class="classifier">constructor</span> `FileInput`</a>


```c
FileInput* FileInput_new(const char* path );
```


#### <a name="FileInput_free_destructor"><span class="classifier">destructor</span> `FileInput_free`</a>


```c
void       FileInput_free(FileInput* this);
```


#### <a name="FileInput_preload_method"><span class="classifier">method</span> `FileInput_preload`</a>

 Preloads data from the input source so that the buffer
	 has up to ITERATOR_BUFFER_AHEAD characters ahead.

```c
size_t FileInput_preload( Iterator* this );
```


#### <a name="FileInput_move_method"><span class="classifier">method</span> `FileInput_move`</a>

 Advances/rewinds the given iterator, loading new data from the file input
	 whenever there is not `ITERATOR_BUFFER_AHEAD` data elements
	 ahead of the iterator's current position.

```c
bool FileInput_move   ( Iterator* this, int n );
```


Grammar
-------

The `Grammar` is the concrete definition of the language you're going to
parse. It is defined by an `axiom` and input data that can be skipped,
such as white space.

The `axiom` and `skip` properties are both references to _parsing elements_.

```c
typedef struct ParsingContext ParsingContext;
typedef struct ParsingElement ParsingElement;
typedef struct ParsingResult  ParsingResult;
typedef struct Reference      Reference;
typedef struct Match          Match;
typedef void                  Element;
```

 typedef struct Element {
 	char           type;       // Type is used du differentiate ParsingElement from Reference
 	int            id;         // The ID, assigned by the grammar, as the relative distance to the axiom
 } Element;

#### <a name="Grammar_type"><span class="classifier">type</span> `Grammar`</a>


```c
typedef struct Grammar {
	ParsingElement*  axiom;       // The axiom
	ParsingElement*  skip;        // The skipped element
	int              axiomCount;  // The count of parsing elemetns in axiom
	int              skipCount;   // The count of parsing elements in skip
	Element**        elements;    // The set of all elements in the grammar
	bool             isVerbose;
} Grammar;
```


#### <a name="Grammar_constructor"><span class="classifier">constructor</span> `Grammar`</a>


```c
Grammar* Grammar_new(void);
```


#### <a name="Grammar_free_destructor"><span class="classifier">destructor</span> `Grammar_free`</a>


```c
void Grammar_free(Grammar* this);
```


#### <a name="Grammar_prepare_method"><span class="classifier">method</span> `Grammar_prepare`</a>


```c
void Grammar_prepare ( Grammar* this );
```


#### <a name="Grammar_symbolsCount_method"><span class="classifier">method</span> `Grammar_symbolsCount`</a>


```c
int Grammar_symbolsCount ( Grammar* this );
```


#### <a name="Grammar_parseIterator_method"><span class="classifier">method</span> `Grammar_parseIterator`</a>


```c
ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator );
```


#### <a name="Grammar_parsePath_method"><span class="classifier">method</span> `Grammar_parsePath`</a>


```c
ParsingResult* Grammar_parsePath( Grammar* this, const char* path );
```


#### <a name="Grammar_parseString_method"><span class="classifier">method</span> `Grammar_parseString`</a>


```c
ParsingResult* Grammar_parseString( Grammar* this, const char* text );
```


#### <a name="Grammar_freeElements_method"><span class="classifier">method</span> `Grammar_freeElements`</a>


```c
void Grammar_freeElements(Grammar* this);
```


Elements
--------

#### <a name="WalkingCallback_callback"><span class="classifier">callback</span> `WalkingCallback`</a>


```c
typedef int (*WalkingCallback)(Element* this, int step, void* context);
```


#### <a name="Element_walk_method"><span class="classifier">method</span> `Element_walk`</a>


```c
int Element_walk( Element* this, WalkingCallback callback, void* context);
```


#### <a name="Element__walk_method"><span class="classifier">method</span> `Element__walk`</a>


```c
int Element__walk( Element* this, WalkingCallback callback, int step, void* context);
```


### Parsing Elements

Parsing elements are the core elements that recognize and process input
data. There are 4 basic types: `Work`, `Token`, `Group` and `Rule`.

Parsing elements offer two main operations: `recognize` and `process`.
The `recognize` method generates a `Match` object (that might be the `FAILURE`
singleton if the data was not recognized). The `process` method tranforms
corresponds to a user-defined action that transforms the `Match` object
and returns the generated value.

Parsing element are assigned an `id` that corresponds to their breadth-first distance
to the axiom. Before parsing, the grammar will re-assign the parsing element's
id accordingly.


#### <a name="Match_type"><span class="classifier">type</span> `Match`</a>


```c
typedef struct Match {
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
```


#### <a name="STATUS_INIT_define"><span class="classifier">define</span> `STATUS_INIT`</a>

 The different values for a match (or iterator)'s status

```c
#define STATUS_INIT        '-'
```


#### <a name="STATUS_PROCESSING_define"><span class="classifier">define</span> `STATUS_PROCESSING`</a>


```c
#define STATUS_PROCESSING  '~'
```


#### <a name="STATUS_MATCHED_define"><span class="classifier">define</span> `STATUS_MATCHED`</a>


```c
#define STATUS_MATCHED     'M'
```


#### <a name="STATUS_SUCCESS_define"><span class="classifier">define</span> `STATUS_SUCCESS`</a>


```c
#define STATUS_SUCCESS     'S'
```


#### <a name="STATUS_PARTIAL_define"><span class="classifier">define</span> `STATUS_PARTIAL`</a>


```c
#define STATUS_PARTIAL     's'
```


#### <a name="STATUS_FAILED_define"><span class="classifier">define</span> `STATUS_FAILED`</a>


```c
#define STATUS_FAILED      'X'
```


#### <a name="STATUS_INPUT_ENDED_define"><span class="classifier">define</span> `STATUS_INPUT_ENDED`</a>


```c
#define STATUS_INPUT_ENDED '.'
```


#### <a name="STATUS_ENDED_define"><span class="classifier">define</span> `STATUS_ENDED`</a>


```c
#define STATUS_ENDED       'E'
```


#### <a name="TYPE_ELEMENT_define"><span class="classifier">define</span> `TYPE_ELEMENT`</a>


```c
#define TYPE_ELEMENT    'E'
```


#### <a name="TYPE_WORD_define"><span class="classifier">define</span> `TYPE_WORD`</a>


```c
#define TYPE_WORD       'W'
```


#### <a name="TYPE_TOKEN_define"><span class="classifier">define</span> `TYPE_TOKEN`</a>


```c
#define TYPE_TOKEN      'T'
```


#### <a name="TYPE_GROUP_define"><span class="classifier">define</span> `TYPE_GROUP`</a>


```c
#define TYPE_GROUP      'G'
```


#### <a name="TYPE_RULE_define"><span class="classifier">define</span> `TYPE_RULE`</a>


```c
#define TYPE_RULE       'R'
```


#### <a name="TYPE_CONDITION_define"><span class="classifier">define</span> `TYPE_CONDITION`</a>


```c
#define TYPE_CONDITION  'c'
```


#### <a name="TYPE_PROCEDURE_define"><span class="classifier">define</span> `TYPE_PROCEDURE`</a>


```c
#define TYPE_PROCEDURE  'p'
```


#### <a name="TYPE_REFERENCE_define"><span class="classifier">define</span> `TYPE_REFERENCE`</a>


```c
#define TYPE_REFERENCE  '#'
```


#### <a name="ID_UNBOUND_define"><span class="classifier">define</span> `ID_UNBOUND`</a>

 A parsing element that is not bound to a grammar will have ID_UNBOUND
	 by default.

```c
#define ID_UNBOUND      -10
```


#### <a name="ID_BINDING_define"><span class="classifier">define</span> `ID_BINDING`</a>

 A parsing element that being bound to a grammar (see `Grammar_prepare`)
	 will have an id of `ID_BINDING` temporarily.

```c
#define ID_BINDING       -1
```


#### <a name="FAILURE_S_singleton"><span class="classifier">singleton</span> `FAILURE_S`</a>

 A specific match that indicates a failure

```c
extern Match FAILURE_S;
```


#### <a name="FAILURE_shared"><span class="classifier">shared</span> `FAILURE`</a>


```c
extern Match* FAILURE;
```


#### <a name="Match_Empty_operation"><span class="classifier">operation</span> `Match_Empty`</a>

 Creates new empty (successful) match

```c
Match* Match_Empty(Element* element, ParsingContext* context);
```


#### <a name="Match_Success_operation"><span class="classifier">operation</span> `Match_Success`</a>

 Creates a new successful match of the given length

```c
Match* Match_Success(size_t length, Element* element, ParsingContext* context);
```


#### <a name="Match_constructor"><span class="classifier">constructor</span> `Match`</a>


```c
Match* Match_new(void);
```


#### <a name="Match_free_destructor"><span class="classifier">destructor</span> `Match_free`</a>

 Frees the given match. If the match is `FAILURE`, then it won't
	 be feed. This means that most of the times you won't need to free
	 a failed match, as it's likely to be the `FAILURE` singleton.

```c
void Match_free(Match* this);
```


#### <a name="Match_isSuccess_method"><span class="classifier">method</span> `Match_isSuccess`</a>


```c
bool Match_isSuccess(Match* this);
```


#### <a name="Match_getOffset_method"><span class="classifier">method</span> `Match_getOffset`</a>


```c
int Match_getOffset(Match* this);
```


#### <a name="Match_getLength_method"><span class="classifier">method</span> `Match_getLength`</a>


```c
int Match_getLength(Match* this);
```


#### <a name="Match__walk_method"><span class="classifier">method</span> `Match__walk`</a>


```c
int Match__walk(Match* this, WalkingCallback callback, int step, void* context );
```


#### <a name="Match_countAll_method"><span class="classifier">method</span> `Match_countAll`</a>


```c
int Match_countAll(Match* this);
```


#### <a name="ParsingElement_type"><span class="classifier">type</span> `ParsingElement`</a>


```c
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
```


#### <a name="ParsingElement_Is_operation"><span class="classifier">operation</span> `ParsingElement_Is`</a>

 Tells if the given pointer is a pointer to a ParsingElement.

```c
bool         ParsingElement_Is(void *);
```


#### <a name="ParsingElement_constructor"><span class="classifier">constructor</span> `ParsingElement`</a>

 Creates a new parsing element and adds the given referenced
	 parsing elements as children. Note that this is an internal
	 constructor, and you should use the specialized versions instead.

```c
ParsingElement* ParsingElement_new(Reference* children[]);
```


#### <a name="ParsingElement_free_destructor"><span class="classifier">destructor</span> `ParsingElement_free`</a>


```c
void ParsingElement_free(ParsingElement* this);
```


#### <a name="ParsingElement_add_method"><span class="classifier">method</span> `ParsingElement_add`</a>

 Adds a new reference as child of this parsing element. This will only
	 be effective for composite parsing elements such as `Rule` or `Token`.

```c
ParsingElement* ParsingElement_add(ParsingElement *this, Reference *child);
```


#### <a name="ParsingElement_clear_method"><span class="classifier">method</span> `ParsingElement_clear`</a>


```c
ParsingElement* ParsingElement_clear(ParsingElement *this);
```


#### <a name="ParsingElement_clear_method"><span class="classifier">method</span> `ParsingElement_clear`</a>

 Returns the match for this parsing element for the given iterator's state.
	 inline Match* ParsingElement_recognize( ParsingElement* this, ParsingContext* context );

#### <a name="ParsingElement_process_method"><span class="classifier">method</span> `ParsingElement_process`</a>

 Processes the given match once the parsing element has fully succeeded. This
	 is where user-bound actions will be applied, and where you're most likely
	 to do things such as construct an AST.

```c
Match* ParsingElement_process( ParsingElement* this, Match* match );
```


#### <a name="ParsingElement_name_method"><span class="classifier">method</span> `ParsingElement_name`</a>

 Transparently sets the name of the element

```c
ParsingElement* ParsingElement_name( ParsingElement* this, const char* name );
```


### Word

Words recognize a static string at the current iterator location.


#### <a name="WordConfig_type"><span class="classifier">type</span> `WordConfig`</a>

 The parsing element configuration information that is used by the
	 `Token` methods.

```c
typedef struct WordConfig {
	const char* word;
	size_t      length;
} WordConfig;
```


#### <a name="ParsingElement_constructor"><span class="classifier">constructor</span> `ParsingElement`</a>


```c
ParsingElement* Word_new(const char* word);
```


#### <a name="Word_free_destructor"><span class="classifier">destructor</span> `Word_free`</a>


```c
void Word_free(ParsingElement* this);
```


#### <a name="Word_recognize_method"><span class="classifier">method</span> `Word_recognize`</a>

 The specialized match function for token parsing elements.

```c
Match*          Word_recognize(ParsingElement* this, ParsingContext* context);
```


#### <a name="Word_word_method"><span class="classifier">method</span> `Word_word`</a>


```c
const char* Word_word(ParsingElement* this);
```


#### <a name="WordMatch_group_method"><span class="classifier">method</span> `WordMatch_group`</a>


```c
const char* WordMatch_group(Match* match);
```


### Tokens

Tokens are regular expression based parsing elements. They do not have
any children and test if the regular expression matches exactly at the
iterator's current location.


#### <a name="TokenConfig_type"><span class="classifier">type</span> `TokenConfig`</a>

 The parsing element configuration information that is used by the
	 `Token` methods.

```c
typedef struct TokenConfig {
	const char* expr;
#ifdef WITH_PCRE
	pcre*       regexp;
	pcre_extra* extra;
#endif
} TokenConfig;
```


#### <a name="TokenMatch_type"><span class="classifier">type</span> `TokenMatch`</a>


```c
typedef struct TokenMatch {
	int             count;
	const char**    groups;
} TokenMatch;
```


#### <a name="Token_new_method"><span class="classifier">method</span> `Token_new`</a>

 Creates a new token with the given POSIX extended regular expression

```c
ParsingElement* Token_new(const char* expr);
```


#### <a name="Token_free_destructor"><span class="classifier">destructor</span> `Token_free`</a>


```c
void Token_free(ParsingElement*);
```


#### <a name="Token_recognize_method"><span class="classifier">method</span> `Token_recognize`</a>

 The specialized match function for token parsing elements.

```c
Match*          Token_recognize(ParsingElement* this, ParsingContext* context);
```


#### <a name="Token_expr_method"><span class="classifier">method</span> `Token_expr`</a>


```c
const char* Token_expr(ParsingElement* this);
```


#### <a name="TokenMatch_free_method"><span class="classifier">method</span> `TokenMatch_free`</a>

 Frees the `TokenMatch` created in `Token_recognize`

```c
void TokenMatch_free(Match* match);
```


#### <a name="TokenMatch_group_method"><span class="classifier">method</span> `TokenMatch_group`</a>


```c
const char* TokenMatch_group(Match* match, int index);
```


#### <a name="TokenMatch_count_method"><span class="classifier">method</span> `TokenMatch_count`</a>


```c
int TokenMatch_count(Match* match);
```


### References

We've seen that parsing elements can have `children`. However, a parsing
element's children are not directly parsing elements but rather
parsing elements' `Reference`s. This is why the `ParsingElement_add` takes
a `Reference` object as parameter.

References allow to share a single parsing element between many different
composite parsing elements, while decorating them with additional information
such as their cardinality (`ONE`, `OPTIONAL`, `MANY` and `MANY_OPTIONAL`)
and a `name` that will allow `process` actions to easily access specific
parts of the parsing element.

#### <a name="Reference_type"><span class="classifier">type</span> `Reference`</a>


```c
typedef struct Reference {
	char            type;            // Set to Reference_T, to disambiguate with ParsingElement
	int             id;              // The ID, assigned by the grammar, as the relative distance to the axiom
	char            cardinality;     // Either ONE (default), OPTIONAL, MANY or MANY_OPTIONAL
	const char*     name;            // The name of the reference (optional)
	struct ParsingElement* element;  // The reference to the parsing element
	struct Reference*      next;     // The next child reference in the parsing elements
} Reference;
```


#### <a name="CARDINALITY_OPTIONAL_define"><span class="classifier">define</span> `CARDINALITY_OPTIONAL`</a>

 The different values for the `Reference` cardinality.

```c
#define CARDINALITY_OPTIONAL      '?'
```


#### <a name="CARDINALITY_ONE_define"><span class="classifier">define</span> `CARDINALITY_ONE`</a>


```c
#define CARDINALITY_ONE           '1'
```


#### <a name="CARDINALITY_MANY_OPTIONAL_define"><span class="classifier">define</span> `CARDINALITY_MANY_OPTIONAL`</a>


```c
#define CARDINALITY_MANY_OPTIONAL '*'
```


#### <a name="CARDINALITY_MANY_define"><span class="classifier">define</span> `CARDINALITY_MANY`</a>


```c
#define CARDINALITY_MANY          '+'
```



#### <a name="Reference_Is_operation"><span class="classifier">operation</span> `Reference_Is`</a>

 Tells if the given pointer is a pointer to Reference

```c
bool Reference_Is(void * this);
```


#### <a name="Reference_Ensure_operation"><span class="classifier">operation</span> `Reference_Ensure`</a>

 Ensures that the given element (or reference) is a reference.

```c
Reference* Reference_Ensure(void* elementOrReference);
```


#### <a name="Reference_FromElement_operation"><span class="classifier">operation</span> `Reference_FromElement`</a>

 Returns a new reference wrapping the given parsing element

```c
Reference* Reference_FromElement(ParsingElement* element);
```


#### <a name="Reference_constructor"><span class="classifier">constructor</span> `Reference`</a>

 References are typically owned by their single parent composite element.

```c
Reference* Reference_new(void);
```


#### <a name="Reference_free_destructor"><span class="classifier">destructor</span> `Reference_free`</a>


```c
void Reference_free(Reference* this);
```


#### <a name="Reference_cardinality_method"><span class="classifier">method</span> `Reference_cardinality`</a>

 Sets the cardinality of this reference, returning it transprently.

```c
Reference* Reference_cardinality(Reference* this, char cardinality);
```


#### <a name="Reference_name_method"><span class="classifier">method</span> `Reference_name`</a>


```c
Reference* Reference_name(Reference* this, const char* name);
```


#### <a name="Reference_hasNext_method"><span class="classifier">method</span> `Reference_hasNext`</a>


```c
bool Reference_hasNext(Reference* this);
```


#### <a name="Reference_hasElement_method"><span class="classifier">method</span> `Reference_hasElement`</a>


```c
bool Reference_hasElement(Reference* this);
```


#### <a name="Reference__walk_method"><span class="classifier">method</span> `Reference__walk`</a>


```c
int Reference__walk( Reference* this, WalkingCallback callback, int step, void* nothing );
```


#### <a name="Reference_recognize_method"><span class="classifier">method</span> `Reference_recognize`</a>

 Returns the matched value corresponding to the first match of this reference.
	 `OPTIONAL` references might return `EMPTY`, `ONE` references will return
	 a match with a `next=NULL` while `MANY` may return a match with a `next`
	 pointing to the next match.

```c
Match* Reference_recognize(Reference* this, ParsingContext* context);
```


### Groups

Groups are composite parsing elements that will return the first matching reference's
match. Think of it as a logical `or`.

#### <a name="ParsingElement_constructor"><span class="classifier">constructor</span> `ParsingElement`</a>


```c
ParsingElement* Group_new(Reference* children[]);
```


#### <a name="Group_recognize_method"><span class="classifier">method</span> `Group_recognize`</a>


```c
Match*          Group_recognize(ParsingElement* this, ParsingContext* context);
```


### Rules

Groups are composite parsing elements that only succeed if all their
matching reference's.

#### <a name="ParsingElement_constructor"><span class="classifier">constructor</span> `ParsingElement`</a>


```c
ParsingElement* Rule_new(Reference* children[]);
```


#### <a name="Rule_recognize_method"><span class="classifier">method</span> `Rule_recognize`</a>


```c
Match*          Rule_recognize(ParsingElement* this, ParsingContext* context);
```


### Procedures

Procedures are parsing elements that do not consume any input, always
succeed and usually have a side effect, such as setting a variable
in the parsing context.

#### <a name="ProcedureCallback_callback"><span class="classifier">callback</span> `ProcedureCallback`</a>


```c
typedef void (*ProcedureCallback)(ParsingElement* this, ParsingContext* context);
```


#### <a name="MatchCallback_callback"><span class="classifier">callback</span> `MatchCallback`</a>


```c
typedef void (*MatchCallback)(Match* m);
```


#### <a name="ParsingElement_constructor"><span class="classifier">constructor</span> `ParsingElement`</a>


```c
ParsingElement* Procedure_new(ProcedureCallback c);
```


#### <a name="Procedure_recognize_method"><span class="classifier">method</span> `Procedure_recognize`</a>


```c
Match*          Procedure_recognize(ParsingElement* this, ParsingContext* context);
```


### Conditions

Conditions, like procedures, execute arbitrary code when executed, but
they might return a FAILURE.

#### <a name="ConditionCallback_callback"><span class="classifier">callback</span> `ConditionCallback`</a>


```c
typedef Match* (*ConditionCallback)(ParsingElement*, ParsingContext*);
```


#### <a name="ParsingElement_constructor"><span class="classifier">constructor</span> `ParsingElement`</a>


```c
ParsingElement* Condition_new(ConditionCallback c);
```


#### <a name="Condition_recognize_method"><span class="classifier">method</span> `Condition_recognize`</a>


```c
Match*          Condition_recognize(ParsingElement* this, ParsingContext* context);
```


The parsing process
-------------------

The parsing itself is the process of taking a `grammar` and applying it
to an input stream of data, represented by the `iterator`.

The grammar's `axiom` will be matched against the `iterator`'s current
position, and if necessary, the grammar's `skip` parsing element
will be applied to advance the iterator.

```c
typedef struct ParsingStep    ParsingStep;
typedef struct ParsingOffset  ParsingOffset;
```


#### <a name="ParsingStats_type"><span class="classifier">type</span> `ParsingStats`</a>


```c
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
```


#### <a name="ParsingStats_constructor"><span class="classifier">constructor</span> `ParsingStats`</a>


```c
ParsingStats* ParsingStats_new(void);
```


#### <a name="ParsingStats_free_destructor"><span class="classifier">destructor</span> `ParsingStats_free`</a>


```c
void ParsingStats_free(ParsingStats* this);
```


#### <a name="ParsingStats_setSymbolsCount_method"><span class="classifier">method</span> `ParsingStats_setSymbolsCount`</a>


```c
void ParsingStats_setSymbolsCount(ParsingStats* this, size_t t);
```


#### <a name="ParsingStats_registerMatch_method"><span class="classifier">method</span> `ParsingStats_registerMatch`</a>


```c
Match* ParsingStats_registerMatch(ParsingStats* this, Element* e, Match* m);
```


#### <a name="ParsingContext_type"><span class="classifier">type</span> `ParsingContext`</a>


```c
typedef struct ParsingContext {
	struct Grammar*              grammar;      // The grammar used to parse
	struct Iterator*             iterator;     // Iterator on the input data
	struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
	struct ParsingOffset* current;      // The current parsing offset
	struct ParsingStats*  stats;
} ParsingContext;
```


#### <a name="ParsingContext_constructor"><span class="classifier">constructor</span> `ParsingContext`</a>


```c
ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator );
```


#### <a name="ParsingContext_text_method"><span class="classifier">method</span> `ParsingContext_text`</a>


```c
iterated_t* ParsingContext_text( ParsingContext* this );
```


#### <a name="ParsingContext_free_destructor"><span class="classifier">destructor</span> `ParsingContext_free`</a>


```c
void ParsingContext_free( ParsingContext* this );
```


#### <a name="ParsingResult_type"><span class="classifier">type</span> `ParsingResult`</a>


```c
typedef struct ParsingResult {
	char            status;
	Match*          match;
	ParsingContext* context;
} ParsingResult;
```


#### <a name="ParsingResult_constructor"><span class="classifier">constructor</span> `ParsingResult`</a>


```c
ParsingResult* ParsingResult_new(Match* match, ParsingContext* context);
```


#### <a name="ParsingResult_free_method"><span class="classifier">method</span> `ParsingResult_free`</a>

 Frees this parsing result instance as well as all the matches it referes to.

```c
void ParsingResult_free(ParsingResult* this);
```


#### <a name="ParsingResult_isFailure_method"><span class="classifier">method</span> `ParsingResult_isFailure`</a>


```c
bool ParsingResult_isFailure(ParsingResult* this);
```


#### <a name="ParsingResult_isPartial_method"><span class="classifier">method</span> `ParsingResult_isPartial`</a>


```c
bool ParsingResult_isPartial(ParsingResult* this);
```


#### <a name="ParsingResult_isComplete_method"><span class="classifier">method</span> `ParsingResult_isComplete`</a>


```c
bool ParsingResult_isComplete(ParsingResult* this);
```


#### <a name="ParsingResult_text_method"><span class="classifier">method</span> `ParsingResult_text`</a>


```c
iterated_t* ParsingResult_text(ParsingResult* this);
```


#### <a name="ParsingResult_textOffset_method"><span class="classifier">method</span> `ParsingResult_textOffset`</a>


```c
int ParsingResult_textOffset(ParsingResult* this);
```


#### <a name="ParsingResult_remaining_method"><span class="classifier">method</span> `ParsingResult_remaining`</a>


```c
size_t ParsingResult_remaining(ParsingResult* this);
```


The result of _recognizing_ parsing elements at given offsets within the
input stream is stored in `ParsingOffset`. Each parsing offset is a stack
of `ParsingStep`, corresponding to successive attempts at matching
parsing elements at the current position.


The parsing offset is a stack of parsing steps, where the tail is the most
specific parsing step. By following the tail's previous parsing step,
you can unwind the stack.

The parsing steps each have an offset within the iterated stream. Offsets
where data has been fully extracted (ie, a leaf parsing element has matched
and processing returned a NOTHING) can be freed as they are not necessary
any more.

#### <a name="ParsingOffset_type"><span class="classifier">type</span> `ParsingOffset`</a>


```c
typedef struct ParsingOffset {
	size_t                offset; // The offset matched in the input stream
	ParsingStep*          last;   // The last matched parsing step (ie. corresponding to the most specialized parsing element)
	struct ParsingOffset* next;   // The link to the next offset (if any)
} ParsingOffset;
```


#### <a name="ParsingOffset_constructor"><span class="classifier">constructor</span> `ParsingOffset`</a>


```c
ParsingOffset* ParsingOffset_new( size_t offset );
```


#### <a name="ParsingOffset_free_destructor"><span class="classifier">destructor</span> `ParsingOffset_free`</a>


```c
void ParsingOffset_free( ParsingOffset* this );
```


The parsing step allows to memoize the state of a parsing element at a given
offset. This is the data structure that will be manipulated and created/destroyed
the most during the parsing process.

```c
typedef struct ParsingStep {
	ParsingElement*     element;       // The parsing elemnt we're matching
	char                step;          // The step corresponds to current child's index (0 for token/word)
	unsigned int        iteration;     // The current iteration (on the step)
	char                status;        // Match status `STATUS_{INIT|PROCESSING|FAILED}`
	Match*              match;         // The corresponding match, if any.
	struct ParsingStep* previous;      // The previous parsing step on the parsing offset's stack
} ParsingStep;
```


#### <a name="ParsingStep_constructor"><span class="classifier">constructor</span> `ParsingStep`</a>


```c
ParsingStep* ParsingStep_new( ParsingElement* element );
```


#### <a name="ParsingStep_free_destructor"><span class="classifier">destructor</span> `ParsingStep_free`</a>


```c
void ParsingStep_free( ParsingStep* this );
```


Processor
---------

```c
typedef struct Processor Processor;
```


#### <a name="ProcessorCallback_callback"><span class="classifier">callback</span> `ProcessorCallback`</a>


```c
typedef void (*ProcessorCallback)(Processor* processor, Match* match);

typedef struct Processor {
	ProcessorCallback   fallback;
	ProcessorCallback*  callbacks;
	int                 callbacksCount;
} Processor;
```


#### <a name="Processor_constructor"><span class="classifier">constructor</span> `Processor`</a>


```c
Processor* Processor_new( );
```


#### <a name="Processor_free_method"><span class="classifier">method</span> `Processor_free`</a>


```c
void Processor_free(Processor* this);
```


#### <a name="Processor_register_method"><span class="classifier">method</span> `Processor_register`</a>


```c
void Processor_register (Processor* this, int symbolID, ProcessorCallback callback) ;
```


#### <a name="Processor_process_method"><span class="classifier">method</span> `Processor_process`</a>


```c
int Processor_process (Processor* this, Match* match, int step);
```


Utilities
---------

#### <a name="Utilities_indent_method"><span class="classifier">method</span> `Utilities_indent`</a>


```c
void Utilities_indent( ParsingElement* this, ParsingContext* context );
```


#### <a name="Utilities_dedent_method"><span class="classifier">method</span> `Utilities_dedent`</a>


```c
void Utilities_dedent( ParsingElement* this, ParsingContext* context );
```


#### <a name="Utilites_checkIndent_method"><span class="classifier">method</span> `Utilites_checkIndent`</a>


```c
Match* Utilites_checkIndent( ParsingElement *this, ParsingContext* context );
```


Syntax Sugar
------------

The parsing library provides a set of macros that make defining grammars
a much easier task. A grammar is usually defined in the following way:

- leaf symbols (words & tokens) are defined ;
- compound symbolds (rules & groups) are defined.

Let's take as simple grammar and define it with the straight API:

```
// Leaf symbols
ParsingElement* s_NUMBER   = Token_new("\\d+");
ParsingElement* s_VARIABLE = Token_new("\\w+");
ParsingElement* s_OPERATOR = Token_new("[\\+\\-\\*\\/]");

// We also attach names to the symbols so that debugging will be easier
ParsingElement_name(s_NUMBER,   "NUMBER");
ParsingElement_name(s_VARIABLE, "VARIABLE");
ParsingElement_name(s_OPERATOR, "OPERATOR");

// Now we defined the compound symbols
ParsingElement* s_Value    = Group_new((Reference*[3]),{
Reference_cardinality(Reference_Ensure(s_NUMBER),   CARDINALITY_ONE),
Reference_cardinality(Reference_Ensure(s_VARIABLE), CARDINALITY_ONE)
NULL
});
ParsingElement* s_Suffix    = Rule_new((Reference*[3]),{
Reference_cardinality(Reference_Ensure(s_OPERATOR),  CARDINALITY_ONE),
Reference_cardinality(Reference_Ensure(s_Value),     CARDINALITY_ONE)
NULL
});
* ParsingElement* s_Expr    = Rule_new((Reference*[3]),{
Reference_cardinality(Reference_Ensure(s_Value),  CARDINALITY_ONE),
Reference_cardinality(Reference_Ensure(s_Suffix), CARDINALITY_MANY_OPTIONAL)
NULL
});

// We define the names as well
ParsingElement_name(s_Value,  "Value");
ParsingElement_name(s_Suffix, "Suffix");
ParsingElement_name(s_Expr, "Expr");
```

As you can see, this is quite verbose and makes reading the grammar declaration
a difficult task. Let's introduce a set of macros that will make expressing
grammars much easier.

Symbol declaration & creation
-----------------------------

#### <a name="SYMBOL_macro"><span class="classifier">macro</span> `SYMBOL`</a>

 Declares a symbol of name `n` as being parsing element `e`.

```c
#define SYMBOL(n,e)       ParsingElement* s_ ## n = ParsingElement_name(e, #n);
```


#### <a name="WORD_macro"><span class="classifier">macro</span> `WORD`</a>

 Creates a `Word` parsing element with the given regular expression

```c
#define WORD(v)           Word_new(v)
```


#### <a name="TOKEN_macro"><span class="classifier">macro</span> `TOKEN`</a>

 Creates a `Token` parsing element with the given regular expression

```c
#define TOKEN(v)          Token_new(v)
```


#### <a name="RULE_macro"><span class="classifier">macro</span> `RULE`</a>

 Creates a `Rule` parsing element with the references or parsing elements
	 as children.

```c
#define RULE(...)         Rule_new((Reference*[(VA_ARGS_COUNT(__VA_ARGS__)+1)]){__VA_ARGS__,NULL})
```


#### <a name="GROUP_macro"><span class="classifier">macro</span> `GROUP`</a>

 Creates a `Group` parsing element with the references or parsing elements
	 as children.

```c
#define GROUP(...)        Group_new((Reference*[(VA_ARGS_COUNT(__VA_ARGS__)+1)]){__VA_ARGS__,NULL})
```


#### <a name="PROCEDURE_macro"><span class="classifier">macro</span> `PROCEDURE`</a>

 Creates a `Procedure` parsing element

```c
#define PROCEDURE(f)      Procedure_new(f)
```


#### <a name="CONDITION_macro"><span class="classifier">macro</span> `CONDITION`</a>

 Creates a `Condition` parsing element

```c
#define CONDITION(f)      Condition_new(f)
```


Symbol reference & cardinality
------------------------------

#### <a name="_S_macro"><span class="classifier">macro</span> `_S`</a>

 Refers to symbol `n`, wrapping it in a `CARDINALITY_ONE` reference

```c
#define _S(n)             ONE(s_ ## n)
```


#### <a name="_O_macro"><span class="classifier">macro</span> `_O`</a>

 Refers to symbol `n`, wrapping it in a `CARDINALITY_OPTIONAL` reference

```c
#define _O(n)             OPTIONAL(s_ ## n)
```


#### <a name="_M_macro"><span class="classifier">macro</span> `_M`</a>

 Refers to symbol `n`, wrapping it in a `CARDINALITY_MANY` reference

```c
#define _M(n)             MANY(s_ ## n)
```


#### <a name="_MO_macro"><span class="classifier">macro</span> `_MO`</a>

 Refers to symbol `n`, wrapping it in a `CARDINALITY_MANY_OPTIONAL` reference

```c
#define _MO(n)            MANY_OPTIONAL(s_ ## n)
```


#### <a name="_AS_macro"><span class="classifier">macro</span> `_AS`</a>

 Sets the name of reference `r` to be v

```c
#define _AS(r,v)          Reference_name(Reference_Ensure(r), v)
```


Supporting macros
-----------------

The following set of macros is mostly used by the set of macros above.
You probably won't need to use them directly.

#### <a name="NAME_macro"><span class="classifier">macro</span> `NAME`</a>

 Sets the name of the given parsing element `e` to be the name `n`.

```c
#define NAME(n,e)         ParsingElement_name(e,n)
```


#### <a name="ONE_macro"><span class="classifier">macro</span> `ONE`</a>

 Sets the given reference or parsing element's reference to CARDINALITY_ONE
	 If a parsing element is given, it will be automatically wrapped in a reference.

```c
#define ONE(v)            Reference_cardinality(Reference_Ensure(v), CARDINALITY_ONE)
```


#### <a name="OPTIONAL_macro"><span class="classifier">macro</span> `OPTIONAL`</a>

 Sets the given reference or parsing element's reference to CARDINALITY_OPTIONAL
	 If a parsing element is given, it will be automatically wrapped in a reference.

```c
#define OPTIONAL(v)       Reference_cardinality(Reference_Ensure(v), CARDINALITY_OPTIONAL)
```


#### <a name="MANY_macro"><span class="classifier">macro</span> `MANY`</a>

 Sets the given reference or parsing element's reference to CARDINALITY_MANY
	 If a parsing element is given, it will be automatically wrapped in a reference.

```c
#define MANY(v)           Reference_cardinality(Reference_Ensure(v), CARDINALITY_MANY)
```


#### <a name="MANY_OPTIONAL_macro"><span class="classifier">macro</span> `MANY_OPTIONAL`</a>

 Sets the given reference or parsing element's reference to CARDINALITY_MANY_OPTIONAL
	 If a parsing element is given, it will be automatically wrapped in a reference.

```c
#define MANY_OPTIONAL(v)  Reference_cardinality(Reference_Ensure(v), CARDINALITY_MANY_OPTIONAL)
```


Grammar declaration with macros
-------------------------------

The same grammar that we defined previously can now be expressed in the
following way:

```
SYMBOL(NUMBER,   TOKEN("\\d+"))
SYMBOL(VAR,      TOKEN("\\w+"))
SYMBOL(OPERATOR, TOKEN("[\\+\\-\\*\\/]"))

SYMBOL(Value,  GROUP( _S(NUMBER),   _S(VAR)     ))
SYMBOL(Suffix, RULE(  _S(OPERATOR), _S(Value)   ))
SYMBOL(Expr,   RULE(  _S(Value),    _MO(Suffix) ))
```

All symbols will be define as `s_XXX`, so that you can do:

```
ParsingGrammar* g = Grammar_new();
g->axiom = s_Expr;
```

License
=======

Revised BSD License Copyright (c) 2014, FFunction inc (1165373771 Quebec
inc) All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer. Redistributions in binary
form must reproduce the above copyright notice, this list of conditions and
the following disclaimer in the documentation and/or other materials
provided with the distribution. Neither the name of the FFunction inc
(CANADA) nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
