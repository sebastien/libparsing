// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 2014-12-12
// Last modification : 2017-01-13
// ----------------------------------------------------------------------------

#include "parsing.h"
#include "gc.h"
#include "oo.h"

#define MATCH_STATS(m) ParsingContext_registerMatch(context, (Element*)this, m)
#define ANONYMOUS      "unnamed"

// SEE: https://en.wikipedia.org/wiki/C_data_types
// SEE: http://stackoverflow.com/questions/18329532/pcre-is-not-matching-utf8-characters
// HASH: search.h, hcreate, hsearch, etc

char   EOL = '\n';

Match FAILURE_S = {
	.status = STATUS_FAILED,
	.length = 0,
	.data   = NULL,
	.next   = NULL    // NOTE: next should *always* be NULL for FAILURE
};

Match* FAILURE = &FAILURE_S;

// ----------------------------------------------------------------------------
//
// LOGGING
//
// ----------------------------------------------------------------------------

const char* EMPTY        = "";
const char* INDENT       = "                                                                                ";
#define     INDENT_WIDTH  2
#define     INDENT_MAX    40

#define     OUT_STEP(msg,...)          OUT_IF(context->grammar->isVerbose && !HAS_FLAG(context->flags, FLAG_SKIPPING), msg, __VA_ARGS__)
#define     OUT_STEP_IF(cond,msg,...)  OUT_IF(context->grammar->isVerbose && !HAS_FLAG(context->flags, FLAG_SKIPPING) && cond, msg, __VA_ARGS__)

// ----------------------------------------------------------------------------
//
// TOOLS
//
// ----------------------------------------------------------------------------

char* String_escape(const char* string) {
	const char* p = string;
	int   n = 0;
	int   l = 0;
	while (*p != '\0') {
		switch(*p) {
			case '\n':
			case '\t':
			case '\r':
			case '"':
				n++;
			default:
				l++;
		}
		p++;
	}
	char* res = malloc(l + n + 1);
	p = string;
	n = 0;
	l = 0;
	while (*p != '\0') {
		char c = *p;
		switch(c) {
			case '\n':
				res[l   + n++] = '\\';
				res[l++ + n]   = 'n';
				break;
			case '\t':
				res[l   + n++] = '\\';
				res[l++ + n]   = 't';
				break;
			case '\r':
				res[l   + n++] = '\\';
				res[l++ + n]   = 'r';
				break;
			case '"':
				res[l   + n++] = '\\';
				res[l++ + n]   = '"';
				break;
			default:
				res[l + n] = c;
				l++;
		}
		p++;
	}
	res[l + n] = '\0';
	return res;
}



// ----------------------------------------------------------------------------
//
// ITERATOR
//
// ----------------------------------------------------------------------------

Iterator* Iterator_Open(const char* path) {
	NEW(Iterator,result);
	result->freeBuffer = TRUE;
	if (Iterator_open(result, path)) {
		return result;
	} else {
		Iterator_free(result);
		return NULL;
	}
}

Iterator* Iterator_FromString(const char* text) {
	NEW(Iterator, this);
	if (this!=NULL) {
		this->buffer     = (char*)text;
		this->current    = (char*)text;
		this->capacity   = strlen(text);
		this->available  = this->capacity;
		this->move       = String_move;
	}
	return this;
}

Iterator* Iterator_new( void ) {
	__NEW(Iterator, this);
	this->status        = STATUS_INIT;
	this->separator     = EOL;
	this->buffer        = NULL;
	this->current       = NULL;
	this->offset        = 0;
	this->lines         = 0;
	this->available     = 0;
	this->capacity      = 0;
	this->input         = NULL;
	this->move          = NULL;
	this->freeBuffer    = FALSE;
	return this;
}

bool Iterator_open( Iterator* this, const char *path ) {
	NEW(FileInput, input, path);
	assert(this->status == STATUS_INIT);
	if (input!=NULL) {
		this->input  = (void*)input;
		this->status = STATUS_PROCESSING;
		this->offset = 0;
		// We allocate a buffer that's twice the size of ITERATOR_BUFFER_AHEAD
		// so that we ensure that the current position always has ITERATOR_BUFFER_AHEAD
		// bytes ahead (if the input source has the data)
		assert(this->buffer == NULL);
		// FIXME: Capacity should be in units, no?
		this->capacity = sizeof(char) * ITERATOR_BUFFER_AHEAD * 2;
		__ARRAY_NEW(new_buffer, char, this->capacity + 1)
		this->buffer   = new_buffer;
		assert(this->buffer != NULL);
		this->current = (char*)this->buffer;
		// We make sure we have a trailing \0 sign to stop any string parsing
		// function to go any further.
		((char*)this->buffer)[this->capacity] = '\0';
		assert(strlen(((char*)this->buffer)) == 0);
		FileInput_preload(this);
		DEBUG("Iterator_open: strlen(buffer)=%zu/%zu", strlen((char*)this->buffer), this->capacity);
		this->move   = FileInput_move;
		ENSURE(input->file);
		return TRUE;
	} else {
		return FALSE;
	}
}

bool Iterator_hasMore( Iterator* this ) {
	size_t remaining = Iterator_remaining(this);
	// DEBUG("Iterator_hasMore: %zu, offset=%zu available=%zu capacity=%zu ", remaining, this->offset, this->available, this->capacity)
	// NOTE: This used to be STATUS_ENDED, but I changed it to the actual.
	return remaining > 0;
}

size_t Iterator_remaining( Iterator* this ) {
	int buffer_offset = ((char*)this->current - this->buffer);
	// FIXME: Does not work if char is not the same as char
	int remaining = this->available - buffer_offset;
	assert(remaining >= 0);
	//DEBUG("Iterator_remaining: %d, offset=%zu available=%zu capacity=%zu", remaining, this->offset, this->available, this->capacity)
	return (size_t)remaining;
}

bool Iterator_moveTo ( Iterator* this, size_t offset ) {
	return this->move(this, offset - this->offset );
}

bool Iterator_backtrack ( Iterator* this, size_t offset, size_t lines ) {
	assert(offset <= this->offset);
	assert(lines  <= this->lines);
	this->lines = lines;
	return this->move(this, offset - this->offset );
}

char Iterator_charAt ( Iterator* this, size_t offset ) {
	assert(this->offset == (this->current - this->buffer));
	assert(offset <= this->available);
	return (char)(this->buffer[offset]);
}

void Iterator_free( Iterator* this ) {
	// FIXME: Should close input file
	// TRACE("Iterator_free: %p", this)
	if (this->freeBuffer) {
		__FREE(this->buffer);
	}
	__FREE(this);
}

// ----------------------------------------------------------------------------
//
// STRING INPUT
//
// ----------------------------------------------------------------------------

bool String_move ( Iterator* this, int n ) {
	assert(this->capacity == this->available);
	if ( n == 0) {
		// --- STAYING IN PLACE -----------------------------------------------
		// We're not moving position
		DEBUG("String_move: did not move (n=%d) offset=%zu/length=%zu, available=%zu, current-buffer=%ud\n", n, this->offset, this->capacity, this->available, (unsigned int)(this->current - this->buffer));
		return TRUE;
	} else if ( n >= 0 ) {
		// --- MOVING FORWARD -------------------------------------------------
		// We're moving forward, so we want to know if there is at one more element
		// in the file input.
		size_t left = this->available - this->offset;
		// `c` is the number of elements we're actually agoing to move, which
		// is either `n` or the number of elements left.
		size_t c    = n <= left ? n : left;
		// This iterates throught the characters and counts line separators.
		while (c > 0) {
			this->current++;
			this->offset++;
			if (*(this->current) == this->separator) {this->lines++;}
			c--;
		}
		// We then store the amount of available
		left = this->available - this->offset;
		// DEBUG("String_move: moved forward by c=%zu, n=%d offset=%zu capacity=%zu, available=%zu, current-buffer=%ld", c_copy, n, this->offset, this->capacity, this->available, this->current - this->buffer);
		if (left == 0) {
			// If we have no more available elements, then the status of
			// the stream is STATUS_ENDED
			this->status = STATUS_ENDED;
			return FALSE;
		} else {
			// Otherwise, we can go on.
			return TRUE;
		}
	} else {
		// --- BACKTRACKING ---------------------------------------------------
		// We cannot backtrack further than the current offset.
		n = MAX(n, 0 - this->offset);
		// FIXME: This is a little bit brittle, we should rather use a macro
		// in the iterator itself.
		this->current    = (((char*)this->current) + n);
		this->offset    += n;
		if (n!=0) {
			this->status  = STATUS_PROCESSING;
		}
		assert(Iterator_remaining(this) >= 0 - n);
		DEBUG("String_move: moved backwards by n=%d offset=%zu/length=%zu, available=%zu, current-buffer=%ud", n, this->offset, this->capacity, this->available, (unsigned int)(this->current - this->buffer));
		return TRUE;
	}
}

// ----------------------------------------------------------------------------
//
// FILE INPUT
//
// ----------------------------------------------------------------------------

FileInput* FileInput_new(const char* path ) {
	__NEW(FileInput, this);
	assert(this != NULL);
	// We open the file
	this->path = path;
	this->file = fopen(path, "r");
	if (this->file==NULL) {
		ERROR("Cannot open file: %s", path);
		__FREE(this);
		return NULL;
	} else {
		return this;
	}
}

