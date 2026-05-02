
#  libparsing
## C & Python Parsing Elements Grammar Library

```
Version :  1.0.0
URL     :  http://github.com/sebastien/parsing
README  :  https://cdn.rawgit.com/sebastien/libparsing/master/README.html
```

`libparsing` is a parsing element grammar (PEG) library written in C with
Python bindings and a TypeScript port.

It offers decent performance while allowing for a
lot of flexibility, below is a comparison of the performance of the JSON grammar,
comparing to Python's standard JSON and Lark's JSON implementation.

```
Benchmark: 10 iterations per parser per dataset
------------------------------------------------------------------------------------------
Dataset    Parser                 Median         Mean   Throughput    vs stdlib
------------------------------------------------------------------------------------------
1 KB       json.loads            24.4 us      26.2 us   56.57 MB/s        1.00x
           libparsing/C          76.0 us      76.0 us   18.16 MB/s         3.1x
           libparsing/ts        850.2 us      1.12 ms    1.62 MB/s        34.9x
           libparsing/py        363.9 us     374.8 us    3.79 MB/s        14.9x
           lark/py               1.81 ms      1.87 ms   762.6 KB/s        74.2x
           libparsing/pypy       1.88 ms      2.57 ms   734.7 KB/s        77.0x
           lark/pypy            10.00 ms     11.80 ms   137.9 KB/s       410.2x
------------------------------------------------------------------------------------------
100 KB     json.loads            4.22 ms      3.65 ms   23.78 MB/s        1.00x
           libparsing/C         10.22 ms     10.22 ms    9.83 MB/s         2.4x
           libparsing/ts        25.85 ms     26.25 ms    3.88 MB/s         6.1x
           libparsing/py        32.41 ms     32.10 ms    3.10 MB/s         7.7x
           lark/py             139.49 ms    139.72 ms   719.9 KB/s        33.0x
           libparsing/pypy      33.91 ms     33.67 ms    2.96 MB/s         8.0x
           lark/pypy            40.83 ms     43.61 ms    2.46 MB/s         9.7x
------------------------------------------------------------------------------------------
1 MB       json.loads           21.74 ms     23.09 ms   46.00 MB/s        1.00x
           libparsing/C        103.03 ms    103.03 ms    9.71 MB/s         4.7x
           libparsing/ts       236.87 ms    241.38 ms    4.22 MB/s        10.9x
           libparsing/py       326.37 ms    326.09 ms    3.06 MB/s        15.0x
           lark/py              1.376 s      1.395 s    726.9 KB/s        63.3x
           libparsing/pypy     218.70 ms    225.30 ms    4.57 MB/s        10.1x
           lark/pypy           364.05 ms    369.32 ms    2.75 MB/s        16.7x
------------------------------------------------------------------------------------------
```

As opposed to more traditional parsing techniques, the grammar is not compiled
but constructed using an API that allows dynamic update of the grammar.

The parser does not do any tokenization, instead the input stream is
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


# Installing

To install the Python parsing module:

```shell
pip install  --user libparsing # From PIP
```

Note that for the above to work, you'll need a C compiler `libffi-dev`  and `libpcre-dev`.
On Ubuntu, do `sudo apt install build-essential libffi-dev libprcre-dev`.

To compile the C parsing module:

```shell
git clone http://github.com/sebastien/libparsing
cd libparsing
make
make install               # You can set PREFIX
make install-link          # Symlink Python module into ~/.local/share/python
```

`libparsing` works with GCC4 and Clang and is written following the `c11`
standard.

# Documentation

For the complete C API documentation, see [docs/libparsing.md](docs/libparsing.md).

