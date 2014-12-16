// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 14-Dec-2014
// ----------------------------------------------------------------------------

#include "parsing.h"
#include "oo.h"

// SEE: https://en.wikipedia.org/wiki/C_data_types
// SEE: http://stackoverflow.com/questions/18329532/pcre-is-not-matching-utf8-characters
// HASH: search.h, hcreate, hsearch, etc

// ----------------------------------------------------------------------------
//
// ITERATOR
//
// ----------------------------------------------------------------------------

Iterator* Iterator_Open(const char* path) {
	NEW(Iterator,result);
	if (Iterator_open(result, path)) {
		return result;
	} else {
		Iterator_destroy(result);
		return NULL;
	}
}

Iterator* Iterator_new( void ) {
	__ALLOC(Iterator, this);
	this->status        = STATUS_INIT;
	this->separator     = EOL;
	this->buffer        = NULL;
	this->current       = NULL;
	this->offset        = 0;
	this->lines         = 0;
	this->available     = 0;
	this->length        = 0;
	this->input         = NULL;
	this->move          = NULL;
	return this;
}

bool Iterator_open( Iterator* this, const char *path ) {
	NEW(FileInput,input, path);
	assert(this->status == STATUS_INIT);
	if (input!=NULL) {
		this->input  = (void*)input;
		this->status = STATUS_PROCESSING;
		this->offset = 0;
		// We allocate a buffer that's twice the size of ITERATOR_BUFFER_AHEAD
		// so that we ensure that the current position always has ITERATOR_BUFFER_AHEAD
		// bytes ahead (if the input source has the data)
		assert(this->buffer == NULL);
		this->length  = sizeof(iterated_t) * ITERATOR_BUFFER_AHEAD * 2;
		this->buffer  = calloc(this->length + 1, 1);
		this->current = (iterated_t*)this->buffer;
		// We make sure we have a trailing \0 sign to stop any string parsing
		// function to go any further.
		((char*)this->buffer)[this->length] = '\0';
		assert(strlen(((char*)this->buffer)) == 0);
		FileInput_preload(this);
		DEBUG("Iterator_open: strlen(buffer)=%zd/%zd", strlen((char*)this->buffer), this->length);
		this->move   = FileInput_move;
		ENSURE(input->file) {};
		return TRUE;
	} else {
		return FALSE;
	}
}