void FileInput_free(FileInput* this) {
	// TRACE("FileInput_free: %p", this)
	if (this->file != NULL) { fclose(this->file);   }
}

size_t FileInput_preload( Iterator* this ) {
	// We want to know if there is at one more element
	// in the file input.
	FileInput*   input         = (FileInput*)this->input;
	size_t       read          = this->current   - this->buffer;
	size_t       left          = this->available - read;
	size_t       until_eob     = this->capacity  - read;
	DEBUG("FileInput_preload: %zu read, %zu available/%zu buffer capacity [%c]", read, this->available, this->capacity, this->status);
	assert (left < this->capacity);
	// Do the number of bytes up until the end of the buffer is less than
	// ITERATOR_BUFFER_AHEAD, then we need to expand the the buffer and make
	// sure we have ITERATOR_BUFFER_AHEAD data, unless we reach the end of the
	// input stream.
	if ( (this->available == 0 || until_eob < ITERATOR_BUFFER_AHEAD) && this->status != STATUS_INPUT_ENDED) {
		// We move buffer[current:] to the begining of the buffer
		// FIXME: We should make sure we don't call preload each time
		// memmove((void*)this->buffer, (void*)this->current, left);
		size_t delta    = this->current - this->buffer;
		// We want to grow the buffer size by ITERATOR_BUFFER_AHEAD
		this->capacity += ITERATOR_BUFFER_AHEAD;
		// This assertion is a bit weird, but it does not hurt
		assert(this->capacity + 1 > 0);
		DEBUG("<<< FileInput: growing buffer to %zu", this->capacity + 1)
		// FIXME: Not sure that realloc is a good idea, as any previous pointer
		// to the buffer would change...
		__RESIZE(this->buffer, this->capacity + 1);
		assert(this->buffer != NULL);
		// We need to update the current pointer as the buffer has changed
		this->current = this->buffer + delta;
		// We make sure we add a trailing \0 to the buffer
		this->buffer[this->capacity] = '\0';
		// We want to read as much as possible so that we fill the buffer
		size_t to_read         = this->capacity - left;
		size_t read            = fread((char*)this->buffer + this->available, sizeof(char), to_read, input->file);
		this->available        += read;
		left                   += read;
		DEBUG("<<< FileInput: read %zu bytes from input, available %zu, remaining %zu", read, this->available, Iterator_remaining(this));
		assert(Iterator_remaining(this) == left);
		assert(Iterator_remaining(this) >= read);
		if (read == 0) {
			 DEBUG("FileInput_preload: End of file reached with %zu bytes available", this->available);
			this->status = STATUS_INPUT_ENDED;
		}
	}
	return left;
}

bool FileInput_move   ( Iterator* this, int n ) {
	if ( n == 0) {
		// We're not moving position
		return TRUE;
	} else if ( n >= 0 ) {
		// We're moving forward, so we want to know if there is at one more element
		// in the file input.
		size_t left = FileInput_preload(this);
		if (left > 0) {
			int c = n > left ? left : n;
			// We have enough space left in the buffer to read at least one character.
			// We increase the head, copy
			while (c > 0) {
				this->current++;
				this->offset++;
				if (*(this->current) == this->separator) {this->lines++;}
				c--;
			}
			DEBUG("[>] %d+%d == %zu (%zu bytes left)", ((int)this->offset) - n, n, this->offset, left);
			if (n>left) {
				this->status = STATUS_INPUT_ENDED;
				return FALSE;
			} else {
				return TRUE;
			}
		} else {
			DEBUG("FileInput_move: end of input stream reach at %zu", this->offset);
			assert (this->status == STATUS_INPUT_ENDED || this->status == STATUS_ENDED);
			this->status = STATUS_ENDED;
			return FALSE;
		}
	} else {
		// The assert below is temporary, once we figure out when to free the input data
		// that we don't need anymore this would work.
		ASSERT(this->capacity > this->offset, "FileInput_move: offset is greater than capacity (%zu > %zu)", this->offset, this->capacity)
		// We make sure that `n` is not bigger than the length of the available buffer
		n = ((int)this->capacity )+ n < 0 ? 0 - (int)this->capacity : n;
		this->current = (((char*)this->current) + n);
		this->offset += n;
		if (n!=0) {this->status  = STATUS_PROCESSING;}
		DEBUG("[<] %d%d == %zu (%zu available, %zu capacity, %zu bytes left)", ((int)this->offset) - n, n, this->offset, this->available, this->capacity, Iterator_remaining(this));
		assert(Iterator_remaining(this) >= 0 - n);
		return TRUE;
	}
}

// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

Grammar* Grammar_new(void) {
	__NEW(Grammar, this);
	this->axiom      = NULL;
	this->skip       = NULL;
	this->axiomCount = 0;
	this->skipCount  = 0;
	this->elements   = NULL;
	this->isVerbose  = FALSE;
	return this;
}

void Grammar_setVerbose ( Grammar* this ) {
	this->isVerbose = TRUE;
}

void Grammar_setSilent ( Grammar* this ) {
	this->isVerbose = FALSE;
}

int Grammar_symbolsCount(Grammar* this) {
	return this->axiomCount + this->skipCount;
}

void Grammar_freeElements(Grammar* this) {
	if (this->elements == NULL) {
		Grammar_prepare(this);
	}
	int count = (this->axiomCount + this->skipCount);
	if (this->elements != NULL) {
		// NOTE: We iterate count so that we have count + 1
		for (int i = 0; i < count + 1 ; i++ ) {
			Element* element = this->elements[i];
			if (element == NULL) {
				TRACE("Grammar_freeElements(%p):[%d/%d]->NULL", this, i, count);
			} else if (ParsingElement_Is(element)) {
				ParsingElement* e = (ParsingElement*)element;
				TRACE("Grammar_freeElements(%p):[%d/%d]->ParsingElement %p %c.%d#%s", this, i, count, element, e->type, e->id, e->name)
				ParsingElement_free(e);
			} else {
				Reference* r = (Reference*)element;
				TRACE("Grammar_freeElements(%p):[%d/%d]->Reference %p.%c(%d)[%c]#%s", this, i, count, element, r->type, r->id, r->cardinality, r->name)
				Reference_free(r);
			}
		}
	}
	this->axiomCount = 0;
	this->skipCount  = 0;
	this->skip       = NULL;
	this->axiom      = NULL;
	__FREE(this->elements);
	this->elements = NULL;
}

void Grammar_free(Grammar* this) {
	Grammar_freeElements(this);
	__FREE(this);
}

// ----------------------------------------------------------------------------
//
// MATCH
//
// ----------------------------------------------------------------------------

Match* Match__Success(size_t length, Element* element, ParsingContext* context) {
	NEW(Match,this);
	assert( element != NULL );
	this->status   = STATUS_MATCHED;
	this->offset   = context->iterator->offset;
	this->length   = length;
	// FIXME: This should be the original line offset
	this->line     = context->iterator->lines;
	this->element  = (Element*)element;
	this->data     = NULL;
	this->next     = NULL;
	this->children = NULL;
	this->parent   = NULL;
	return this;
}

Match* Match_Success(size_t length, ParsingElement* element, ParsingContext* context) {
	return Match__Success(length, (Element*)element, context);
}

Match* Match_SuccessFromReference(size_t length, Reference* element, ParsingContext* context) {
	return Match__Success(length, (Element*)element, context);
}

Match* Match_new(void) {
	__NEW(Match,this);
	// DEBUG("Allocating match: %p", this);
	this->status    = STATUS_INIT;
	this->offset    = 0;
	this->length    = 0;
	this->line      = 0;
	this->element   = NULL;
	this->data      = NULL;
	this->next      = NULL;
	this->children  = NULL;
	this->parent    = NULL;
	this->result    = NULL;
	return this;
}

// TODO: We might want to recycle the objects for better performance and
// fewer allocs.
void Match_free(Match* this) {
	if (this!=NULL && this!=FAILURE) {
		TRACE("Match_free(%c:%d@%s,%lu-%lu)", ((ParsingElement*)this->element)->type, ((ParsingElement*)this->element)->id, ((ParsingElement*)this->element)->name, this->offset, this->offset + this->length)

		// We free the children
		assert(this->children != this);
		Match_free(this->children);

		// We free the next one
		assert(this->next != this);
		Match_free(this->next);

		// If the match is from a parsing element
		if (ParsingElement_Is(this->element)) {
			ParsingElement* element = ((ParsingElement*)this->element);
			assert(ParsingElement_Is(this->element));
			// and the parsing element declared a free match function, we
			// apply it.
			if (element->freeMatch) {
				element->freeMatch(this);
			}
		} else {
			assert(Reference_Is(this->element));
			ParsingElement* element = ((Reference*)this->element)->element;
			assert(ParsingElement_Is(element));
			if (element->freeMatch) {
				element->freeMatch(this);
			}

		}
		// We deallocate this one
		__FREE(this);
	}
}


