
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
pip install  libparsing    # From PIP
```

Note that for the above to work, you'll need a C compiler `libffi-dev`  and `libpcre-dev`.
On Ubuntu, do `sudo apt install build-essential libffi-dev libprcre-dev`.

To compile the C parsing module:

```shell
git clone http://github.com/sebastien/libparsing
cd libparsing
make
make install               # You can set PREFIX
```

`libparsing` works with GCC4 and Clang and is written following the `c11`
standard.

Documentation
=============

For the complete C API documentation, see [docs/libparsing.md](docs/libparsing.md).

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
