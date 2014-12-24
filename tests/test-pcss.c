#include "../src/parsing.h"

int main (void) {
	// We define the grammar
	Grammar* g                 = Grammar_new();

	// ========================================================================
	// TOKENS
	// ========================================================================

	SYMBOL (SPACES,            TOKEN("[ ]+"))
	SYMBOL (TABS,              TOKEN("\\t*"))
	SYMBOL (COMMENT,           TOKEN("[ \\t]*//[^\\n]*"))
	SYMBOL (EOL,               TOKEN("[ ]*\\n(\\s*\\n)*"))
	SYMBOL (NUMBER,            TOKEN("-?(0x)?[0-9]+(\\.[0-9]+)?"))
	SYMBOL (ATTRIBUTE,         TOKEN("[a-zA-Z\\-_][a-zA-Z0-9\\-_]*"))
	SYMBOL (ATTRIBUTE_VALUE,   TOKEN("\"[^\"]*\"|'[^']*'|[^,\\]]+"))
	SYMBOL (SELECTOR_SUFFIX,   TOKEN("\\:[\\-a-z][a-z0-9\\-]*(\\([0-9]+\\))?"))
	SYMBOL (SELECTION_OPERATOR,TOKEN( "\\>|[ ]+"))
	SYMBOL (INCLUDE,           WORD( "%include"))
	SYMBOL (COLON,             WORD(":"))
	SYMBOL (DOT,               WORD("."))
	SYMBOL (LP,                WORD("("))
	SYMBOL (IMPORTANT,         WORD("!important"))
	SYMBOL (RP,                WORD(")"))
	SYMBOL (SELF,              WORD("&"))
	SYMBOL (COMMA,             WORD(","))
	SYMBOL (EQUAL,             WORD("="))
	SYMBOL (LSBRACKET,         WORD("["))
	SYMBOL (RSBRACKET,         WORD("]"))

	SYMBOL (PATH,              TOKEN("\"[^\"]+\"|'[^']'|[^\\s\\n]+"))
	SYMBOL (PERCENTAGE,        TOKEN("\\d+(\\.\\d+)?%"))
	SYMBOL (STRING_SQ,         TOKEN("'((\\\\'|[^'\\n])*)'"))
	SYMBOL (STRING_DQ,         TOKEN("\"((\\\\\"|[^\"\\n])*)\""))
	SYMBOL (STRING_UQ,         TOKEN("[^\\s\\n\\*;]+"))
	SYMBOL (INFIX_OPERATOR,    TOKEN("[\\-\\+\\*\\/]"))

	SYMBOL (NODE,              TOKEN("\\*|([a-zA-Z][a-zA-Z0-9\\-]*)"))
	SYMBOL (NODE_CLASS,        TOKEN("\\.[a-zA-Z][a-zA-Z0-9\\-]*"))
	SYMBOL (NODE_ID,           TOKEN("#[a-zA-Z][a-zA-Z0-9\\-]*"))

	SYMBOL (UNIT,              TOKEN("em|ex|px|cm|mm|in|pt|pc|ch|rem|vh|vmin|vmax|s|deg|rad|grad|ms|Hz|kHz|%"))
	// FIXME: Should be the same token
	SYMBOL (VARIABLE_NAME,     TOKEN("[\\w_][\\w\\d_]*"))
	SYMBOL (METHOD_NAME,       TOKEN("[\\w_][\\w\\d_]*"))
	SYMBOL (MACRO_NAME,        TOKEN("[\\w_][\\w\\d_]*"))
	SYMBOL (REFERENCE,         TOKEN("\\$([\\w_][\\w\\d_]*)"))
	SYMBOL (COLOR_HEX,         TOKEN("#([A-Fa-f0-9][A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?([A-Fa-f0-9][A-Fa-f0-9])?)"))
	SYMBOL (COLOR_RGB,         TOKEN("rgba?\\((\\s*\\d+\\s*,\\s*\\d+\\s*,\\s*\\d+\\s*(,\\s*\\d+(\\.\\d+)?\\s*)?)\\)"))
	SYMBOL (CSS_PROPERTY,      TOKEN("[a-z][a-z0-9\\-]*"))
	SYMBOL (SPECIAL_NAME,      TOKEN("@[A-Za-z][A-Za-z0-9_\\-]*"))
	SYMBOL (SPECIAL_FILTER,    TOKEN("\\[[^\\]]+\\]"))

	// ========================================================================
	// INDENTATION
	// ========================================================================

	SYMBOL (Indent,           PROCEDURE (Utilities_indent))
	SYMBOL (Dedent,           PROCEDURE (Utilities_dedent))
	SYMBOL (CheckIndent,      RULE      ( _AS(_S(TABS),"tabs"), ONE(CONDITION(Utilites_checkIndent) )))
	SYMBOL (Attribute,        RULE      (
		_AS( _S(ATTRIBUTE), "name"), _AS( OPTIONAL( RULE( _S(EQUAL), _S(ATTRIBUTE_VALUE)) ), "value")
	));

	SYMBOL (Attributes,       RULE      (
		_S(LSBRACKET),
		_AS( _S(Attribute), "head"),
		_AS( OPTIONAL(RULE( _S(COMMA), _S(Attribute))), "tail"),
		_S(RSBRACKET)
	));

	SYMBOL (Selector,         RULE       (
		_AS (OPTIONAL( GROUP( _S(SELF), _S(NODE) )), "scope"),
		_AS (_O      (NODE_ID),                     "nid"),
		_AS (_MO     (NODE_CLASS),                  "nclass"),
		_AS (_O      (Attributes),                  "attributes"),
		_AS (_MO     (SELECTOR_SUFFIX),             "suffix")
	));

	SYMBOL  (SelectorNarrower, RULE         (
		_AS(_S(SELECTION_OPERATOR), "op"),
		_AS(_S(Selector),           "sel")
	));

	SYMBOL  (Selection,        RULE       (
		_AS( _S (Selector),         "head"),
		_AS( _MO(SelectorNarrower), "tail")
	));

	SYMBOL (SelectionList,    RULE       (
		_AS(_S(Selection), "head"),
		_AS(MANY_OPTIONAL(RULE(_S(COMMA), _S(Selection))), "tail")
	));

	// ========================================================================
	// VALUES & EXPRESSIONS
	// ========================================================================

	SYMBOL      (Suffixes, GROUP(NULL))
	SYMBOL      (Number,           RULE(
		_AS( _S(NUMBER), "value"),
		_AS( _O(UNIT),   "unit")
	))
	SYMBOL     (String,           GROUP(_S(STRING_UQ),      _S(STRING_SQ), _S(STRING_DQ)))
	SYMBOL     (Value,            GROUP(_S(Number),         _S(COLOR_HEX), _S(COLOR_RGB), _S(REFERENCE), _S(String)))
	SYMBOL     (Parameters,       RULE (_S(VARIABLE_NAME), MANY_OPTIONAL(RULE(_S(COMMA), _S(VARIABLE_NAME)))))
	SYMBOL     (Arguments,        RULE (_S(Value),         MANY_OPTIONAL(RULE(_S(COMMA), _S(Value)))))

	SYMBOL     (Expression, RULE(NULL))

	//  NOTE: We use Prefix and Suffix to avoid recursion, which creates a lot
	//  of problems with parsing expression grammars
	// SYMBOL     (Prefix, _S(Expression))
	SYMBOL     (Prefix, GROUP(
		_S(Value),
		ONE(RULE(_S(LP), _S(Expression), _S(RP)))
	))

	// FIXME: Add a macro to support that
	ParsingElement_add(s_Expression, ONE(RULE( _S(Prefix), _MO(Suffixes))));

	SYMBOL     (Invocation,     RULE(
		_AS( OPTIONAL(RULE( _S(DOT), _S(METHOD_NAME))), "method"),
		_S(LP), _AS(_O(Arguments), "arguments"), _S(RP)
	));
	SYMBOL     (InfixOperation, RULE(_S(INFIX_OPERATOR), _S(Expression)))

	// FIXME: Add a macro to support that
	ParsingElement_add(s_Suffixes, ONE(GROUP( _S(InfixOperation), _S(Invocation))));

	// ========================================================================
	// LINES (BODY)
	// ========================================================================

	SYMBOL     (Comment,          RULE(_M(COMMENT), _S(EOL)))
	SYMBOL     (Include,          RULE(_S(INCLUDE), _S(PATH), _S(EOL)))
	SYMBOL     (Declaration,      RULE(
		_AS(_S(VARIABLE_NAME), "name"),
		_S(EQUAL),
		_AS(_S(Expression), "value"), _S(EOL)
	))

	// ========================================================================
	// OPERATIONS
	// ========================================================================

	SYMBOL     (Assignment,       RULE(
		_AS(_S(CSS_PROPERTY), "name"),
		_S(COLON),
		_AS(_M(Expression), "values"),
		_AS(_O(IMPORTANT), "important")
	))
	SYMBOL     (MacroInvocation,  RULE(_S(MACRO_NAME),   _S(LP), _O(Arguments), _S(RP)))

	// ========================================================================
	// BLOCK STRUCTURE
	// ========================================================================

	SYMBOL  (Code, GROUP(NULL))

	// FIXME: Manage memoization here
	// NOTE: If would be good to sort this out and allow memoization for some
	// of the failures. A good idea would be to append the indentation value to
	// the caching key.
	// .processMemoizationKey(lambda _,c:_ + ":" + c.getVariables().get("requiredIndent", 0))
	SYMBOL    (Statement,     RULE(
		_S(CheckIndent), ONE(GROUP(_S(Assignment), _S(MacroInvocation), _S(COMMENT))), _S(EOL)
	))

	SYMBOL    (Block,         RULE(
		_S(CheckIndent), _AS(GROUP(_S(PERCENTAGE), _S(SelectionList)), "selector"), _O(COLON), _S(EOL),
		_S(Indent), _AS(_MO(Code), "code"), _S(Dedent)
	))
	ParsingElement_add(s_Code, ONE(GROUP(_S(Block), _S(Statement))));

	SYMBOL    (SpecialDeclaration,   RULE(
		_S(CheckIndent), _S(SPECIAL_NAME), _O(SPECIAL_FILTER), _O(Parameters), _S(COLON)
	))
	SYMBOL    (SpecialBlock,         RULE(
		_S(CheckIndent), _S(SpecialDeclaration), _O(EOL), _S(Indent), _MO(Code), _S(Dedent)
	))

	// ========================================================================
	// AXIOM
	// ========================================================================

	SYMBOL     (Source,  GROUP(MANY_OPTIONAL(
		GROUP( _S(Comment), _S(Block), _S(SpecialBlock), _S(Declaration), _S(Include))
	)))

	g->axiom = s_Source;
	g->skip  = s_SPACES;

	// ========================================================================
	// MAIN
	// ========================================================================

	Iterator* iterator = Iterator_new();
	const char* path = "tests/test-pcss.pcss";

	DEBUG("Opening file: %s", path)
	if (!Iterator_open(iterator, path)) {
		ERROR("Cannot open file: %s", path);
	} else {
		ParsingResult* r = Grammar_parseFromIterator(g, iterator);
		// Below is a simple test on how to iterate on the file
		// int count = 0;
		// while (FileInput_next(i)) {
		// 	DEBUG("Read %c at %zd/%zd\n", *i->current, i->offset, i->available);
		// 	count += 1;
		// }
		printf("Status %c, read %zd/%zd bytes\n", r->status, r->context->iterator->offset, r->context->iterator->available);
	}
	printf ("[OK]");
	return 1;
}