int Match_getElementID(Match* this) {
	if (this == NULL || this->element == NULL) {return -1;}
	if (((ParsingElement*)this->element)->type == TYPE_REFERENCE) {
		return ((Reference*)this->element)->id;
	} else {
		ParsingElement* element = ParsingElement_Ensure(this->element);
		return element->id;
	}
}

char Match_getElementType(Match* this) {
	if (this == NULL || this->element == NULL) {return ' ';}
	if (((ParsingElement*)this->element)->type == TYPE_REFERENCE) {
		return ((Reference*)this->element)->element->type;
	} else {
		ParsingElement* element = ParsingElement_Ensure(this->element);
		return element->type;
	}
}

const char* Match_getElementName(Match* this) {
	if (this == NULL || this->element == NULL) {return NULL;}
	if (((ParsingElement*)this->element)->type == TYPE_REFERENCE) {
		return ((Reference*)this->element)->name;
	} else {
		ParsingElement* element = ParsingElement_Ensure(this->element);
		return element->name;
	}
}

int Match_getOffset(Match *this) {
	if (this == NULL) {return -1;}
	return (int)this->offset;
}

int Match_getLength(Match *this) {
	if (this == NULL) {return 0;}
	return (int)this->length;
}

int Match_getEndOffset(Match *this) {
	if (this == NULL) {return -1;}
	return (int)(this->length + this->offset);
}

bool Match_isSuccess(Match* this) {
	return (this != NULL && this != FAILURE && this->status == STATUS_MATCHED);
}

int Match__walk(Match* this, MatchWalkingCallback callback, int step, void* context ){
	step = callback(this, step, context);
	if (this->children != NULL && step >= 0) {
		step = Match__walk(this->children, callback, step + 1, context);
	}
	if (this->next != NULL && step >= 0) {
		step = Match__walk(this->next, callback, step + 1, context);
	}
	return step;
}


bool Match_hasNext(Match* this) {
	return this != NULL && this->next != NULL;
}

Match* Match_getNext(Match* this) {
	return this != NULL ? this->next : NULL;
}

bool Match_hasChildren(Match* this) {
	return this != NULL && this->children != NULL;
}

Match* Match_getChildren(Match* this) {
	return this != NULL ? this->children : NULL;
}

int Match__walkCounter (Match* this, int step, void* context) {
	return step;
}

int Match_countAll(Match* this) {
	return Match__walk(this, Match__walkCounter, 0, NULL);
}

int Match_countChildren(Match* this) {
	int count = 0;
	Match* child = this->children;
	while (child!=NULL){
		count += 1;
		child = child->next;
	}
	return count;
}

// ============================================================================
// JSON FORMATTING
// ============================================================================
//
#define JSONV(format,...) OUTPUT(format, __VA_ARGS__)
#define JSON(format)      OUTPUT(format)

void Match__childrenToJSON(Match* match, int fd) {
	int count = 0 ;
	Match* child = match->children;
	while (child != NULL) {
		ParsingElement* element = ParsingElement_Ensure(child->element);
		if (element->type != TYPE_PROCEDURE && element->type != TYPE_CONDITION) {
			count += 1;
		}
		child = child->next;
	}
	child = match->children;
	int i = 0;
	while (child != NULL) {
		ParsingElement* element = ParsingElement_Ensure(child->element);
		if (element->type != TYPE_PROCEDURE && element->type != TYPE_CONDITION) {
			Match__toJSON(child, fd);
			if ( (i+1) < count ) {
				JSON(",");
			}
			i += 1;
		}
		child = child->next;
	}
}

void Match__toJSON(Match* match, int fd) {
	if (match == NULL || match->element == NULL) {
		JSON("null");
		return;
	}

	ParsingElement* element = (ParsingElement*)match->element;

	if (element->type == TYPE_REFERENCE) {
		Reference* ref = (Reference*)match->element;
		if (ref->cardinality == CARDINALITY_ONE || ref->cardinality == CARDINALITY_OPTIONAL) {
			Match__toJSON(match->children, fd);
		} else {
			JSON("[");
			Match__childrenToJSON(match, fd);
			JSON("]");
		}
	}
	else if (element->type != TYPE_REFERENCE) {
		//printf("{\"type\":\"%c\",\"name\":%s,\"start\":%l ,\"length\":%l ,\"value\":", element->type, element->name, match->offset, match->length);
		int i     = 0;
		int count = 0;
		char* word = NULL;
		switch(element->type) {
			case TYPE_WORD:
				word = String_escape(Word_word(element));
				JSONV("\"%s\"", word);
				free(word);
				break;
			case TYPE_TOKEN:
				count = TokenMatch_count(match);
				if (count>1) {JSON("[");}
				for (i=0 ; i < count ; i++) {
					word = String_escape(TokenMatch_group(match, i));
					JSONV("\"%s\"", word);
					free(word);
					if ((i + 1) < count) {JSON(",X");}
				}
				if (count>1) {JSON("]");}
				break;
			case TYPE_GROUP:
				if (match->children == NULL)  {
					JSON("GROUP:undefined");
				} else {
					Match__toJSON(match->children, fd);
				}
				break;
			case TYPE_RULE:
				JSON("[");
				Match__childrenToJSON(match, fd);
				JSON("]");
				break;
			case TYPE_PROCEDURE:
				break;
			case TYPE_CONDITION:
				break;
			default:
				JSONV("\"ERROR:undefined element type=%c\"", element->type);
		}
	} else {
		JSONV("\"ERROR:unsupported element type=%c\"", element->type);
	}
}

// @method
void Match_toJSON(Match* this, int fd) {
	Match__toJSON(this, 1);
}

// ----------------------------------------------------------------------------
//
// PERSING ELEMENT
//
// ----------------------------------------------------------------------------

bool ParsingElement_Is(void *this) {
	if (this == NULL) { return FALSE; }
	switch (((ParsingElement*)this)->type) {
		// It is not a parsing element if it is a refernence
		case TYPE_ELEMENT:
		case TYPE_WORD:
		case TYPE_TOKEN:
		case TYPE_GROUP:
		case TYPE_RULE:
		case TYPE_CONDITION:
		case TYPE_PROCEDURE:
			return TRUE;
		default:
			return FALSE;
	}
}

ParsingElement* ParsingElement_Ensure(void* elementOrReference) {
	void * element = elementOrReference;
	assert(element!=NULL);
	assert(Reference_Is(element) || ParsingElement_Is(element));
	return Reference_Is(element) ? ((Reference*)element)->element : (ParsingElement*)element;
}

ParsingElement* ParsingElement_new(Reference* children[]) {
	__NEW(ParsingElement, this);
	this->type      = TYPE_ELEMENT;
	this->id        = ID_UNBOUND;
	this->name      = NULL;
	this->config    = NULL;
	this->children  = NULL;
	this->recognize = NULL;
	this->process   = NULL;
	this->freeMatch = NULL;
	if (children != NULL && *children != NULL) {
		Reference* r = Reference_Ensure(*children);
		while ( r != NULL ) {
			DEBUG("ParsingElement: %s adding child: %s", this->name, r->element->name)
			// FIXME: Make sure how memory is managed here
			ParsingElement_add(this, r);
			r = *(++children);
		}
	}
	return this;
}

void ParsingElement_freeChildren( ParsingElement* this ) {
	if (this == NULL) {return;}
	Reference* child = this->children;
	while (child != NULL) {
		Reference* next = child->next;
		assert(Reference_Is(child));
		Reference_free(child);
		child = next;
	}
}


void ParsingElement_free(ParsingElement* this) {
	// NOTE: We don't want/need to free the children as the Grammar already
	// holds a table of all elements.
	if (this == NULL) {return;}
	switch (this->type) {
		case TYPE_TOKEN:
			Token_free(this);
			break;
		case TYPE_WORD:
			Word_free(this);
			break;
		default:
			if (this!=NULL) {__FREE(this->name)};
			__FREE(this);
	}
}

