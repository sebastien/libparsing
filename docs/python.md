Python API
==========

Input data
----------

The parsing library can be used via Python through the `libparsing` module. 

### <a name="Grammar_class"><span class="classifier">class</span> `Grammar`</a>

The `Grammar` is the concrete definition of the language you're going to parse. It provides methods to construct parsing elements and define rules.

```python
from libparsing import Grammar
g = Grammar()
```

#### <a name="Grammar_parseString_method"><span class="classifier">method</span> `Grammar.parseString`</a>

Parses the given string and returns a `ParsingResult`.

```python
def parseString(self, text: str) -> ParsingResult
```

#### <a name="Grammar_rule_method"><span class="classifier">method</span> `Grammar.rule`</a>

Creates a `Rule` composite parsing element that matches all given children in sequence.

```python
def rule(self, name: str, *children: ParsingElement) -> Rule
```

#### <a name="Grammar_token_method"><span class="classifier">method</span> `Grammar.token`</a>

Creates a `Token` parsing element using a PCRE regular expression.

```python
def token(self, name: str, expr: str) -> Token
```

#### <a name="Grammar_group_method"><span class="classifier">method</span> `Grammar.group`</a>

Creates a `Group` composite parsing element that matches the first successful child reference. Think of it as a logical `or`.

```python
def group(self, name: str, *children: ParsingElement) -> Group
```

#### <a name="Grammar_word_method"><span class="classifier">method</span> `Grammar.word`</a>

Creates a `Word` parsing element that matches an exact string.

```python
def word(self, name: str, text: str) -> Word
```

#### <a name="Grammar_axiom_method"><span class="classifier">method</span> `Grammar.axiom`</a>

Sets the grammar's axiom, which is the starting element of the grammar.

```python
def axiom(self, element: ParsingElement) -> Grammar
```

#### <a name="Grammar_skip_method"><span class="classifier">method</span> `Grammar.skip`</a>

Sets the grammar's skipped element (e.g. whitespace).

```python
def skip(self, element: ParsingElement) -> Grammar
```

Elements
--------

### Parsing Elements

Parsing elements are the core elements that recognize and process input data. 

#### <a name="ParsingElement_class"><span class="classifier">class</span> `ParsingElement`</a>

The base class for all parsing elements.

*   `name`: The name of the parsing element.
*   `type`: The type code of the element (e.g., `b'T'`, `b'R'`).
*   `id`: The internal grammar ID.

It offers fluent modifiers to wrap elements in references:

*   `optional()`: Sets cardinality to `?` (0 or 1)
*   `oneOrMore()`: Sets cardinality to `+` (1 or more)
*   `zeroOrMore()`: Sets cardinality to `*` (0 or more)
*   `_as(name)`: Gives a name to a reference, accessible within matches.

#### <a name="Token_class"><span class="classifier">class</span> `Token`</a>
Inherits `ParsingElement`. Represents a PCRE regular expression match.

#### <a name="Word_class"><span class="classifier">class</span> `Word`</a>
Inherits `ParsingElement`. Represents an exact string match.

#### <a name="Group_class"><span class="classifier">class</span> `Group`</a>
Inherits `ParsingElement`. Logical OR for matching one of several child references.

#### <a name="Rule_class"><span class="classifier">class</span> `Rule`</a>
Inherits `ParsingElement`. Sequence for matching all child references in order.

#### <a name="Reference_class"><span class="classifier">class</span> `Reference`</a>
Wraps a parsing element with a cardinality (`1`, `?`, `*`, `+`) and an optional name for retrieving the match.


Matches & Results
-----------------

#### <a name="ParsingResult_class"><span class="classifier">class</span> `ParsingResult`</a>

The result of parsing a string.

*   `status`: The completion status.
*   `match`: The root `Match` object if parsing partially or completely succeeded.
*   `isSuccess()`: True if the parsing finished without failure.
*   `isFailure()`: True if the parsing failed.
*   `isComplete()`: True if the input was fully parsed without failure.

#### <a name="Match_class"><span class="classifier">class</span> `Match`</a>

Represents a successful match of a parsing element.

*   `name`: Name of the matched element or reference.
*   `value`: The matched string.
*   `group(index=0)`: Gets captured values or groups.
*   `offset`, `length`: Start and extent of the match.
*   `children`: List of child matches.
*   It supports iteration and subscripting (`match[name]`) to access named references.


Usage Example
-------------

```python
from libparsing import Grammar

g = Grammar()
s = g.symbols

# Leaf symbols
g.token("NUMBER", r"\d+")
g.word("PLUS", "+")
g.token("WS", r"\s+")

# Compound symbols
g.rule("Expr", 
    s.NUMBER._as("left"),
    s.PLUS,
    s.NUMBER._as("right")
)

# Setup grammar
g.skip(s.WS)
g.axiom(s.Expr)

# Parse
result = g.parseString("42 + 10")
if result.isComplete():
    m = result.match
    print(f"Matched: {m.value}")
    print(f"Left side: {m['left'].value}")
    print(f"Right side: {m['right'].value}")
else:
    print(result.describe())
```
