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

bool Iterator_hasMore( Iterator* this ) {
	return this->status != STATUS_ENDED;
}

size_t Iterator_remaining( Iterator* this ) {
	return this->available - (this->current - this->buffer);
}

bool Iterator_moveTo ( Iterator* this, size_t offset ) {
	return this->move(this, offset - this->offset );
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

bool Match_isSuccess(Match* this) {
	return (this != NULL && this != FAILURE && this->status == STATUS_MATCHED);
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

Match* ParsingElement_process( ParsingElement* this, Match* match ) {
	return match;
}

ParsingElement* ParsingElement_name( ParsingElement* this, const char* name ){
	this->name = name;
	return this;
}

// ----------------------------------------------------------------------------
//
// REFERENCE
//
// ----------------------------------------------------------------------------


bool Reference_Is(void *this) {
	return this!=NULL && ((Reference*)this)->type == Reference_T;
}

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
	this->cardinality = CARDINALITY_SINGLE;
	this->name        = "_";
	this->element     = NULL;
	this->next        = NULL;
	return this;
}

Reference* Reference_cardinality(Reference* this, char cardinality) {
	assert(this!=NULL);
	this->cardinality = cardinality;
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
				// If it's the first match and we're in a SINGLE reference
				// we force has_more to FALSE and exit the loop.
				result = match;
				head   = result;
				if (this->cardinality == CARDINALITY_SINGLE ) {
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
		case CARDINALITY_SINGLE:
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
	if ( regcomp( &(config->regex), expr, REG_EXTENDED) == 0) {
		this->config = config;
		return this;
	} else {
		ERROR("Cannot compile POSIX regex: %s", expr);
		__DEALLOC(config);
		ParsingElement_destroy(this);
		return NULL;
	}
}

// TODO: Implement Token_destroy and regfree

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
	// We get the current parsing context and make sure we have
	// at least TOKEN_MATCH_RANGE characters available (or the EOF). The
	// limitation here is that we don't necessarily want ot load the whole
	// file in memory, but could do it 1MB/time for instance.

	// NOTE: This means we need to pass the context
	//
	// Context_preload(context, TOKEN_MATCH_RANGE);

	// We need at least one more match than what we're requesting
	regmatch_t matches[2];
	const regex_t* regex  = & (((Token*)this->config)->regex);
	regexec(regex, context->iterator->buffer, 1, matches, 0);
	DEBUG("Buffer length: %zd: %s", strlen(context->iterator->buffer), context->iterator->buffer);
	if (matches[0].rm_so != -1) {
		DEBUG("Matched %s %d-%d", this->name, matches[0].rm_so, matches[1].rm_eo);
		return Match_Empty();
	} else {
		DEBUG("Failed %s", this->name);
		return FAILURE;
	}
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

int main (int argc, char* argv[]) {

	// We defined the grammar
	Grammar* g                 = Grammar_new();

	// ParsingElement* s_NUMBER   = NAME("NUMBER",   Token_new("^([0-9]+)"));
	// ParsingElement* s_VARIABLE = NAME("VARIABLE", Token_new("^([A-Z]+)"));
	// ParsingElement* s_OP       = NAME("OP",       Token_new("^\\-|\\+|\\*"));
	// ParsingElement* s_SPACES   = NAME("SPACES",   Token_new("^([ ]+)"));
	ParsingElement* s_NUMBER   = NAME("NUMBER",   Word_new("NUM"));
	ParsingElement* s_VARIABLE = NAME("VARIABLE", Word_new("VAR"));
	ParsingElement* s_OP       = NAME("OP",       Word_new("OP"));
	ParsingElement* s_SPACES   = NAME("SPACES",   Word_new(" "));

	// FIXME: This is not very elegant, but I did not really find a better
	// way. I tried passing the elements as an array, but it doesn't really
	// work.
	//
	// Alternative:
	// GROUP(s_Value) ONE(s_NUMBER) MANY(s_VARIABLE) END_GROUP
	//
	//
	// What we should aim:
	//
	// SYMBOL(Value, GROUP( s_NUMBER,      s_VARIABLE ));
	// SYMBOL(Value, RULE ( s_NUMBER, MANY(s_VARIABLE) ));

	ParsingElement* s_Value    = NAME("Value", Group_new((Reference*[3]){
		ONE(s_NUMBER),
		ONE(s_VARIABLE),
		NULL
	}));

	ParsingElement* s_Suffix   = NAME("Suffix", Rule_new ((Reference*[3]){
		ONE(s_OP),
		ONE(s_Value),
		NULL
	}));

	ParsingElement* s_Expr    = NAME("Expr", Rule_new (NULL));
		ParsingElement_add( s_Expr, ONE  (s_Value)  );
		ParsingElement_add( s_Expr, MANY (s_Suffix) );

	g->axiom = s_Expr;
	g->skip  = s_SPACES;

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