ParsingElement* ParsingElement_add(ParsingElement* this, Reference* child) {
	assert(!Reference_hasNext(child));
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

ParsingElement* ParsingElement_clear(ParsingElement* this) {
	Reference* child = this->children;
	while ( child != NULL ) {
		assert(Reference_Is(child));
		Reference* next = child->next;
		Reference_free(child);
		child = next;
	}
	return this;
}

Match* ParsingElement_process( ParsingElement* this, Match* match ) {
	return match;
}

size_t ParsingElement_skip( ParsingElement* this, ParsingContext* context) {
	if (this == NULL || context == NULL || context->grammar->skip == NULL || context->flags & FLAG_SKIPPING) {return 0;}
	context->flags = context->flags | FLAG_SKIPPING;
	ParsingElement* skip = context->grammar->skip;
	size_t offset        = context->iterator->offset;
	// We don't care about the result, just the offset change.
	Match_free(skip->recognize(skip, context));
	size_t skipped = context->iterator->offset - offset;
	if (skipped > 0) {
		OUT_IF(context->grammar->isVerbose, " %s   ►►►skipped %zu", context->indent, skipped)
	}
	context->flags = context->flags & ~FLAG_SKIPPING;
	return skipped;
}

ParsingElement* ParsingElement_name( ParsingElement* this, const char* name ) {
	if (this == NULL) {return this;}
	__FREE(this->name);
	__STRING_COPY(this->name, name);
	return this;
}

const char* ParsingElement_getName( ParsingElement* this ) {
	return this == NULL ? NULL : (const char*)this->name;
}

int ParsingElement_walk( ParsingElement* this, ElementWalkingCallback callback, void* context ) {
	return ParsingElement__walk(this, callback, 0, context);
}

int ParsingElement__walk( ParsingElement* this, ElementWalkingCallback callback, int step, void* context ) {
	TRACE("ParsingElement__walk: %4d %c %-20s [%4d]", this->id, this->type, this->name, step);
	int i = step;
	step  = callback((Element*)this, step, context);
	Reference* child = this->children;
	while ( child != NULL && step >= 0) {
		// We are sure here that the child is a reference, so we can
		// call Reference__walk directly.
		assert(Reference_Is(child));
		int j = Reference__walk(child, callback, ++i, context);
		// We need to break the loop whenever this returns < 0
		if (j > 0) { step = i = j; }
		else {break;}
		child = child->next;
	}
	return (step > 0) ? step : i;
}

// ----------------------------------------------------------------------------
//
// ELEMENT
//
// ----------------------------------------------------------------------------

int Element_walk( Element* this, ElementWalkingCallback callback, void* context ) {
	return Element__walk(this, callback, 0, context);
}

int Element__walk( Element* this, ElementWalkingCallback callback, int step, void* context ) {
	assert (callback != NULL);
	TRACE("Element__walk     = %4d", step);
	if (this!=NULL) {
		if (Reference_Is(this)) {
			step = Reference__walk((Reference*)this, callback, step, context);
		} else if (ParsingElement_Is(this)) {
			step = ParsingElement__walk((ParsingElement*)this, callback, step, context);
		} else {
			assert(FALSE);
		}
	}
	return step;
}

// ----------------------------------------------------------------------------
//
// REFERENCE
//
// ----------------------------------------------------------------------------

bool Reference_Is(void * this) {
	return this!=NULL && ((Reference*)this)->type == TYPE_REFERENCE;
}

bool Reference_IsMany(void * this) {
	return Reference_Is(this) && (((Reference*)this)->cardinality == CARDINALITY_MANY || ((Reference*)this)->cardinality == CARDINALITY_MANY_OPTIONAL);
}

Reference* Reference_Ensure(void* elementOrReference) {
	void * element = elementOrReference;
	assert(element!=NULL);
	assert(Reference_Is(element) || ParsingElement_Is(element));
	return ParsingElement_Is(element) ? Reference_FromElement(element) : element;
}

Reference* Reference_FromElement(ParsingElement* element){
	NEW(Reference, this);
	assert(element!=NULL);
	this->element = element;
	this->name    = NULL;
	ASSERT(element->recognize, "Reference_FromElement: Element %s has no recognize callback", element->name);
	return this;
}

Reference* Reference_new(void) {
	__NEW(Reference, this);
	this->type        = TYPE_REFERENCE;
	this->id          = ID_UNBOUND;
	this->cardinality = CARDINALITY_ONE;
	this->name        = NULL;
	this->element     = NULL;
	this->next        = NULL;
	assert(!Reference_hasElement(this));
	assert(!Reference_hasNext(this));
	// DEBUG("Reference_new: %p, element=%p, next=%p", this, this->element, this->next);
	return this;
}

void Reference_free(Reference* this) {
	// TRACE("Reference_free: %p", this)
	// NOTE: We do not free the referenced element nor the next reference.
	// That would be the job of the grammar.
	if (this != NULL) {__FREE(this->name);}
	__FREE(this)
}

bool Reference_hasElement(Reference* this) {
	return this->element != NULL;
}

bool Reference_hasNext(Reference* this) {
	return this->next != NULL;
}

bool Reference_isMany(Reference* this) {
	// NOTE: This is redundant wit Reference_IsMany
	return this != NULL && (this->cardinality == CARDINALITY_MANY || this->cardinality == CARDINALITY_MANY_OPTIONAL);
}

Reference* Reference_cardinality(Reference* this, char cardinality) {
	assert(this!=NULL);
	this->cardinality = cardinality;
	return this;
}

Reference* Reference_name(Reference* this, const char* name) {
	assert(this!=NULL);
	__FREE(this->name);
	__STRING_COPY(this->name, name);
	return this;
}

int Reference__walk( Reference* this, ElementWalkingCallback callback, int step, void* context ) {
	TRACE("Reference__walk     : %4d %c %-20s [%4d]", this->id, this->type, this->name, step);
	step = callback((Element*)this, step, context);
	if (step >= 0) {
		assert(!Reference_Is(this->element));
		step = ParsingElement__walk(this->element, callback, step + 1, context);
	}
	return step;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {

	// References are pretty much always the root elements (at the exception of
	// the axiom). They can match 0 or many elements (depending on their cardinality),
	// and should try to skip input if after each iteration.

	assert(this->element != NULL);
	Match* result = FAILURE;
	Match* tail   = NULL;
	int    count  = 0;
	int    offset = context->iterator->offset;
	int    match_end_offset = offset;
	size_t match_end_lines  = context->iterator->lines;

	// If the wrapped element is a procedure, then the cardinality can only be one or optional, as a procedure does
	// not consume input.
	assert(this->element->type != TYPE_PROCEDURE || this->cardinality == CARDINALITY_ONE || this->cardinality == CARDINALITY_OPTIONAL );

	// We loop while there is more data to parse, or if the element type is a procedure (or condition)
	size_t current_offset = offset;
	while ((Iterator_hasMore(context->iterator) || this->element->type == TYPE_PROCEDURE || this->element->type == TYPE_CONDITION)) {

		// We log the current iteration, but only if we know there's going to be more than one
		ASSERT(this->element->recognize, "Reference_recognize: Element '%s' has no recognize callback", this->element->name);
		if (this->cardinality != CARDINALITY_ONE && this->cardinality != CARDINALITY_OPTIONAL) {
			OUT_STEP("   %s ├┈" BOLDYELLOW "[%d](%c)" RESET,
				context->indent, count, this->cardinality
			);
		}

		// We ask the element to recognize the current iterator's position
		int iteration_offset = context->iterator->offset;
		Match* match         = this->element->recognize(this->element, context);
		int parsed           = context->iterator->offset - iteration_offset;

		// Is the match successful ?
		if (Match_isSuccess(match)) {
			match_end_offset = Match_getEndOffset(match);
			// NOTE: not 100% about this
			match_end_lines  = context->iterator->lines;
			if (count == 0) {
				// If it's the first match and we're in a ONE/OPTIONAL reference, we break
				// the loop.
				result = match;
				tail   = match;
				if (parsed == 0 || this->cardinality == CARDINALITY_ONE || this->cardinality == CARDINALITY_OPTIONAL) {
					// If we have cardinality that is either 0..1 or 1, then we can exit the iteration
					// as we've recognized the reference properly.
					count += 1;
					break;
				}
			} else {
				// If we're already had a match we append the tail and update
				// the tail to be the current match
				tail->next = match;
				tail       = match;
				if (parsed == 0) {
					break;
				}
			}
			count++;
		// or is it not successful?
		} else {
			// If the match is not a success, then we try to skip some input
			// and see if we get a match.
			size_t skipped = ParsingElement_skip((ParsingElement*)this, context);
			// We only break when there's not skipped input.
			if (skipped == 0) {
				break;
			}
		}
		if (current_offset == context->iterator->offset) {
			break;
		}
	}

	// Here we make sure that the skipping does not take away valuable input
	// from the iterator. For instance, if a skip eats whitespace after
	// the last match, that will make any whitespace-consuming token
	// fail, while they would match if there had been no skipping.
	if (context->iterator->offset != match_end_offset) {
		// NOTE: It backtrack always right?
		Iterator_backtrack(context->iterator, match_end_offset, match_end_lines);
	}

	DEBUG_IF(count > 0, "        Reference %s#%d@%s matched %d times out of %c",  this->element->name, this->element->id, this->name, count, this->cardinality);

	// Depending on the cardinality, we might return FAILURE, or not
	bool is_success = Match_isSuccess(result) ? TRUE : FALSE;
	switch (this->cardinality) {
		case CARDINALITY_ONE:
			break;
		case CARDINALITY_OPTIONAL:
			// For optional, we return an empty match if the match fails, which
			// will make the reference succeed.
			is_success = TRUE;
			break;
		case CARDINALITY_MANY:
			assert(count > 0 || result == FAILURE);
			break;
		case CARDINALITY_MANY_OPTIONAL:
			assert(count > 0 || result == FAILURE);
			is_success = TRUE;
			break;
		default:
			// Unsuported cardinality
			ERROR("Unsupported cardinality %c", this->cardinality);
			return MATCH_STATS(FAILURE);
	}

	// NOTE: We don't log refernence match, as they're duplicates of the actual
	// wrapped parsing element.
	if (is_success == TRUE) {
		// If we have a success, then we create a new match with the reference
		// as element. The data will be NULL, but the `child` (and actually,
		// the children) will match the cardinality and will contain parsing
		// element matches.
		int    length   = context->iterator->offset - offset;
		Match* m        = Match_SuccessFromReference(length, this, context);
		// We make sure that if we had a success, that we add
		m->children     = result == FAILURE ? NULL : result;
		m->offset       = offset;
		assert(m->children == NULL || m->children->element != NULL);
		//OUT_IF(context->grammar->isVerbose, "[✓] %sReference %s#%d@%s matched %d/%c times over %d-%d", context->indent, this->element->name, this->element->id, this->name, count, this->cardinality, offset, offset+length)
		return MATCH_STATS(m);
	} else {
		//OUT_IF(context->grammar->isVerbose, " !  %sReference %s#%d@%s failed %d/%c times at %d-%d", context->indent, this->element->name, this->element->id, this->name, count, this->cardinality, offset, (int)context->stats->matchOffset);
		return MATCH_STATS(FAILURE);
	}
}

// ----------------------------------------------------------------------------
//
// WORD
//
// ----------------------------------------------------------------------------

ParsingElement* Word_new(const char* word) {
	__NEW(WordConfig, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->type           = TYPE_WORD;
	this->recognize      = Word_recognize;
	assert(word != NULL);
	config->length       = strlen(word);
	// NOTE: As of 0.7.5 we now keep a copy of the string, as it was
	// causing problems with PyPy, hinting at potential allocation issues
	// elsewhere.
	__STRING_COPY(config->word, word);
	assert(config->length>0);
	this->config         = config;
	assert(this->config    != NULL);
	assert(this->recognize != NULL);
	return this;
}

// TODO: Implement Word_free and regfree
void Word_free(ParsingElement* this) {
	// TRACE("Word_free: %p", this)
	WordConfig* config = (WordConfig*)this->config;
	if (config != NULL) {
		// We don't have anything special to dealloc besides the config
		free((void*)config->word);
		__FREE(config);
	}
	if (this!=NULL) {__FREE(this->name)};
	__FREE(this);
}


const char* Word_word(ParsingElement* this) {
	return ((WordConfig*)this->config)->word;
}

Match* Word_recognize(ParsingElement* this, ParsingContext* context) {
	WordConfig* config = ((WordConfig*)this->config);
	if (strncmp(config->word, context->iterator->current, config->length) == 0) {
		// NOTE: You can see here that the word actually consumes input
		// and moves the iterator.
		Match* success = MATCH_STATS(Match_Success(config->length, this, context));
		ASSERT(config->length > 0, "Word: %s configuration length == 0", config->word)
		context->iterator->move(context->iterator, config->length);
		OUT_STEP("[✓] %s└ Word %s#%d:`" CYAN "%s" RESET "` matched %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, ((WordConfig*)this->config)->word, context->iterator->lines, context->iterator->offset - config->length, context->iterator->offset, context->depth);
		return success;
	} else {
		OUT_STEP(" !  %s└ Word %s#%d:" CYAN "`%s`" RESET " failed at %zu:%zu[→%d]", context->indent, this->name, this->id, ((WordConfig*)this->config)->word, context->iterator->lines, context->iterator->offset, context->depth);
		return MATCH_STATS(FAILURE);
	}
}

const char* WordMatch_group(Match* match) {
	return ((WordConfig*)((ParsingElement*)match->element)->config)->word;
}

void Word_print(ParsingElement* this) {
	WordConfig* config = (WordConfig*)this->config;
	OUTPUT("Word:%c:%s#%d<%s>\n", this->type, this->name != NULL ? this->name : ANONYMOUS, this->id, config->word);
}

// ----------------------------------------------------------------------------
//
// TOKEN
//
// ----------------------------------------------------------------------------

ParsingElement* Token_new(const char* expr) {
	__NEW(TokenConfig, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->type           = TYPE_TOKEN;
	this->recognize      = Token_recognize;
	this->freeMatch      = TokenMatch_free;
	// NOTE: As of 0.7.5 we now keep a copy of the string, as it was
	// causing problems with PyPy, hinting at potential allocation issues
	// elsewhere.
	__STRING_COPY(config->expr, expr);
#ifdef WITH_PCRE
	const char* pcre_error;
	int         pcre_error_offset = -1;
	config->regexp = pcre_compile(config->expr, PCRE_UTF8, &pcre_error, &pcre_error_offset, NULL);
	if (pcre_error != NULL) {
		ERROR("Token: cannot compile regular expression `%s` at %d: %s", config->expr, pcre_error_offset, pcre_error);
		__FREE(config);
		__FREE(this);
		return NULL;
	}
	// SEE: http://pcre.org/original/doc/html/pcrejit.html
	config->extra = pcre_study(config->regexp, PCRE_STUDY_JIT_COMPILE, &pcre_error);
	if (pcre_error != NULL) {
		ERROR("Token: cannot optimize regular expression `%s` at %d: %s", config->expr, pcre_error_offset, pcre_error);
		__FREE(config);
		__FREE(this);
		return NULL;
	}
#endif
	this->config = config;
	assert(strcmp(config->expr, expr) == 0);
	assert(strcmp(Token_expr(this), expr) == 0);
	return this;
}


void Token_free(ParsingElement* this) {
	TokenConfig* config = (TokenConfig*)this->config;
	if (config != NULL) {
		// FIXME: Not sure how to free a regexp
#ifdef WITH_PCRE
		if (config->regexp != NULL) {pcre_free(config->regexp);}
		if (config->extra  != NULL) {pcre_free_study(config->extra);}
#endif
		__FREE(config->expr);
		__FREE(config);
	}
	if (this!=NULL) {__FREE(this->name)};
	__FREE(this);
}

const char* Token_expr(ParsingElement* this) {
	return ((TokenConfig*)this->config)->expr;
}

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
	assert(this->config);
	if(this->config == NULL) {return FAILURE;}
	Match* result = NULL;
#ifdef WITH_PCRE
	TokenConfig* config = (TokenConfig*)this->config;
	// NOTE: This has to be a multiple of 3, according to `man pcre_exec`
	int vector_length = 30;
	int vector[vector_length];
	const char* line = (const char*)context->iterator->current;
	// SEE: http://www.mitchr.me/SS/exampleCode/AUPG/pcre_example.c.html
	int r = pcre_exec(
		config->regexp, config->extra,     // Regex
		line,                              // Line
		context->iterator->available,      // Available data
		0,                                 // Offset
		  PCRE_ANCHORED                    // OPTIONS -- we do not skip position
		| PCRE_NO_UTF8_CHECK               // These following one are necessary
		| PCRE_NO_UTF16_CHECK              // for good performance, or the whole
		| PCRE_NO_UTF32_CHECK,             // string will be checked at each exec.
		vector,                            // Vector of matching offsets
		vector_length);                    // Number of elements in the vector
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
		OUT_STEP("    %s└✘Token " BOLDRED "%s" RESET "#%d:`" CYAN "%s" RESET "` failed at %zu:%zu", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset);
	} else {
		if(r == 0) {
			ERROR("Token: %s many substrings matched\n", config->expr);
			// Set rc to the max number of substring matches possible.
			// FIMXE: Not sure why we're doing 3 here, but it's what is
			// state in the doc
			// `ovecsize     Number of elements in the vector (a multiple of 3)`
			// in `man pcre_exec`.
			r = vector_length / 3;
		}
		// FIXME: Make sure it is the length and not the end offset
		result = Match_Success(vector[1], this, context);
		OUT_STEP("[✓] %s└ Token " BOLDGREEN "%s" RESET "#%d:" CYAN "`%s`" RESET " matched " BOLDGREEN "%zu:%zu-%zu" RESET, context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset, context->iterator->offset + result->length);

		// We create the token match
		__NEW(TokenMatch, data);
		data->count    = r;
		__ARRAY_NEW(groups, const char*, r);
		data->groups   = groups;
		// NOTE: We do this here, but it's probably better to do it later
		// once the token is recognized, although this poses the problem
		// of preserving the input.
		for (int j=0 ; j<r ; j++) {
			const char* substring;
			// This function copies the data into a freshly allocated
			// substring.
			pcre_get_substring(line, vector, r, j, &(substring));
			data->groups[j] = substring;
		}
		result->data = data;
		context->iterator->move(context->iterator,result->length);
		assert (result->data != NULL);
		assert(Match_isSuccess(result));
	}
#endif
	return MATCH_STATS(result);
}

const char* TokenMatch_group(Match* match, int index) {
	assert (match                != NULL);
	assert (match->data          != NULL);
	assert (((ParsingElement*)(match->element))->type == TYPE_TOKEN);
	TokenMatch* m = (TokenMatch*)match->data;
	assert (index >= 0);
	assert (index < m->count);
	return m->groups[index];
}


int TokenMatch_count(Match* match) {
	assert (match                != NULL);
	assert (match->data          != NULL);
	assert (((ParsingElement*)(match->element))->type == TYPE_TOKEN);
	TokenMatch* m = (TokenMatch*)match->data;
	return m->count;
}

void Token_print(ParsingElement* this) {
	TokenConfig* config = (TokenConfig*)this->config;
	OUTPUT("Token:%c:%s#%d<%s>\n", this->type, this->name != NULL ? this->name : ANONYMOUS, this->id, config->expr);
}


void TokenMatch_free(Match* match) {
	assert (match                != NULL);
	assert (Match_getElementType(match) == TYPE_TOKEN);
#ifdef WITH_PCRE
	TRACE("TokenMatch_free: %p", match)
	if (match->data != NULL) {
		TokenMatch* m = (TokenMatch*)match->data;
		if (m != NULL ) {
			for (int j=0 ; j<m->count ; j++) {
				pcre_free_substring(m->groups[j]);
			}
		}
		__FREE(m->groups);
	}
#endif
	__FREE(match->data);

}

// ----------------------------------------------------------------------------
//
// GROUP
//
// ----------------------------------------------------------------------------

ParsingElement* Group_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->type           = TYPE_GROUP;
	this->recognize      = Group_recognize;
	return this;
}

Match* Group_recognize(ParsingElement* this, ParsingContext* context){

	// The goal is to find ONE (and only one) matching element.
	OUT_STEP("??? %s┌── Group " BOLDYELLOW "%s" RESET ":#%d at %zu:%zu[→%d]", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset, context->depth);
	Match*     result           = NULL;
	size_t     offset           = context->iterator->offset;
	size_t     lines            = context->iterator->lines;
	int        step             = 0;

	// Note: we don't skip in groups, that,s the business of references
	size_t     iteration_offset = context->iterator->offset;
	Reference* child            = this->children;
	Match*     match            = NULL;
	step                        = 0;
	while (child != NULL ) {
		match = Reference_recognize(child, context);
		if (Match_isSuccess(match)) {
			// The first succeeding child wins
			result           = Match_Success(match->length, this, context);
			result->offset   = iteration_offset;
			result->children = match;
			child            = NULL;
			break;
		} else {
			// Otherwise we try the next child
			Match_free(match);
			child  = child->next;
			step  += 1;
		}
	}

	// We've either found one element, or nothing
	if (Match_isSuccess(result)) {
		OUT_STEP( "[✓] %s╘═⇒ Group " BOLDGREEN "%s" RESET "#%d[%d] matched" BOLDGREEN "%zu:%zu-%zu" RESET "[%zu][→%d]", context->indent, this->name, this->id, step,  context->iterator->lines, result->offset, context->iterator->offset, result->length, context->depth)
		return MATCH_STATS(result);
	} else {
		// If no child has succeeded, the whole group fails
		OUT_STEP(" !  %s╘═⇒ Group " BOLDRED "%s" RESET "#%d[%d] failed at %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, step, context->iterator->lines, context->iterator->offset, offset, context->depth)
		if (context->iterator->offset != offset ) {
			Iterator_backtrack(context->iterator, offset, lines);
			assert( context->iterator->offset == offset );
		}
		return MATCH_STATS(FAILURE);
	}

}


// ----------------------------------------------------------------------------
//
// RULE
//
// ----------------------------------------------------------------------------

ParsingElement* Rule_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->type           = TYPE_RULE;
	this->recognize      = Rule_recognize;
	// DEBUG("Rule_new: %p", this)
	return this;
}

Match* Rule_recognize (ParsingElement* this, ParsingContext* context){

	// An empty rule will fail. Not sure if this is the right thing to do, but
	// if we don't set the result, it will return NULL and break assertions
	Match*      result    = FAILURE;
	Match*      last      = NULL;
	int         step      = 0;
	const char* step_name = NULL;
	size_t      offset    = context->iterator->offset;
	size_t      lines     = context->iterator->lines;
	Reference* child      = this->children;

	OUT_STEP("??? %s┌── Rule:" BOLDYELLOW "%s" RESET " at %zu:%zu[→%d]", context->indent, this->name, context->iterator->lines, context->iterator->offset, context->depth);

	// We create a new parsing variable context
	ParsingContext_push(context);

	// We don't need to care wether the parsing context has more
	// data, the Reference_recognize will take care of it.
	while (child != NULL) {

		if (child->next != NULL) {
			OUT_STEP(" ‥%s├─" BOLDYELLOW "%d" RESET, context->indent, step);
		} else {
			OUT_STEP(" ‥%s└─" BOLDYELLOW "%d" RESET, context->indent, step);
		}


		// We iterate over the children of the rule. We expect each child to
		// match, and we might skip inbetween the children to find a match.
		Match* match = Reference_recognize(child, context);

		// If the match is not a success, we will try to skip some input
		// and try the match again.
		if (!Match_isSuccess(match)) {

			Match_free(match);
			size_t skipped = ParsingElement_skip(this, context);

			// If we've skipped at least one input element, then we can
			// try the match again.
			if (skipped > 0) {

				// If the rule failed, we try to skip characters. We free any
				// failure match, as we won't need it anymore.
				match = Reference_recognize(child, context);

				// If we haven't matched even after the skip, then we have a failure.
				if (!Match_isSuccess(match)) {
					// We free any failure match
					Match_free(match);
					result = FAILURE;
					// NOTE: We don't need to backtrack here, as a failure will
					// automatically backtrack to the start offset, so we
					// don't have the problem of skipping eating input
					// as in Reference_recognize
					break;
				}
			// If we didn't skip, then we fail the rule
			} else {
				result = FAILURE;
				break;
			}
		}

		// So we had a match
		assert(Match_isSuccess(match));
		if (last == NULL) {
			// If this is the first child (ie. last == NULL), we create
			// a new match success at the original parsing offset.
			result           = Match_Success(0, this, context);
			result->offset   = offset;
			result->children = last = match;
		} else {
			last = last->next = match;
		}

		// We log the step name, for debugging purposes
		step_name = child->name;
		// And we get the next child.
		child     = child->next;
		// We increment the step counter, used for debugging as well.
		step++;
	}

	// We pop the parsing context
	ParsingContext_pop(context);

	// We process the result
	if (Match_isSuccess(result)) {
		OUT_STEP("[✓] %s╘═⇒ Rule " BOLDGREEN "%s" RESET "#%d[%d] matched " BOLDGREEN "%zu:%zu-%zu" RESET "[%zub][→%d]",
				context->indent, this->name, this->id, step, context->iterator->lines,  offset, context->iterator->offset, result->length, context->depth)
		// In case of a success, we update the length based on the last
		// match.
		result->length = last->offset - result->offset + last->length;
	} else {
		OUT_STEP(" !  %s╘ Rule " BOLDRED "%s" RESET "#%d failed on step %d=%s at %zu:%zu-%zu[→%d]",
				context->indent, this->name, this->id, step, step_name == NULL ? "-" : step_name, context->iterator->lines, offset, context->iterator->offset, context->depth)
		// If we had a failure, then we backtrack the iterator
		if (offset != context->iterator->offset) {
			Iterator_backtrack(context->iterator, offset, lines);
			assert( context->iterator->offset == offset );
		}
	}

	return MATCH_STATS(result);
}

// ----------------------------------------------------------------------------
//
// PROCEDURE
//
// ----------------------------------------------------------------------------

ParsingElement* Procedure_new(ProcedureCallback c) {
	ParsingElement* this = ParsingElement_new(NULL);
	this->type      = TYPE_PROCEDURE;
	this->config    = c;
	this->recognize = Procedure_recognize;
	return this;
}

Match*  Procedure_recognize(ParsingElement* this, ParsingContext* context) {
	if (this->config != NULL) {
		// FIXME: Executing handlers is still quite problematic
		((ProcedureCallback)(this->config))(this, context);
	}
	OUT_STEP_IF(this->name, "[✓] %sProcedure " BOLDGREEN "%s" RESET "#%d executed at %zu", context->indent, this->name, this->id, context->iterator->offset)
	return MATCH_STATS(Match_Success(0, this, context));
}

// ----------------------------------------------------------------------------
//
// CONDITION
//
// ----------------------------------------------------------------------------

ParsingElement* Condition_new(ConditionCallback c) {
	ParsingElement* this = ParsingElement_new(NULL);
	this->type      = TYPE_CONDITION;
	this->config    = c;
	this->recognize = Condition_recognize;
	return this;
}

Match*  Condition_recognize(ParsingElement* this, ParsingContext* context) {
	if (this->config != NULL) {
		bool value    = ((ConditionCallback)this->config)(this, context);
		Match* result = value == TRUE ? Match_Success(0, this, context) : FAILURE;
		OUT_STEP_IF(Match_isSuccess(result), "[✓] %s└ Condition " BOLDGREEN "%s" RESET "#%d matched %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset - result->length, context->iterator->offset, context->depth)
		OUT_STEP_IF(!Match_isSuccess(result), " !  %s└ Condition " BOLDRED "%s" RESET "#%d failed at %zu:%zu[→%d]",  context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset, context->depth)
		return  MATCH_STATS(result);
	} else {
		OUT_STEP("[✓] %s└ Condition %s#%d matched by default at %zu", context->indent, this->name, this->id, context->iterator->offset);
		Match* result = Match_Success(0, this, context);
		assert(Match_isSuccess(result));
		return  MATCH_STATS(result);
	}
}

// ----------------------------------------------------------------------------
//
// PARSING STEP
//
// ----------------------------------------------------------------------------

ParsingStep* ParsingStep_new( ParsingElement* element ) {
	__NEW(ParsingStep, this);
	assert(element != NULL);
	this->element   = element;
	this->step      = 0;
	this->iteration = 0;
	this->status    = STATUS_INIT;
	this->match     = (Match*)NULL;
	this->previous  = NULL;
	return this;
}

void ParsingStep_free( ParsingStep* this ) {
	__FREE(this);
}

// ----------------------------------------------------------------------------
//
// PARSING OFFSET
//
// ----------------------------------------------------------------------------

ParsingOffset* ParsingOffset_new( size_t offset ) {
	__NEW(ParsingOffset, this);
	this->offset = offset;
	this->last   = (ParsingStep*)NULL;
	this->next   = (ParsingOffset*)NULL;
	return this;
}

void ParsingOffset_free( ParsingOffset* this ) {
	ParsingStep* step     = this->last;
	ParsingStep* previous = NULL;
	while (step != NULL) {
		previous   = step->previous;
		ParsingStep_free(step);
		step       = previous;
	}
	__FREE(this);
}

// ----------------------------------------------------------------------------
//
// PARSING VARIABLE
//
// ----------------------------------------------------------------------------

ParsingVariable* ParsingVariable_new(int depth, const char* key, void* value) {
	__NEW(ParsingVariable, this);
	this->depth    = depth;
	__STRING_COPY(this->key, key);
	this->value    = value;
	this->previous = NULL;
	return this;
}

void ParsingVariable_free(ParsingVariable* this) {
	if (this!=NULL) {
		__FREE(this->key);
		__FREE(this);
	}
}

void ParsingVariable_freeAll(ParsingVariable* this) {
	ParsingVariable* current = this;
	while (current!=NULL) {
		ParsingVariable* to_free = current;
		current = current->previous;
		ParsingVariable_free(to_free);
	}
}

int ParsingVariable_getDepth(ParsingVariable* this) {
	return this == NULL ? -1 : this->depth;
}

const char* ParsingVariable_getName(ParsingVariable* this) {
	return (const char*)this->key;
}

void* ParsingVariable_get(ParsingVariable* this, const char* name) {
	ParsingVariable* found = ParsingVariable_find(this, name, FALSE);
	return found != NULL ? found->value : NULL;
}

bool ParsingVariable_is(ParsingVariable* this, const char* key) {
	if (this == NULL || key == NULL) {return FALSE;}
	return (key == this->key || strcmp(this->key, key)) == 0 ? TRUE : FALSE;
}

ParsingVariable* ParsingVariable_find(ParsingVariable* this, const char* key, bool local) {
	ParsingVariable* current=this;
	while (current!=NULL) {
		if (ParsingVariable_is(current, key)) {
			return current;
		}
		if (current->previous!=NULL) {
			// When local is TRUE, we stop the search when the depth changes
			current = (local && current->previous->depth != current->depth) ? NULL : current->previous;
		} else {
			current = NULL;
		}
	}
	return current;
}

ParsingVariable* ParsingVariable_set(ParsingVariable* this, const char* key, void* value) {
	ParsingVariable* found = ParsingVariable_find(this, key, TRUE);
	if (found == NULL) {
		found = ParsingVariable_new( this->depth, key, value );
		found->previous = this;
		return found;
	} else {
		found->value = value;
		return found;
	}
}

ParsingVariable* ParsingVariable_push(ParsingVariable* this) {
	int depth            = this == NULL ? 0 : ParsingVariable_getDepth(this) + 1;
	ParsingVariable* res = ParsingVariable_new(depth, "depth", (void*)(long)depth);
	res->previous        = this;
	return res;
}

ParsingVariable* ParsingVariable_pop(ParsingVariable* this) {
	if (this == NULL) {return NULL;}
	ParsingVariable* current  = this;
	int depth = this->depth;
	while (current != NULL && current->depth >= depth) {
		ParsingVariable* to_free  = current;
		current = current->previous;
		ParsingVariable_free(to_free);
	}
	return current;
}

int  ParsingVariable_count(ParsingVariable* this) {
	ParsingVariable* current = this;
	int count = 0;
	while (current!=NULL) {
		current = current->previous;
		count++;
	}
	return count;
}

// ----------------------------------------------------------------------------
//
// PARSING CONTEXT
//
// ----------------------------------------------------------------------------

ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator ) {
	__NEW(ParsingContext, this);
	this->grammar   = g;
	this->iterator  = iterator;
	this->stats     = ParsingStats_new();
	if (g != NULL) {
		ParsingStats_setSymbolsCount(this->stats, g->axiomCount + g->skipCount);
	}
	this->offsets   = NULL;
	this->current   = NULL;
	this->depth     = 0;
	this->variables = ParsingVariable_new(0, "depth", 0);
	this->callback  = NULL;
	this->indent    = INDENT + (INDENT_MAX * INDENT_WIDTH);
	this->flags     = 0;
	this->lastMatch = NULL;
	return this;
}

void ParsingContext_free( ParsingContext* this ) {
	// NOTE: We don't need to free the last match, or the grammar;
	if (this!=NULL) {
		ParsingVariable_freeAll(this->variables);
		ParsingStats_free(this->stats);
		Iterator_free(this->iterator);
		__FREE(this);
	}
}

char* ParsingContext_text( ParsingContext* this ) {
	return this->iterator->buffer;
}

char ParsingContext_charAt ( ParsingContext* this, size_t offset ) {
	return Iterator_charAt(this->iterator, offset);
}


void ParsingContext_push     ( ParsingContext* this ) {
	this->variables = ParsingVariable_push(this->variables);
	if (this->callback != NULL) {this->callback(this, '+');}
	this->depth += 1;
	if (this->depth >= 0) {
		int d = this->depth % INDENT_MAX;
		this->indent = INDENT + (INDENT_MAX - d) * INDENT_WIDTH;
	}
}

void ParsingContext_pop      ( ParsingContext* this ) {
	if (this->callback != NULL) {this->callback(this, '-');}
	this->variables = ParsingVariable_pop(this->variables);
	this->depth -= 1;
	if (this->depth <= 0) {
		this->indent = INDENT + INDENT_MAX * INDENT_WIDTH;
	} else {
		int d = this->depth % INDENT_MAX;
		this->indent = INDENT + (INDENT_MAX - d) * INDENT_WIDTH;
	}
}

void* ParsingContext_get(ParsingContext* this, const char* name) {
	return ParsingVariable_get(this->variables, name);
}

int ParsingContext_getInt(ParsingContext* this, const char* name) {
	return (int)(long)(ParsingVariable_get(this->variables, name));
}

void ParsingContext_set(ParsingContext*  this, const char* name, void* value) {
	this->variables = ParsingVariable_set(this->variables, name, value);
}

void ParsingContext_setInt(ParsingContext*  this, const char* name, int value) {
	this->variables = ParsingVariable_set(this->variables, name, (void*)(long)value);
}

void ParsingContext_on(ParsingContext* this, ContextCallback callback) {
	this->callback = callback;
}

int  ParsingContext_getVariableCount(ParsingContext* this) {
	return ParsingVariable_count(this->variables);
}

size_t ParsingContext_getOffset(ParsingContext* this) {
	return this->iterator->offset;
}

Match* ParsingContext_registerMatch(ParsingContext* this, Element* e, Match* m) {
	ParsingStats_registerMatch(this->stats, e, m);
	// NOTE: We make sure to only register the deepest match, as the grammar
	// is likely to backtack and yield a partial match, erasing where the error
	// actually lies. We skip empty matches.
	if (Match_isSuccess(m)
	&& (this->lastMatch == NULL || ((this->lastMatch->offset + this->lastMatch->length) < (m->offset + m->length)))
	&& m->length > 0
	) {
		this->lastMatch = m;
	}
	return m;
}

// ----------------------------------------------------------------------------
//
// PARSING STATS
//
// ----------------------------------------------------------------------------

ParsingStats* ParsingStats_new(void) {
	__NEW(ParsingStats,this);
	this->bytesRead = 0;
	this->parseTime = 0;
	this->successBySymbol = NULL;
	this->failureBySymbol = NULL;
	this->failureOffset   = 0;
	this->matchOffset     = 0;
	this->matchLength     = 0;
	this->failureElement  = NULL;
	return this;
}

void ParsingStats_free(ParsingStats* this) {
	if (this != NULL) {
		__FREE(this->successBySymbol);
		__FREE(this->failureBySymbol);
	}
	__FREE(this);
}

void ParsingStats_setSymbolsCount(ParsingStats* this, size_t t) {
	__ARRAY_RESIZE(this->successBySymbol, size_t, t);
	__ARRAY_RESIZE(this->failureBySymbol, size_t, t);
	this->symbolsCount    = t;
}

Match* ParsingStats_registerMatch(ParsingStats* this, Element* e, Match* m) {
	// FIXME: This is broken!
	// We can convert ParsingElements to Reference and vice-versa as they
	// have the same start sequence (char type, int id).
	// Reference* r = (Reference*)e;
	// if (m!=NULL && Match_isSuccess(m)) {
	// 	this->successBySymbol[r->id] += 1;
	// 	if (m->offset >= this->matchOffset) {
	// 		this->matchOffset = m->offset;
	// 		this->matchLength = m->length;
	// 	}
	// } else {
	// 	this->failureBySymbol[r->id] += 1;
	// 	// We register the deepest failure
	// 	if(m != NULL && m->offset >= this->failureOffset) {
	// 		this->failureOffset  = m->offset;
	// 		this->failureElement = m->element;
	// 	}
	// }
	return m;
}

// ----------------------------------------------------------------------------
//
// PARSING RESULT
//
// ----------------------------------------------------------------------------

ParsingResult* ParsingResult_new(Match* match, ParsingContext* context) {
	__NEW(ParsingResult,this);
	assert(match != NULL);
	assert(context != NULL);
	assert(context->iterator != NULL);
	this->match   = match;
	this->context = context;
	if (match != FAILURE) {
		if (Iterator_hasMore(context->iterator) && Iterator_remaining(context->iterator) > 0) {
			LOG_IF(context->grammar->isVerbose, "Partial success, parsed %zu bytes, %zu remaining", context->iterator->offset, Iterator_remaining(context->iterator));
			this->status = STATUS_PARTIAL;
		} else {
			LOG_IF(context->grammar->isVerbose, "Succeeded, iterator at %zu, parsed %zu bytes, %zu remaining", context->iterator->offset, context->stats->bytesRead, Iterator_remaining(context->iterator));
			this->status = STATUS_SUCCESS;
		}
	} else {
		LOG_IF(context->grammar->isVerbose, "Failed, parsed %zu bytes, %zu remaining", context->iterator->offset, Iterator_remaining(context->iterator))
		this->status = STATUS_FAILED;
	}
	return this;
}


bool ParsingResult_isFailure(ParsingResult* this) {
	return this->status == STATUS_FAILED;
}

bool ParsingResult_isPartial(ParsingResult* this) {
	return this->status == STATUS_PARTIAL;
}

bool ParsingResult_isSuccess(ParsingResult* this) {
	return this->status == STATUS_SUCCESS;
}

char* ParsingResult_text(ParsingResult* this) {
	return this->context->iterator->buffer;
}

size_t ParsingResult_remaining(ParsingResult* this) {
	return Iterator_remaining(this->context->iterator);
}

int ParsingResult_textOffset(ParsingResult* this) {
	int buffer_offset = this->context->iterator->current - this->context->iterator->buffer;
	return this->context->iterator->offset - buffer_offset;
}

void ParsingResult_free(ParsingResult* this) {
	if (this != NULL) {
		Match_free(this->match);
		ParsingContext_free(this->context);
	}
	__FREE(this);
}

// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

int Grammar__resetElementIDs(Element* e, int step, void* nothing) {
	if (Reference_Is(e)) {
		Reference* r = (Reference*)e;
		if (r->id != ID_BINDING) {
			TRACE("Grammar__resetElementIDs: reset reference %d %s [%d]", r->id, r->name, step)
			r->id = ID_BINDING;
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id != ID_BINDING) {
			TRACE("Grammar__resetElementIDs: reset parsing element %d %s [%d]", r->id, r->name, step)
			r->id = ID_BINDING;
			return step;
		} else {
			return -1;
		}
	}
}

int Grammar__assignElementIDs(Element* e, int step, void* nothing) {
	if (Reference_Is(e)) {
		Reference* r = (Reference*)e;
		if (r->id == ID_BINDING) {
			r->id = step;
			DEBUG_IF(r->name != NULL, "[%03d] [%c] %s", r->id, r->type, r->name);
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id == ID_BINDING) {
			r->id = step;
			DEBUG_IF(r->name != NULL, "[%03d] [%c] %s", r->id, r->type, r->name);
			return step;
		} else {
			return -1;
		}
	}
}

int Grammar__registerElement(Element* e, int step, void* grammar) {
	Reference* r  = (Reference*)e;
	Grammar*   g  = (Grammar*)grammar;
	r->id         = r->id;
	Element*   ge = g->elements[r->id];
	if (ge == NULL) {
		TRACE("Grammar__registerElement:  %3d %c %s", r->id, r->type, r->name);
		g->elements[r->id] = e;
		return step;
	} else {
		return -1;
	}
}

void Grammar_prepare ( Grammar* this ) {
	if (this->skip!=NULL)  {
		this->skip->id = 0;
	}
	if (this->axiom!=NULL) {
		// We would need to free elements if they were already allocated
		if (this->elements) { __FREE(this->elements) ; this->elements = NULL; }
		assert(this->elements == NULL);

		TRACE("Grammar_prepare: resetting element IDs %c", ' ')
		ParsingElement_walk(this->axiom, Grammar__resetElementIDs, NULL);
		if (this->skip != NULL) {
			ParsingElement_walk(this->skip, Grammar__resetElementIDs, NULL);
		}

		TRACE("Grammar_prepare: assigning new element IDs %c", ' ')
		int count = ParsingElement_walk(this->axiom, Grammar__assignElementIDs, NULL);
		this->axiomCount = count;
		if (this->skip != NULL) {
			this->skipCount = ParsingElement__walk(this->skip, Grammar__assignElementIDs, count + 1, NULL) - count;
		}

		// Now we register the elements
		__ARRAY_NEW(elements, Element*, this->skipCount + this->axiomCount + 1);
		this->elements = elements;

		count = ParsingElement_walk(this->axiom, Grammar__registerElement, this);
		if (this->skip != NULL) {
			ParsingElement__walk(this->skip, Grammar__registerElement, count, this);
		}

		#ifdef WITH_TRACE
		int j = this->skipCount + this->axiomCount + 1;
		TRACE("Grammar_prepare:  skip=%d + axiom=%d = total=%d symbols", this->skipCount, this->axiomCount, j);
		for (int i=0 ; i < j ; i++) {
			Element* element = this->elements[i];
			if (element == NULL) {
			} else if (element->type == TYPE_REFERENCE) {
				TRACE("Grammar_prepare:  Reference    %4d %c %-20s [%4d/%4d]", element->id, element->type, element->name, i, j - 1);
			} else {
				TRACE("Grammar_prepare:  Element      %4d %c %-20s [%4d/%4d]", element->id, element->type, element->name, i, j - 1);
			}
		}
		#endif
	}
}

ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator ) {
	// We make sure the grammar is prepared before we start parsing
	if (this->elements == NULL) {Grammar_prepare(this);}
	assert(this->axiom != NULL);
	// ParsingOffset*  offset  = ParsingOffset_new(iterator->offset);
	ParsingContext* context = ParsingContext_new(this, iterator);
	assert(this->axiom->recognize != NULL);
	clock_t t1  = clock();
	Match* match = this->axiom->recognize(this->axiom, context);
	context->stats->parseTime = ((double)clock() - (double)t1) / CLOCKS_PER_SEC;
	context->stats->bytesRead = iterator->offset;
	return ParsingResult_new(match, context);
}

ParsingResult* Grammar_parsePath( Grammar* this, const char* path ) {
	Iterator* iterator = Iterator_Open(path);
	if (iterator != NULL) {
		return Grammar_parseIterator(this, iterator);
	} else {
		errno = ENOENT;
		return NULL;
	}
}

ParsingResult* Grammar_parseString( Grammar* this, const char* text ) {
	Iterator* iterator = Iterator_FromString(text);
	if (iterator != NULL) {
		return Grammar_parseIterator(this, iterator);
	} else {
		errno = ENOENT;
		return NULL;
	}
}

// ----------------------------------------------------------------------------
//
// PROCESSOR
//
// ----------------------------------------------------------------------------

Processor* Processor_new() {
	__NEW(Processor,this);
	this->callbacksCount = 100;
	__ARRAY_NEW(callbacks, ProcessorCallback, (size_t)this->callbacksCount);
	this->callbacks      = callbacks;
	this->fallback       = NULL;
	return this;
}

void Processor_free(Processor* this) {
	__FREE(this);
}

void Processor_register (Processor* this, int symbolID, ProcessorCallback callback ) {
	if (this->callbacksCount < (symbolID + 1)) {
		int cur_count        = this->callbacksCount;
		int new_count        = symbolID + 100;
		__ARRAY_RESIZE(this->callbacks, ProcessorCallback, new_count);
		this->callbacksCount = new_count;
		// We zero the new values, as `realloc` does not guarantee zero data.
		while (cur_count < new_count) {
			this->callbacks[cur_count] = NULL;
			cur_count++;
		}
	}
	this->callbacks[symbolID] = callback;
}

int Processor_process (Processor* this, Match* match, int step) {
	ProcessorCallback handler = this->fallback;
	if (ParsingElement_Is(match->element)) {
		int element_id = ((ParsingElement*)match->element)->id;
		if (element_id >= 0 && element_id < this->callbacksCount) {
			handler = this->callbacks[element_id];
		}
	}
	if (handler != NULL) {
		handler (this, match);
	} else {
		Match* child = match->children;
		while (child) {
			step  = Processor_process(this, child, step);
			child = child->next;
		}
	}
	return step;
}

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

bool Utilites_checkIndent( ParsingElement *this, ParsingContext* context ) {
	// Variable tabs = ParsingContext_getVariable("tabs", NULL, sizeof(int));
	// // TokenMatch_group(0)
	// int depth     = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	// if (depth != tabs_count) {
	// 	return FAILURE;
	// } else {
	// 	return Match_Success();
	// }
	return TRUE;
}

// EOF
