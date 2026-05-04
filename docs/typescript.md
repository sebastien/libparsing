# TypeScript API

The pure TypeScript port of `libparsing` provides an object-oriented API that closely mirrors the Python bindings. It relies on standard JavaScript features (native `RegExp` and Garbage Collection) and comes with zero dependencies.

## Grammar

The `Grammar` is the main entry point to construct a parser. It maintains the rules and controls the parsing execution. 

```typescript
import { Grammar } from "libparsing";

const g = new Grammar({ name: "MyGrammar" });
```

### Factory Methods

The `Grammar` instance acts as a factory for parsing elements. The symbols are automatically registered inside the `symbols` dictionary, which allows attribute-style access (e.g. `g.symbols.NUMBER`).

- `word(name: string, pattern: string): Word`
  Recognizes a static literal string.
- `token(name: string, pattern: string): Token`
  Recognizes a regular expression pattern.
- `rule(name: string, ...children: (ParsingElement | Reference)[]): Rule`
  A sequence where all children must match in order.
- `group(name: string, ...children: (ParsingElement | Reference)[]): Group`
  An ordered choice (alternation) returning the first matching child.
- `procedure(name: string, callback: ProcedureCallback): Procedure`
  Executes a side effect without consuming input.
- `condition(name: string, callback: ConditionCallback): Condition`
  Succeeds (with zero length) if the callback returns true.

You can also use anonymous versions of these methods (`aword`, `atoken`, `arule`, `agroup`, `aprocedure`, `acondition`) which do not attach names or register into the `symbols` dictionary.

### Parsing Execution

- `parseString(text: string): ParsingResult`
  Parses the provided string using the defined grammar and returns a `ParsingResult`.
  Make sure to set the `axiom` property before calling this method. You can also specify an element to skip automatically (like whitespace) by setting the `skip` property.

## Parsing Elements and References

The parsing elements (`Word`, `Token`, `Group`, `Rule`, `Procedure`, `Condition`) form the abstract syntax tree of your grammar.

### Cardinality

References wrap a parsing element and dictate how many times it should match. You can adjust the cardinality of any parsing element using the following chainable methods:
- `.one()` - Must match exactly once (default).
- `.optional()` - Matches zero or one time.
- `.zeroOrMore()` - Matches zero or many times.
- `.oneOrMore()` - Matches one or many times.
- `.notEmpty()` - Matches conditionally based on non-empty results.

Example:
```typescript
g.rule("Expression", g.symbols.Value, g.symbols.Suffix.zeroOrMore());
```

### Named Slots
You can label specific references in your grammar for easier extraction during the processing phase:
- `._as(name: string)` - Associates a name to the reference.

Example:
```typescript
g.rule("Assignment", g.symbols.VAR._as("name"), g.symbols.EQ, g.symbols.Expr._as("value"));
```

## Match and ParsingResult

When `parseString` is called, it outputs a `ParsingResult`. 

### `ParsingResult`
This object gives you high-level information about the parsing attempt.
- `isSuccess()` / `isFailure()` / `isPartial()` / `isComplete()`: The resolution status of the parsing attempt.
- `match`: The root `Match` object if parsing succeeded.
- `context`: The `ParsingContext` holding the current offset and stats.
- `describe()`: Returns a nicely formatted description of the result (e.g., pointing out where a syntax error happened in the source input).

### `Match`
A `Match` represents a node in the successfully parsed tree. It carries matched data and relationships to parent and child nodes.
- `isSuccess` / `isFailed`: Match status.
- `value`: The matched text value for leaf elements (`Word`, `Token`).
- `group(index?: number)`: Extracts capture groups. For a `Token`, it returns regex capture groups.
- `get(indexOrKey?: number | string)`: Accesses child matches by index or by their named slot.
- `textFrom(input: string)`: Returns the raw matched substring from the input text.
- `children`: Pointer to the first child `Match` node.
- `next`: Pointer to the next sibling `Match` node.

## Processor

The `Processor` transforms the raw `Match` tree into a concrete Abstract Syntax Tree (AST) or directly interprets it. 

By subclassing `Processor` and defining methods named `on<SymbolName>`, the methods will be auto-discovered and bound to the corresponding grammar symbols.

- `asLazy()` (default) processes nodes only when requested.
- `asEager()` processes the tree bottom-up.

## Usage Example

Here is a complete example defining a simple arithmetic expression parser:

```typescript
import { Grammar, Processor, Match } from "libparsing";

// 1. Define the grammar
const g = new Grammar();

// Tokens
g.token("NUMBER", "\\d+");
g.token("VAR", "\\w+");
g.token("OPERATOR", "[\\+\\-\\*\\/]");
g.skipWhitespace = true; // Use the built-in fast whitespace skipper

// Rules
g.group("Value", g.symbols.NUMBER, g.symbols.VAR);
g.rule("Suffix", g.symbols.OPERATOR._as("op"), g.symbols.Value._as("val"));
g.rule("Expr", g.symbols.Value._as("left"), g.symbols.Suffix.zeroOrMore()._as("rights"));

g.axiom = g.symbols.Expr;

// 2. Parse a string
const result = g.parseString("42 + x");

if (result.isFailure()) {
    console.error(result.describe());
} else {
    console.log("Parsing successful!");
    
    // 3. Process the AST
    class ExprProcessor extends Processor {
        onNUMBER(match: Match) {
            return parseInt(match.value!, 10);
        }
        
        onVAR(match: Match) {
            return match.value;
        }
        
        onExpr(left: any, rights: any[]) {
            let res = left;
            for (const r of rights) {
                res = { op: r.op, left: res, right: r.val };
            }
            return res;
        }
        
        onSuffix(op: any, val: any) {
            return { op: op.value, val };
        }
    }
    
    // Initialize an Eager processor that traverses the AST bottom-up
    const processor = new ExprProcessor(g).asEager();
    const ast = processor.process(result.match!);
    
    console.log(JSON.stringify(ast, null, 2));
}
```