void Iterator_destroy( Iterator* this ) {
	// TODO: Take care of input
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// FILE INPUT
//
// ----------------------------------------------------------------------------

FileInput* FileInput_new(const char* path ) {
	__ALLOC(FileInput, this);
	assert(this != NULL);
	// We open the file
	this->file = fopen(path, "r");
	if (this->file==NULL) {
		ERROR("Cannot open file: %s", path);
		__DEALLOC(this);
		return NULL;
	} else {
		return this;
	}
}

void FileInput_destroy(FileInput* this) {
	if (this->file != NULL) { fclose(this->file);   }
}

size_t FileInput_preload( Iterator* this ) {
	// We want to know if there is at one more element
	// in the file input.
	FileInput*   input         = (FileInput*)this->input;
	size_t       read          = this->current   - this->buffer;
	size_t       left          = this->available - read;
	//DEBUG("FileInput_preload: %zd read, %zd available / %zd length [%c]", read, this->available, this->length, this->status);
	assert (read >= 0);
	assert (left >= 0);
	assert (left  < this->length);
	// Do we have less left than the buffer ahead?
	if ( left < ITERATOR_BUFFER_AHEAD && this->status != STATUS_INPUT_ENDED) {
		// We move buffer[current:] to the begining of the buffer
		// FIXME: We should make sure we don't call preload each time
		// memmove((void*)this->buffer, (void*)this->current, left);
		// We realloc the memory to make sure we
		size_t delta  = this->current - this->buffer;
		this->length += this->length;
		this->buffer  = realloc((void*)this->buffer, this->length + 1);
		this->current = this->buffer + delta;
		this->buffer[this->length] = '\0';
		// We want to read as much as possible so that we fill the buffer
		size_t to_read        = this->length - left;
		size_t read           = fread((void*)this->buffer + left, sizeof(char), to_read, input->file);
		DEBUG("FileInput_preload: trying to get %zd bytes from input, got %zd", to_read, read);
		left = this->available= left + read;
		if (read == 0) {
			DEBUG("FileInput_preload: End of file reached with %zd bytes available", this->available);
			this->status = STATUS_INPUT_ENDED;
		}
	}
	return left;
}

bool FileInput_move   ( Iterator* this, size_t n ) {
	if ( n == 0) {
		// We're not moving position
		return TRUE;
	} else if ( n >= 0 ) {
		// We're moving forward, so we want to know if there is at one more element
		// in the file input.
		size_t left = FileInput_preload(this);
		if (left > 0) {
			size_t c = n > left ? left : n;
			// We have enough space left in the buffer to read at least one character.
			// We increase the head, copy
			while (c > 0) {
				this->current++;
				this->offset++;
				if (*(this->current) == this->separator) {this->lines++;}
				c--;
			}
			DEBUG("FileInput_move: +%zd/%zd left, current offset %zd", n, left, this->offset);
			if (n>left) {
				this->status == STATUS_INPUT_ENDED;
				return FALSE;
			} else {
				return TRUE;
			}
		} else {
			DEBUG("FileInput_move: end of input stream reach at %zd", this->offset);
			assert (this->status == STATUS_INPUT_ENDED || this->status == STATUS_ENDED);
			this->status = STATUS_ENDED;
			return FALSE;
		}
	} else {
		// The assert below is temporary, once we figure out when to free the input data
		// that we don't need anymore this would work.
		ASSERT(this->length > this->offset, "FileInput_move: offset is greater than length (%zd > %zd)", this->offset, this->length);
		// We make sure that `n` is not bigger than the length of the available buffer
		n = this->length + n < 0 ? 0 - this->length : n;
		this->current = (((char*)this->current) + n);
		this->offset += n;
		this->status  = STATUS_PROCESSING;
		return TRUE;
	}
}


// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

Grammar* Grammar_new() {
	__ALLOC(Grammar, this);
	this->axiom     = NULL;
	this->skip      = NULL;
	return this;
}

// ----------------------------------------------------------------------------
//
// MATCH
//
// ----------------------------------------------------------------------------

Match* Match_Empty() {
	NEW(Match,this);
	this->status = STATUS_MATCHED;
	return this;
}


Match* Match_Success(size_t length) {
	NEW(Match,this);
	this->status = STATUS_MATCHED;
	this->length = length;
	return this;
}

Match* Match_new() {
	__ALLOC(Match,this);
	this->status    = STATUS_INIT;
	this->length    = 0;
	this->data      = NULL;
	this->next      = NULL;
	return this;
}

void Match_destroy(Match* this) {
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// PARSING ELEMENT
//
// ----------------------------------------------------------------------------

bool ParsingElement_Is(void *this) {
	return this!=NULL && ((ParsingElement*)this)->type == ParsingElement_T;
}

ParsingElement* ParsingElement_new(Reference* children[]) {
	__ALLOC(ParsingElement, this);
	this->type      = ParsingElement_T;
	this->id        = 0;
	this->name      = "_";
	this->config    = NULL;
	this->children  = NULL;
	this->recognize = NULL;
	this->process   = NULL;
	if (children != NULL ) {
		Reference* r = Reference_Ensure(*children);
		DEBUG("Array length: %zd", sizeof(children))
		while ( r != NULL ) {
			DEBUG("Adding child: %s", r->element->name)
			// FIXME: Make sure how memory is managed here
			ParsingElement_add(this, r);
			r = *(++children);
		}
	}
	return this;
}

void ParsingElement_destroy(ParsingElement* this) {
	Reference* child = this->children;
	while (child != NULL) {
		Reference* next = child->next;
		__DEALLOC(child);
		child = next;
	}
	__DEALLOC(this);
}

ParsingElement* ParsingElement_add(ParsingElement *this, Reference *child) {
	assert(child->next == NULL);
	assert(child->element->recognize!=NULL);
	if (this->children) {
		// If there are children, we skip until the end and add it
		Reference* ref = this->children;
		while (ref->next != NULL) {ref = ref->next;}
		ref->next = child;
	} else {
		// If there are no children, we set it as the first
		this->children = child;
	}
	return this;
}

// ----------------------------------------------------------------------------
//
// REFERENCE
//
// ----------------------------------------------------------------------------

Reference* Reference_Ensure(void* elementOrReference) {
	void * element = elementOrReference;
	assert(element!=NULL);
	assert(Reference_Is(element) || ParsingElement_Is(element));
	return ParsingElement_Is(element) ? Reference_New(element) : element;
}

Reference* Reference_New(ParsingElement* element){
	NEW(Reference, this);
	assert(element!=NULL);
	this->element = element;
	ASSERT(element->recognize, "Reference_New: Element %s has no recognize callback", element->name);
	return this;
}

Reference* Reference_new() {
	__ALLOC(Reference, this);
	this->type        = Reference_T;
	this->cardinality = CARDINALITY_ONE;
	this->name        = "_";
	this->element     = NULL;
	this->next        = NULL;
	return this;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {
	assert(this->element != NULL);
	Match* result = FAILURE;
	Match* head;
	Match* match;
	int    count    = 0;
	while (Iterator_hasMore(context->iterator)) {
		ASSERT(this->element->recognize, "Reference_recognize: Element %s has no recognize callback", this->element->name);
		// We ask the element to recognize the current iterator's position
		match = this->element->recognize(this->element, context);
		if (Match_isSuccess(match)) {
			DEBUG("Reference_recognize: Matched %s at %zd", this->element->name, context->iterator->offset);
			if (count == 0) {
				// If it's the first match and we're in a ONE reference
				// we force has_more to FALSE and exit the loop.
				result = match;
				head   = result;
				if (this->cardinality == CARDINALITY_ONE ) {
					break;
				}
			} else {
				// If we're already had a match we append the head and update
				// the head to be the current match
				head = head->next = match;
			}
			count++;
		} else {
			break;
		}
	}
	// Depending on the cardinality, we might return FAILURE, or not
	switch (this->cardinality) {
		case CARDINALITY_ONE:
			// For single, we return the match as-is
			return result;
		case CARDINALITY_OPTIONAL:
			// For optional, we return the an empty match if
			// the match fails.
			return result == FAILURE ? Match_Empty() : result;
		case CARDINALITY_MANY:
			return count > 0 ? result : FAILURE;
		case CARDINALITY_MANY_OPTIONAL:
			return count > 0 ? result : Match_Empty();
		default:
			// Unsuported cardinality
			ERROR("Unsupported cardinality %c", this->cardinality);
			return FAILURE;
	}
}

// ----------------------------------------------------------------------------
//
// WORD
//
// ----------------------------------------------------------------------------

ParsingElement* Word_new(const char* word) {
	__ALLOC(Word, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->recognize      = Word_recognize;
	assert(word != NULL);
	config->word         = word;
	config->length       = strlen(word);
	assert(config->length>0);
	this->config         = config;
	return this;
}

// TODO: Implement Word_destroy and regfree

Match* Word_recognize(ParsingElement* this, ParsingContext* context) {
	Word* config = ((Word*)this->config);
	if (strncmp(config->word, context->iterator->current, config->length) == 0) {
		// NOTE: You can see here that the word actually consumes input
		// and moves the iterator.
		context->iterator->move(context->iterator, config->length);
		return Match_Success(config->length);
	} else {
		return FAILURE;
	}
}

// ----------------------------------------------------------------------------
//
// TOKEN
//
// ----------------------------------------------------------------------------

ParsingElement* Token_new(const char* expr) {
	__ALLOC(Token, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->recognize      = Token_recognize;
	const char* pcre_error;
	int         pcre_error_offset = -1;
	config->expr   = expr;
	config->regexp = pcre_compile(expr, PCRE_UTF8, &pcre_error, &pcre_error_offset, NULL);
	if (pcre_error != NULL) {
		ERROR("Token: cannot compile regular expression `%s` at %d: %s", expr, pcre_error_offset, pcre_error);
		__DEALLOC(config);
		__DEALLOC(this);
		return NULL;
	}
	config->extra = pcre_study(config->regexp, 0, &pcre_error);
	if (pcre_error != NULL) {
		ERROR("Token: cannot optimize regular expression `%s` at %d: %s", expr, pcre_error_offset, pcre_error);
		__DEALLOC(config);
		__DEALLOC(this);
		return NULL;
	}
	this->config = config;
	return this;
}

void Token_destroy(ParsingElement* this) {
	Token* config = (Token*)this->config;
	if (config != NULL) {
		// FIXME: Not sure how to free a regexp
		if (config->regexp != NULL) {}
		if (config->extra  != NULL) {pcre_free_study(config->extra);}
		__DEALLOC(config);
	}
	__DEALLOC(this);
}

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
	assert(this->config);
	if(this->config == NULL) {return FAILURE;}
	Token* config     = (Token*)this->config;
	// NOTE: This has to be a multiple of 3, according to `man pcre_exec`
	int vector_length = 30;
	int vector[vector_length];
	int r = pcre_exec(
		config->regexp, config->extra,     // Regex
		(char*)context->iterator->current, // Line
		context->iterator->available,      // Available data
		0,                                 // Offset
		PCRE_ANCHORED,                     // OPTIONS -- we do not skip position
		vector,                            // Vector of matching offsets
		vector_length);                    // Number of elements in the vector
	Match* result = NULL;
	if (r <= 0) {
		// DEBUG("Token: %s FAILED on %s", config->expr, context->iterator->buffer);
		switch(r) {
			case PCRE_ERROR_NOMATCH      : result = FAILURE;                                                        break;
			case PCRE_ERROR_NULL         : ERROR("Token:%s Something was null", config->expr);                      break;
			case PCRE_ERROR_BADOPTION    : ERROR("Token:%s A bad option was passed", config->expr);                 break;
			case PCRE_ERROR_BADMAGIC     : ERROR("Token:%s Magic number bad (compiled re corrupt?)", config->expr); break;
			case PCRE_ERROR_UNKNOWN_NODE : ERROR("Token:%s Something kooky in the compiled re", config->expr);      break;
			case PCRE_ERROR_NOMEMORY     : ERROR("Token:%s Ran out of memory", config->expr);                       break;
			default                      : ERROR("Token:%s Unknown error", config->expr);                           break;
		};
	} else {
		// DEBUG("Token: %s matched %d on %s", config->expr, r, context->iterator->buffer);
		if(r == 0) {
			ERROR("Token: %s many substrings matched\n", config->expr);
			// Set rc to the max number of substring matches possible.
			// FIMXE: Not sure why we're doing 3 here, but it's what is
			// state in the doc
			// `ovecsize     Number of elements in the vector (a multiple of 3)`
			// in `man pcre_exec`.
			r = vector_length / 3;
		}
		result           = Match_new();
		result->length   = vector[1];
		context->iterator->move(context->iterator,result->length);

		// TokenMatch* data = _ALLOC(TokenMatch);
		// data->groups     = r;
		// data->vector     = malloc(r * 3);
		// memcpy(data->vector, &vector, r * 3);
	}
	return result;
}


// FIXME: Not sure what to do exactly here, but we'd like to retrieve the group
void* Token_Group(ParsingElement* this, Match* match) {
	if (!Match_isSuccess(match)) {return NULL;}
	//	// PCRE contains a handy function to do the above for you:
	//	for( int j=0; j<r; j++ ) {
	//		const char *match;
	//		pcre_get_substring(line, vector, r, j, &match);
	//		printf("Match(%2d/%2d): (%2d,%2d): '%s'\n", j, r-1, vector[j*2], vector[j*2+1], match);
	//		pcre_free_substring(match);
	//	}
}

// ----------------------------------------------------------------------------
//
// GROUP
//
// ----------------------------------------------------------------------------

ParsingElement* Group_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->recognize = Group_recognize;
	return this;
}

Match* Group_recognize(ParsingElement* this, ParsingContext* context){
	Reference* child = this->children;
	Match*     match;
	size_t     offset = context->iterator->offset;
	while (child != NULL ) {
		match = Reference_recognize(child, context);
		if (Match_isSuccess(match)) {
			// The first succeding child wins
			return match;
		} else {
			// Otherwise we skip to the next child
			child = child->next;
		}
	}
	// If no child has succeeded, the whole group fails
	Iterator_moveTo(context->iterator, offset);
	return FAILURE;
}

// ----------------------------------------------------------------------------
//
// RULE
//
// ----------------------------------------------------------------------------

ParsingElement* Rule_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->recognize      = Rule_recognize;
	return this;
}

Match* Rule_recognize (ParsingElement* this, ParsingContext* context){
	Reference* child  = this->children;
	Match*     result = NULL;
	Match*     last   = NULL;
	int        step   = 0;
	size_t     offset = context->iterator->offset;
	// We don't need to care wether the parsing context has more
	// data, the Reference_recognize will take care of it.
	while (child != NULL) {
		Match* match = Reference_recognize(child, context);
		DEBUG("Rule_recognize:%s[%d]=%s matched:%d at %zd", this->name, step, child->element->name, Match_isSuccess(match), context->iterator->offset);
		if (!Match_isSuccess(match)) {
			ParsingElement* skip = context->grammar->skip;
			Match* skip_match    = skip->recognize(skip, context);
			while (Match_isSuccess(skip_match)){skip_match = skip->recognize(skip, context);}
			match = Reference_recognize(child, context);
			if (!Match_isSuccess(match)) {
				break;
			}
		}
		if (last == NULL) {
			last = result = match;
		} else {
			last = last->next = match;
		}
		child = child->next;
		step++;
	}
	if (!Match_isSuccess(result)) {
		Iterator_moveTo(context->iterator, offset);
	}
	return result;
}

// ----------------------------------------------------------------------------
//
// PROCEDURE
//
// ----------------------------------------------------------------------------

ParsingElement* Procedure_new(ProcedureCallback c) {
	ParsingElement* this = ParsingElement_new(NULL);
	this->config = c;
	return this;
}

Match*  Procedure_recognize(ParsingElement* this, ParsingContext* context) {
	if (this->config != NULL) {
		((ProcedureCallback)(this->config))(this, context);
	}
	return Match_Success(0);
}

// ----------------------------------------------------------------------------
//
// CONDITION
//
// ----------------------------------------------------------------------------

ParsingElement* Condition_new(ConditionCallback c) {
	ParsingElement* this = ParsingElement_new(NULL);
	this->config = c;
	return this;
}

Match*  Condition_recognize(ParsingElement* this, ParsingContext* context) {
	if (this->config != NULL) {
		return ((ConditionCallback)this->config)(this, context);
	} else {
		return Match_Success(0);
	}
}



// ----------------------------------------------------------------------------
//
// PARSING STEP
//
// ----------------------------------------------------------------------------

ParsingStep* ParsingStep_new( ParsingElement* element ) {
	__ALLOC(ParsingStep, this);
	this->element   = element;
	this->step      = 0;
	this->iteration = 0;
	this->status    = STATUS_INIT;
	this->match     = (Match*)NULL;
	this->previous  = NULL;
	return this;
}

void ParsingStep_destroy( ParsingStep* this ) {
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// PARSING OFFSET
//
// ----------------------------------------------------------------------------


ParsingOffset* ParsingOffset_new( size_t offset ) {
	__ALLOC(ParsingOffset, this);
	this->offset = offset;
	this->last   = (ParsingStep*)NULL;
	this->next   = (ParsingOffset*)NULL;
	return this;
}

void ParsingOffset_destroy( ParsingOffset* this ) {
	ParsingStep* step     = this->last;
	ParsingStep* previous = NULL;
	while (step != NULL) {
		previous   = step->previous;
		ParsingStep_destroy(step);
		step       = previous;
	}
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

Match* Grammar_parseFromIterator( Grammar* this, Iterator* iterator ) {
	ParsingOffset* offset  = ParsingOffset_new(iterator->offset);
	ParsingContext context = (ParsingContext){
		.grammar  = this,
		.iterator = iterator,
		.offsets  = offset,
		.offsets  = offset,
	};
	assert(this->axiom != NULL);
	Match* match = this->axiom->recognize(this->axiom, &context);
	if (match != FAILURE) {
		if (Iterator_hasMore(context.iterator)) {
			LOG("Partial success, parsed %zd bytes, %zd remaining", context.iterator->offset, Iterator_remaining(context.iterator));
		} else {
			LOG("Succeeded, parsed %zd bytes", context.iterator->offset);
		}
	} else {
		LOG("Failed, parsed %zd bytes, %zd remaining", context.iterator->offset, Iterator_remaining(context.iterator))
	}
	return match;
}

//
// ----------------------------------------------------------------------------
//
// MAIN
//
// ----------------------------------------------------------------------------

void Utilities_indent( ParsingElement* this, ParsingContext* context ) {
	//int depth = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	//ParsingContext_setVariable("indent", depth + 1,     sizeof(int));
}

void Utilities_dedent( ParsingElement* this, ParsingContext* context ) {
	//int depth = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	//ParsingContext_setVariable("indent", depth - 1,     sizeof(int));
}

Match* Utilites_checkIndent( ParsingElement *this, ParsingContext* context ) {
	// Variable tabs = ParsingContext_getVariable("tabs", NULL, sizeof(int));
	// // TokenMatch_group(0)
	// int depth     = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	// if (depth != tabs_count) {
	// 	return FAILURE;
	// } else {
	// 	return Match_Success();
	// }
	return FAILURE;
}

int main (int argc, char* argv[]) {

	// We define the grammar
	Grammar* g                 = Grammar_new();

	// ========================================================================
	// TOKENS
	// ========================================================================

	SYMBOL (SPACES,            TOKEN("[ ]+"))
	SYMBOL (TABS,              TOKEN("\\t*"))
	SYMBOL (EMPTY_LINES,       TOKEN("([ \\t]*\\n)+"))
	SYMBOL (INDENT,            TOKEN("\\t+"))
	SYMBOL (COMMENT,           TOKEN("[ \\t]*//[^\n]*"))
	SYMBOL (EOL,               TOKEN("[ ]*\n(\\s*\n)*"))
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
	SYMBOL (TAB,               WORD("\t"))
	SYMBOL (EQUAL,             WORD("="))
	SYMBOL (LSBRACKET,         WORD("["))
	SYMBOL (RSBRACKET,         WORD("]"))

	SYMBOL (PATH,              TOKEN("\"[^\"]+\"|'[^']'|[^\\s\\n]+"))
	SYMBOL (PERCENTAGE,        TOKEN("\\d+(\\.\\d+)?%"))
	SYMBOL (STRING_SQ,         TOKEN("'((\\\\'|[^'\\n])*)'"))
	SYMBOL (STRING_DQ,         TOKEN("\"((\\\\\"|[^\"\\n])*)\""))
	SYMBOL (STRING_UQ,         TOKEN("[^\\s\n\\*;]+"))
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
	SYMBOL (COLOR_NAME,        TOKEN("[a-z][a-z0-9\\-]*"))
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

	SYMBOL      (Suffixes, NULL)
	SYMBOL      (Number,           RULE(
		_AS( _S(NUMBER), "value"),
		_AS( _O(UNIT),   "unit")
	))
	SYMBOL     (String,           GROUP(_S(STRING_UQ),      _S(STRING_SQ), _S(STRING_DQ)))
	SYMBOL     (Value,            GROUP(_S(Number),         _S(COLOR_HEX), _S(COLOR_RGB), _S(REFERENCE), _S(String)))
	SYMBOL     (Parameters,       RULE (_S(VARIABLE_NAME), MANY_OPTIONAL(RULE(_S(COMMA), _S(VARIABLE_NAME)))))
	SYMBOL     (Arguments,        RULE (_S(Value),         MANY_OPTIONAL(RULE(_S(COMMA), _S(Value)))))

	SYMBOL     (Expression, NULL)

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
	SYMBOL     (Declaration,      RULE(_AS(_S(VARIABLE_NAME), "name"), _S(EQUAL), _AS(_S(Expression), "value"), _S(EOL)))

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

	SYMBOL  (Code, NULL)

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

	SYMBOL     (Source,  GROUP(
		_S(Comment), _S(Block), _S(SpecialBlock), _S(Declaration), _S(Include)
	))

	g->axiom = s_Source;
	g->skip  = s_SPACES;

	// ========================================================================
	// MAIN
	// ========================================================================

	Iterator* iterator = Iterator_new();
	const char* path = "test.txt";

	DEBUG("Opening file: %s", path)
	if (!Iterator_open(iterator, path)) {
		ERROR("Cannot open file: %s", path);
	} else {
		Grammar_parseFromIterator(g, iterator);
		// Below is a simple test on how to iterate on the file
		// int count = 0;
		// while (FileInput_next(i)) {
		// 	DEBUG("Read %c at %zd/%zd\n", *i->current, i->offset, i->available);
		// 	count += 1;
		// }
		// printf("Read %d bytes\n", count);
	}
}

// EOF
