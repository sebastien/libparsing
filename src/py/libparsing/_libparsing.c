typedef struct gc_Reference { char guard; size_t size; int count; void* previous; void* next; } gc_Reference;
void gc_Reference_acquire( gc_Reference* ref );
gc_Reference* gc_Reference_release( gc_Reference* ref );
void gc_Reference_free( gc_Reference* ref );
gc_Reference* gc_ref( void* ptr );
void* gc_Reference_data( gc_Reference* ref ) {
 if (ref == NULL) {
  return NULL;
 } else {
  return ref + sizeof(gc_Reference);
 }
}

void gc_Reference_acquire( gc_Reference* ref ) {
 assert (ref != NULL);
 assert(((gc_Reference*)ref)->guard == 'G');
 ref->count += 1;
}

gc_Reference* gc_Reference_release( gc_Reference* ref ) {
 assert (ref != NULL);
 assert(((gc_Reference*)ref)->guard == 'G');
 ref->count -= 1;
 if (ref->count <= 0) {
  gc_Reference_free(ref);
  return NULL;
 } else {
  return ref;
 }
}

void gc_Reference_free( gc_Reference* ref ) {
 assert (ref != NULL);
 assert(((gc_Reference*)ref)->guard == 'G');
 assert(ref->count <= 0);
 free(ref);
}
gc_Reference* gc_ref( void* ptr ) {
 if (ptr == NULL) {
  return NULL;
 } else {

  return ptr;





 }
}


void gc_init( gc_Reference* ref, size_t size ) {







}





void* gc_new( size_t size ) {

 return malloc(size);





}

void* gc_newBlank( size_t size ) {

 return calloc(1, size);





}




void gc_free( void* ptr ) {

 free(ptr);



}

void gc_acquire( const void* ptr ) {



}

void gc_release( const void* ptr ) {



}

void* gc_realloc( void* ptr, size_t size ) {

 return realloc(ptr, size);
}

char* gc_strdup(const char* s) {

 return strdup(s);






}

void* gc_calloc(size_t count, size_t size) {

 return calloc(count, size);




}
int Parsing_hasPCRE(void);


int Parsing_hasGC(void);
typedef struct Iterator {
 char status;
 char* buffer;
 char* current;
 char separator;
 size_t offset;
 size_t lines;
 size_t capacity;
 size_t available;
 bool freeBuffer;

 void* input;
 void (*freeInput) (void*);
 bool (*move) (struct Iterator*, int n);
} Iterator;




typedef struct FileInput {
 FILE* file;
 const char* path;
} FileInput;



extern char EOL;



Iterator* Iterator_Open(const char* path);



Iterator* Iterator_FromString(const char* text);


Iterator* Iterator_new(void);


void Iterator_free(Iterator* this);





bool Iterator_open( Iterator* this, const char* path );




bool Iterator_hasMore( Iterator* this );





size_t Iterator_remaining( Iterator* this );



bool Iterator_moveTo ( Iterator* this, size_t offset );



bool Iterator_backtrack ( Iterator* this, size_t offset, size_t lines );



char Iterator_charAt ( Iterator* this, size_t offset );


bool String_move ( Iterator* this, int offset );
FileInput* FileInput_new(const char* path );


void FileInput_free(void* this);




size_t FileInput_preload( Iterator* this );





bool FileInput_move ( Iterator* this, int n );
typedef struct ParsingVariable ParsingVariable;
typedef struct ParsingContext ParsingContext;
typedef struct ParsingElement ParsingElement;
typedef struct ParsingResult ParsingResult;
typedef struct Reference Reference;
typedef struct Match Match;
typedef struct Element Element;


typedef struct Element {
 char type;
 int id;
 char* name;
} Element;


typedef struct Grammar {
 ParsingElement* axiom;
 ParsingElement* skip;
 int axiomCount;
 int skipCount;
 Element** elements;
 bool isVerbose;
 bool noMemo;
 bool skipWhitespace;
} Grammar;


Grammar* Grammar_new(void);


void Grammar_free(Grammar* this);


void Grammar_prepare ( Grammar* this );


void Grammar_setVerbose ( Grammar* this );


void Grammar_setNoMemo ( Grammar* this );


void Grammar_setSilent ( Grammar* this );


int Grammar_symbolsCount ( const Grammar* this );


ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator );


ParsingResult* Grammar_parsePath( Grammar* this, const char* path );


ParsingResult* Grammar_parseString( Grammar* this, const char* text );


void Grammar_freeElements(Grammar* this);







typedef int (*ElementWalkingCallback)(Element* this, int step, void* context);


int Element_walk( Element* this, ElementWalkingCallback callback, void* context);


int Element__walk( Element* this, ElementWalkingCallback callback, int step, void* context);
typedef struct Match {

 char status;
 size_t offset;
 size_t length;
 size_t line;
 Element* element;
 void* data;
 struct Match* next;
 struct Match* children;
 struct Match* parent;
 void* result;
} Match;
typedef int (*MatchWalkingCallback)(Match* this, int step, void* context);



extern Match FAILURE_S;


extern Match* FAILURE;



Match* Match_Success(size_t length, ParsingElement* element, ParsingContext* context);

Match* Match_SuccessFromReference(size_t length, Reference* element, ParsingContext* context);


Match* Match_new(void);





void* Match_free(Match* this);


void* Match_fail(Match* this);


bool Match_isSuccess(const Match* this);


bool Match_hasNext(const Match* this);


Match* Match_getNext(Match* this);


bool Match_hasChildren(const Match* this);


Match* Match_getChildren(Match* this);


int Match_getOffset(const Match* this);


int Match_getLength(const Match* this);


int Match_getEndOffset(const Match* this);





ParsingElement* Match_getParsingElement(Match* this);


int Match_getElementID(Match* this);


char Match_getType(Match* this);





char Match_getElementType(Match* this);


const char* Match_getElementName(Match* this);





int Match__walk(Match* this, MatchWalkingCallback callback, int step, void* context );


int Match_countAll(Match* this);


int Match_countChildren(Match* this);



void Match__writeJSON(Match* match, int fd, int flags);


void Match_writeJSON(Match* this, int fd);


void Match_printJSON(Match* this);



void Match__writeXML(Match* match, int fd, int flags);


void Match_writeXML(Match* this, int fd);


void Match_printXML(Match* this);


typedef struct ParsingElement {
 char type;
 int id;
 char* name;
 void* config;
 struct Reference* children;
 struct Match* (*recognize) (struct ParsingElement*, ParsingContext*);
 struct Match* (*process) (struct ParsingElement*, ParsingContext*, Match*);
 void (*freeMatch) (Match*);
} ParsingElement;



bool ParsingElement_Is(void* this);





ParsingElement* ParsingElement_new(Reference* children[]);


void ParsingElement_freeChildren(ParsingElement* this);


void ParsingElement_free(ParsingElement* this);

ParsingElement* ParsingElement_Ensure(void* referenceOfElement);


ParsingElement* ParsingElement_insert(ParsingElement* this, int index, Reference* child);


ParsingElement* ParsingElement_replace(ParsingElement* this, int index, Reference* child);




ParsingElement* ParsingElement_add(ParsingElement* this, Reference* child);


ParsingElement* ParsingElement_clear(ParsingElement* this);




size_t ParsingElement_skip(const ParsingElement* this, ParsingContext* context);



size_t ParsingElement_skipFast(const ParsingElement* this, ParsingContext* context);





Match* ParsingElement_process( const ParsingElement* this, Match* match );




ParsingElement* ParsingElement_name( ParsingElement* this, const char* name );


const char* ParsingElement_getName( const ParsingElement* this );


int ParsingElement_walk( ParsingElement* this, ElementWalkingCallback callback, void* context);


int ParsingElement__walk( ParsingElement* this, ElementWalkingCallback callback, int step, void* context);
typedef struct WordConfig {
 char* word;
 size_t length;
} WordConfig;


ParsingElement* Word_new(const char* word);


void Word_free(ParsingElement* this);



Match* Word_recognize(ParsingElement* this, ParsingContext* context);


const char* Word_word(ParsingElement* this);


const char* WordMatch_group(Match* match);
typedef int (*TokenCustomRecognize)(const char* input, int available, int* ovector, int* out_count);




typedef struct TokenConfig {
 char* expr;
 const char* literal;
 int literalLen;
 TokenCustomRecognize customRecognize;




} TokenConfig;
typedef struct TokenPattern {
 char type;
 char quantifier;
 union {
  unsigned char bitmap[32];
  struct {
   struct TokenPattern** children;
   int childCount;
  };
  struct {
   const char* literal;
   int literalLen;
  };
 };
} TokenPattern;



typedef struct RangeTokenConfig {
 TokenPattern* pattern;
 char* expr;
 TokenCustomRecognize customRecognize;
} RangeTokenConfig;


typedef struct TokenMatch {
 int count;
 const char** groups;
 int* ovector;
 const char* input;
 bool extracted;
} TokenMatch;





ParsingElement* Token_new(const char* expr);


void Token_free(ParsingElement*);



void Token_setCustomRecognize(ParsingElement* this, TokenCustomRecognize recognizer);



int Token_recognizeJSONString(const char* input, int available, int* ovector, int* out_count);



int Token_recognizeJSONNumber(const char* input, int available, int* ovector, int* out_count);



Match* Token_recognize(ParsingElement* this, ParsingContext* context);


const char* Token_expr(ParsingElement* this);



void TokenMatch_free(Match* match);


const char* TokenMatch_group(Match* match, int index);


int TokenMatch_count(Match* match);
TokenPattern* tp_char(char c);



TokenPattern* tp_range(char lo, char hi);




TokenPattern* tp_set(const char* chars);



TokenPattern* tp_not_set(const char* chars);



TokenPattern* tp_any(void);



TokenPattern* tp_digit(void);



TokenPattern* tp_alpha(void);



TokenPattern* tp_word(void);



TokenPattern* tp_space(void);






TokenPattern* tp_seq(TokenPattern* children[]);




TokenPattern* tp_alt(TokenPattern* children[]);





TokenPattern* tp_many(TokenPattern* p);



TokenPattern* tp_optional(TokenPattern* p);



TokenPattern* tp_many_optional(TokenPattern* p);





TokenPattern* tp_literal(const char* str);





void TokenPattern_free(TokenPattern* this);






int TokenPattern_match(const TokenPattern* pattern, const char* input, int available);






ParsingElement* RangeToken_new(TokenPattern* pattern);


void RangeToken_free(ParsingElement* this);



Match* RangeToken_recognize(ParsingElement* this, ParsingContext* context);



void RangeToken_setCustomRecognize(ParsingElement* this, TokenCustomRecognize recognizer);
typedef struct Reference {
 char type;
 int id;
 char* name;
 char cardinality;
 struct ParsingElement* element;
 struct Reference* next;
} Reference;
bool Reference_Is(void* this);




bool Reference_IsMany(void* this);



Reference* Reference_Ensure(void* elementOrReference);



Reference* Reference_FromElement(ParsingElement* element);



Reference* Reference_new(void);


void Reference_free(Reference* this);



Reference* Reference_cardinality(Reference* this, char cardinality);


Reference* Reference_name(Reference* this, const char* name);


bool Reference_hasNext(const Reference* this);


bool Reference_hasElement(const Reference* this);


bool Reference_isMany(const Reference* this);


int Reference__walk( Reference* this, ElementWalkingCallback callback, int step, void* nothing );






Match* Reference_recognize(Reference* this, ParsingContext* context);
ParsingElement* Group_new(Reference* children[]);


Match* Group_recognize(ParsingElement* this, ParsingContext* context);
ParsingElement* Rule_new(Reference* children[]);


Match* Rule_recognize(ParsingElement* this, ParsingContext* context);
typedef void (*ProcedureCallback)(ParsingElement* this, ParsingContext* context);


typedef void (*MatchCallback)(Match* m);


ParsingElement* Procedure_new(ProcedureCallback c);


Match* Procedure_recognize(ParsingElement* this, ParsingContext* context);
typedef bool (*ConditionCallback)(ParsingElement*, ParsingContext*);


ParsingElement* Condition_new(ConditionCallback c);


Match* Condition_recognize(ParsingElement* this, ParsingContext* context);
typedef struct ArenaBlock {
 struct ArenaBlock* next;
 size_t used;
 size_t capacity;
 char data[];
} ArenaBlock;


typedef struct Arena {
 ArenaBlock* current;
 ArenaBlock* first;
} Arena;


Arena* Arena_new(void);



void* Arena_alloc(Arena* arena, size_t size);



void Arena_free(Arena* arena);
typedef struct MemoEntry {
 char status;
 Match* match;
 size_t end_offset;
 size_t end_lines;
} MemoEntry;


typedef struct ParsingStats {
 size_t bytesRead;
 double parseTime;
 size_t symbolsCount;
 size_t* successBySymbol;
 size_t* failureBySymbol;
 size_t failureOffset;
 size_t matchOffset;
 size_t matchLength;
 Element* failureElement;
} ParsingStats;


ParsingStats* ParsingStats_new(void);


void ParsingStats_free(ParsingStats* this);


void ParsingStats_setSymbolsCount(ParsingStats* this, size_t t);
typedef struct ParsingVariable {
 int depth;
 char* key;
 void* value;
 struct ParsingVariable* previous;
} ParsingVariable;


ParsingVariable* ParsingVariable_new(int depth, const char* key, void* value);


void ParsingVariable_free(ParsingVariable* this);


void ParsingVariable_freeAll(ParsingVariable* this);


bool ParsingVariable_is(const ParsingVariable* this, const char* key);


ParsingVariable* ParsingVariable_set(ParsingVariable* this, const char* name, void* value);


void* ParsingVariable_get(ParsingVariable* this, const char* name);


ParsingVariable* ParsingVariable_find(ParsingVariable* this, const char* key, bool local);


int ParsingVariable_getDepth(ParsingVariable* this);


const char* ParsingVariable_getName(const ParsingVariable* this);


int ParsingVariable_count(ParsingVariable* this);
typedef void (*ContextCallback)(ParsingContext* context, char op );


typedef struct ParsingContext {
 struct Grammar* grammar;
 struct Iterator* iterator;
 struct ParsingStats* stats;
 struct ParsingVariable* variables;
 size_t lastMatchOffset;
 size_t lastMatchLength;
 int lastMatchElementID;
 ContextCallback callback;
 int depth;
 const char* indent;
 int flags;
 bool freeIterator;
 Arena* arena;
 MemoEntry* memoTable;
 size_t memoCapacity;
 size_t inputLength;
} ParsingContext;






ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator );


char* ParsingContext_text( ParsingContext* this );



char ParsingContext_charAt ( ParsingContext* this, size_t offset );


size_t ParsingContext_getOffset( ParsingContext* this );


void ParsingContext_free( ParsingContext* this );



void ParsingContext_push ( ParsingContext* this );




void ParsingContext_pop ( ParsingContext* this );



void* ParsingContext_get(ParsingContext* this, const char* name);


intptr_t ParsingContext_getInt(ParsingContext* this, const char* name);


void ParsingContext_set(ParsingContext* this, const char* name, void* value);


void ParsingContext_setInt(ParsingContext* this, const char* name, int value);


void ParsingContext_on(ParsingContext* this, ContextCallback callback);


int ParsingContext_getVariableCount(ParsingContext* this);




Match* ParsingContext_registerMatch(ParsingContext* this, Element* e, Match* m);



Match* ParsingContext_memoGet(ParsingContext* this, int elementId, size_t offset);



void ParsingContext_memoSet(ParsingContext* this, int elementId, size_t offset, Match* match, size_t endOffset, size_t endLines);


typedef struct ParsingResult {
 char status;
 Match* match;
 ParsingContext* context;
} ParsingResult;


ParsingResult* ParsingResult_new(Match* match, ParsingContext* context);



void ParsingResult_free(ParsingResult* this);


bool ParsingResult_isSuccess(const ParsingResult* this);


bool ParsingResult_isFailure(const ParsingResult* this);


bool ParsingResult_isPartial(const ParsingResult* this);


char* ParsingResult_text(ParsingResult* this);


int ParsingResult_textOffset(ParsingResult* this);


size_t ParsingResult_remaining(ParsingResult* this);






typedef struct Processor Processor;


typedef void (*ProcessorCallback)(Processor* processor, Match* match);

typedef struct Processor {
 ProcessorCallback fallback;
 ProcessorCallback* callbacks;
 int callbacksCount;
} Processor;



Processor* Processor_new(void);


void Processor_free(Processor* this);


void Processor_register (Processor* this, int symbolID, ProcessorCallback callback) ;


int Processor_process (Processor* this, Match* match, int step);







void Utilities_indent( ParsingElement* this, ParsingContext* context );


void Utilities_dedent( ParsingElement* this, ParsingContext* context );


bool Utilites_checkIndent( ParsingElement* this, ParsingContext* context );
typedef struct MatchFlatNode {
    char type;
    int id;
    int numChildren;
    char isMany;
    const char* wordValue;
    Match* match;
} MatchFlatNode;





int Match_flatten(Match* this, MatchFlatNode* buffer, int bufferSize);






typedef struct MatchPostNode {
    char type;
    int id;
    int numChildren;
    const char* wordValue;
    Match* match;
} MatchPostNode;







int Match_flattenPost(Match* this, MatchPostNode* buffer, int bufferSize);






int Match_flattenPostArrays(Match* this, char* types, int* ids, int* nchildren,
                            const char** words, Match** matches, int bufferSize);







int Match_flattenPostArraysEx(Match* this, char* types, int* ids, int* nchildren,
                              const char** words, Match** matches,
                              const char* action_codes, int max_id,
                              char* strbuf, int strbufSize,
                              int* out_strbuf_used,
                              int bufferSize);
typedef struct gc_Reference {
 char guard;
 size_t size;
 int count;
 void* previous;
 void* next;
} gc_Reference;
void* gc_Reference_data( gc_Reference* ref );

void gc_Reference_acquire( gc_Reference* ref );

gc_Reference* gc_Reference_release( gc_Reference* ref );

void gc_Reference_free( gc_Reference* ref );
gc_Reference* gc_ref( void* ptr );






void* gc_new( size_t size );





void gc_free( void* ptr );



void* gc_realloc( void* ptr, size_t size );

char* gc_strdup(const char* s);

void* gc_calloc(size_t count, size_t size);

void gc_acquire( const void* ptr );

void gc_release( const void* ptr );




int Parsing_hasPCRE(void) {



 return 0;

}

int Parsing_hasGC(void) {

 return 1;



}





char EOL = '\n';

Match FAILURE_S = {
 .status = 'F',
 .length = 0,
 .data = NULL,
 .next = NULL
};

Match* FAILURE = &FAILURE_S;







const char* EMPTY = "";
const char* INDENT = "                                                                                ";
char* String_escape(const char* string) {
 const char* p = string;
 int n = 0;
 int l = 0;
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
    res[l + n++] = '\\';
    res[l++ + n] = 'n';
    break;
   case '\t':
    res[l + n++] = '\\';
    res[l++ + n] = 't';
    break;
   case '\r':
    res[l + n++] = '\\';
    res[l++ + n] = 'r';
    break;
   case '"':
    res[l + n++] = '\\';
    res[l++ + n] = '"';
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
Arena* Arena_new(void) {
 Arena* arena = (Arena*)malloc(sizeof(Arena));
 assert(arena != NULL);
 ArenaBlock* block = (ArenaBlock*)malloc(sizeof(ArenaBlock) + (64 * 1024));
 assert(block != NULL);
 block->next = NULL;
 block->used = 0;
 block->capacity = (64 * 1024);
 arena->current = block;
 arena->first = block;
 return arena;
}

void* Arena_alloc(Arena* arena, size_t size) {

 size = (size + 7) & ~((size_t)7);
 ArenaBlock* block = arena->current;
 if (block->used + size > block->capacity) {
  size_t cap = (64 * 1024) > size ? (64 * 1024) : size;
  ArenaBlock* new_block = (ArenaBlock*)malloc(sizeof(ArenaBlock) + cap);
  assert(new_block != NULL);
  new_block->next = NULL;
  new_block->used = 0;
  new_block->capacity = cap;
  block->next = new_block;
  arena->current = new_block;
  block = new_block;
 }
 void* ptr = block->data + block->used;
 block->used += size;
 return ptr;
}

void Arena_free(Arena* arena) {
 if (arena == NULL) {return;}
 ArenaBlock* block = arena->first;
 while (block != NULL) {
  ArenaBlock* next = block->next;
  free(block);
  block = next;
 }
 free(arena);
}







Iterator* Iterator_Open(const char* path) {
 Iterator* result = Iterator_new();
 result->freeBuffer = 1;
 if (Iterator_open(result, path)) {
  return result;
 } else {
  Iterator_free(result);
  return NULL;
 }
}

Iterator* Iterator_FromString(const char* text) {
 Iterator* this = Iterator_new();
 if (this!=NULL) {
  this->buffer = (char*)text;
  this->current = (char*)text;
  this->capacity = strlen(text);
  this->available = this->capacity;
  this->move = String_move;
 }
 return this;
}

Iterator* Iterator_new( void ) {
 Iterator* this = (Iterator*) gc_new(sizeof(Iterator)); assert (this!=NULL); ;
 this->status = '-';
 this->separator = EOL;
 this->buffer = NULL;
 this->current = NULL;
 this->offset = 0;
 this->lines = 0;
 this->available = 0;
 this->capacity = 0;
 this->input = NULL;
 this->freeInput = NULL;
 this->move = NULL;
 this->freeBuffer = 0;
 return this;
}

void Iterator__freeInput( Iterator* this ) {
 if (this->freeInput != NULL && this->input != NULL) {
  this->freeInput(this->input);
 }
 this->freeInput = NULL;
 this->input = NULL;
}

void Iterator_free( Iterator* this ) {
 ;
 if (this != NULL) {
  Iterator__freeInput(this);
 }
 if (this->freeBuffer) {
  if (this->buffer!=NULL) {; gc_free(this->buffer); } ;
 }
 if (this!=NULL) {; gc_free(this); } ;
}

bool Iterator_open( Iterator* this, const char *path ) {
 FileInput* input = FileInput_new(path);
 assert(this->status == '-');
 Iterator__freeInput(this);
 if (input!=NULL) {
  this->input = (void*)input;
  this->freeInput = FileInput_free;
  this->status = '~';
  this->offset = 0;



  assert(this->buffer == NULL);

  this->capacity = sizeof(char) * 64000 * 2;
  char* new_buffer = (char*) gc_calloc(this->capacity + 1, sizeof(char)) ; assert (new_buffer!=NULL);
  this->buffer = new_buffer;
  assert(this->buffer != NULL);
  this->current = (char*)this->buffer;


  ((char*)this->buffer)[this->capacity] = '\0';
  assert(strlen(((char*)this->buffer)) == 0);
  FileInput_preload(this);
  ;;
  this->move = FileInput_move;
  if (input->file==NULL) {printf("[!] %s\n", strerror(errno));};
  return 1;
 } else {
  return 0;
 }
}

bool Iterator_hasMore( Iterator* this ) {
 size_t remaining = Iterator_remaining(this);


 return remaining > 0;
}

size_t Iterator_remaining( Iterator* this ) {
 int buffer_offset = ((char*)this->current - this->buffer);

 int remaining = this->available - buffer_offset;
 assert(remaining >= 0);

 return (size_t)remaining;
}

bool Iterator_moveTo ( Iterator* this, size_t offset ) {
 return this->move(this, offset - this->offset );
}

bool Iterator_backtrack ( Iterator* this, size_t offset, size_t lines ) {
 assert(offset <= this->offset);
 assert(lines <= this->lines);
 this->lines = lines;
 return this->move(this, offset - this->offset );
}

char Iterator_charAt ( Iterator* this, size_t offset ) {
 assert(this->offset == (this->current - this->buffer));
 assert(offset <= this->available);
 return (char)(this->buffer[offset]);
}
bool String_move ( Iterator* this, int n ) {
 assert(this->capacity == this->available);
 if ( n == 0) {


  ;;
  return 1;
 } else if ( n >= 0 ) {



  size_t left = this->available - this->offset;


  size_t c = n <= left ? n : left;

  while (c > 0) {
   this->current++;
   this->offset++;
   if (*(this->current) == this->separator) {this->lines++;}
   c--;
  }

  left = this->available - this->offset;

  if (left == 0) {


   this->status = 'E';
   return 0;
  } else {

   return 1;
  }
 } else {


  n = (n > 0 - this->offset ? n : 0 - this->offset);


  this->current = (((char*)this->current) + n);
  this->offset += n;
  if (n!=0) {
   this->status = '~';
  }
  assert(Iterator_remaining(this) >= 0 - n);
  ;;
  return 1;
 }
}







FileInput* FileInput_new(const char* path ) {
 FileInput* this = (FileInput*) gc_new(sizeof(FileInput)); assert (this!=NULL); ;
 assert(this != NULL);

 this->path = path;
 this->file = fopen(path, "r");
 if (this->file==NULL) {
  fprintf(stderr, "ERR ");fprintf(stderr, "Cannot open file: %s", path);fprintf(stderr, "\n");;
  if (this!=NULL) {; gc_free(this); } ;
  return NULL;
 } else {
  return this;
 }
}

void FileInput_free(void* this) {
 ;
 FileInput* self = (FileInput*) this;
 if (self != NULL && self->file != NULL) { fclose(self->file); }
 if (this!=NULL) {; gc_free(this); } ;
}

size_t FileInput_preload( Iterator* this ) {


 FileInput* input = (FileInput*)this->input;
 size_t read = this->current - this->buffer;
 size_t left = this->available - read;
 size_t until_eob = this->capacity - read;
 ;;
 assert (left < this->capacity);




 if ( (this->available == 0 || until_eob < 64000) && this->status != '.') {



  size_t delta = this->current - this->buffer;

  this->capacity += 64000;

  assert(this->capacity + 1 > 0);
  ;


  this->buffer=gc_realloc(this->buffer,this->capacity + 1); ;
  assert(this->buffer != NULL);

  this->current = this->buffer + delta;

  this->buffer[this->capacity] = '\0';

  size_t to_read = this->capacity - left;
  size_t bytes_read = fread((char*)this->buffer + this->available, sizeof(char), to_read, input->file);
  this->available += bytes_read;
  left += bytes_read;
  ;;
  assert(Iterator_remaining(this) == left);
  assert(Iterator_remaining(this) >= bytes_read);
  if (bytes_read == 0) {
    ;;
   this->status = '.';
  }
 }
 return left;
}

bool FileInput_move ( Iterator* this, int n ) {
 if ( n == 0) {

  return 1;
 } else if ( n >= 0 ) {


  size_t left = FileInput_preload(this);
  if (left > 0) {
   int c = n > left ? left : n;


   while (c > 0) {
    this->current++;
    this->offset++;
    if (*(this->current) == this->separator) {this->lines++;}
    c--;
   }
   ;;
   if (n>left) {
    this->status = '.';
    return 0;
   } else {
    return 1;
   }
  } else {
   ;;
   assert (this->status == '.' || this->status == 'E');
   this->status = 'E';
   return 0;
  }
 } else {


 

  int buffer_pos = (int)(this->current - this->buffer);
  n = buffer_pos + n < 0 ? -buffer_pos : n;
  this->current = (((char*)this->current) + n);
  this->offset += n;
  if (n!=0) {this->status = '~';}
  ;;
  assert(Iterator_remaining(this) >= 0 - n);
  return 1;
 }
}







Grammar* Grammar_new(void) {
 Grammar* this = (Grammar*) gc_new(sizeof(Grammar)); assert (this!=NULL); ;
 this->axiom = NULL;
 this->skip = NULL;
 this->axiomCount = 0;
 this->skipCount = 0;
 this->elements = NULL;
 this->isVerbose = 0;
 this->noMemo = 0;
 this->skipWhitespace = 0;
 return this;
}

void Grammar_setVerbose ( Grammar* this ) {
 this->isVerbose = 1;
}

void Grammar_setNoMemo ( Grammar* this ) {
 this->noMemo = 1;
}

void Grammar_setSilent ( Grammar* this ) {
 this->isVerbose = 0;
}

int Grammar_symbolsCount(const Grammar* this) {
 return this->axiomCount + this->skipCount;
}

void Grammar_freeElements(Grammar* this) {
 if (this->elements == NULL) {
  Grammar_prepare(this);
 }
 int count = (this->axiomCount + this->skipCount);
 if (this->elements != NULL) {

  for (int i = 0; i < count + 1 ; i++ ) {
   Element* element = this->elements[i];
   if (element == NULL) {
    ;;
   } else if (ParsingElement_Is(element)) {
    ParsingElement* e = (ParsingElement*)element;
    ;
    ParsingElement_free(e);
   } else {
    Reference* r = (Reference*)element;
    ;
    Reference_free(r);
   }
  }
 }
 this->axiomCount = 0;
 this->skipCount = 0;
 this->skip = NULL;
 this->axiom = NULL;
 if (this->elements!=NULL) {; gc_free(this->elements); } ;
 this->elements = NULL;
}

void Grammar_free(Grammar* this) {
 Grammar_freeElements(this);
 if (this!=NULL) {; gc_free(this); } ;
}







Match* Match__Success(size_t length, Element* element, ParsingContext* context) {

 Match* this = (Match*)Arena_alloc(context->arena, sizeof(Match));
 assert( element != NULL );
 this->status = 'M';
 this->offset = context->iterator->offset;
 this->length = length;

 this->line = context->iterator->lines;
 this->element = (Element*)element;
 this->data = NULL;
 this->next = NULL;
 this->children = NULL;
 this->parent = NULL;
 this->result = NULL;
 return this;
}

Match* Match_Success(size_t length, ParsingElement* element, ParsingContext* context) {
 return Match__Success(length, (Element*)element, context);
}

Match* Match_SuccessFromReference(size_t length, Reference* element, ParsingContext* context) {
 return Match__Success(length, (Element*)element, context);
}

Match* Match_new(void) {
 Match* this = (Match*) gc_new(sizeof(Match)); assert (this!=NULL); ;

 this->status = '-';
 this->offset = 0;
 this->length = 0;
 this->line = 0;
 this->element = NULL;
 this->data = NULL;
 this->next = NULL;
 this->children = NULL;
 this->parent = NULL;
 this->result = NULL;
 return this;
}

inline void Match_free__specialized(Match* this, const ParsingElement* element) {
 assert(ParsingElement_Is(this->element));
 if (element!=NULL && this!=NULL){
  switch (element->type) {
   case 'T':
    TokenMatch_free(this);
    break;
  }
 }
}



void* Match_free(Match* this) {
 if (this!=NULL && this!=FAILURE) {
  ;


  assert(this->children != this);
  Match_free(this->children);
  this->children = NULL;


  assert(this->next != this);
  Match_free(this->next);
  this->next = NULL;


  if (ParsingElement_Is(this->element)) {
   ParsingElement* element = ((ParsingElement*)this->element);
   Match_free__specialized(this,element);
  } else {
   assert(Reference_Is(this->element));
   ParsingElement* element = ((Reference*)this->element)->element;
   Match_free__specialized(this,element);
  }


 }
 return NULL;
}


void* Match_fail( Match* this ) {
 Match_free(this);
 return FAILURE;
}

ParsingElement* Match_getParsingElement( Match* this ) {
 return ParsingElement_Ensure(this->element);
}

int Match_getElementID(Match* this) {
 if (this == NULL || this->element == NULL) {return -1;}
 if (((ParsingElement*)this->element)->type == '#') {
  return ((Reference*)this->element)->id;
 } else {
  ParsingElement* element = ParsingElement_Ensure(this->element);
  return element->id;
 }
}

char Match_getType(Match* this) {
 if (this == NULL || this->element == NULL) {return ' ';}
 else {return this->element->type;}
}

char Match_getElementType(Match* this) {
 if (this == NULL || this->element == NULL) {return ' ';}
 if (((ParsingElement*)this->element)->type == '#') {
  return ((Reference*)this->element)->element->type;
 } else {
  ParsingElement* element = ParsingElement_Ensure(this->element);
  return element->type;
 }
}

const char* Match_getElementName(Match* this) {
 if (this == NULL || this->element == NULL) {return NULL;}
 if (((ParsingElement*)this->element)->type == '#') {
  return ((Reference*)this->element)->name;
 } else {
  ParsingElement* element = ParsingElement_Ensure(this->element);
  return element->name;
 }
}

int Match_getOffset(const Match* this) {
 if (this == NULL) {return -1;}
 return (int)this->offset;
}

int Match_getLength(const Match* this) {
 if (this == NULL) {return 0;}
 return (int)this->length;
}

int Match_getEndOffset(const Match* this) {
 if (this == NULL) {return -1;}
 return (int)(this->length + this->offset);
}

bool Match_isSuccess(const Match* this) {
 return (this != NULL && this != FAILURE && this->status == 'M');
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


bool Match_hasNext(const Match* this) {
 return this != NULL && this->next != NULL;
}

Match* Match_getNext(Match* this) {
 return this != NULL ? this->next : NULL;
}

bool Match_hasChildren(const Match* this) {
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
void Match__childrenWriteJSON(Match* match, int fd, int flags) {
 int count = 0 ;
 Match* child = match->children;
 while (child != NULL) {
  ParsingElement* element = ParsingElement_Ensure(child->element);
  if (element->type != 'p' && element->type != 'c') {
   count += 1;
  }
  child = child->next;
 }
 child = match->children;
 int i = 0;
 while (child != NULL) {
  ParsingElement* element = ParsingElement_Ensure(child->element);
  if (element->type != 'p' && element->type != 'c') {
   Match__writeJSON(child, fd, flags);
   if ( (i+1) < count ) {
    dprintf(fd,"%s",",");
   }
   i += 1;
  }
  child = child->next;
 }
}

void Match__writeJSON(Match* match, int fd, int flags) {
 if (match == NULL || match->element == NULL) {
  dprintf(fd,"%s","null");
  return;
 }

 ParsingElement* element = (ParsingElement*)match->element;

 if (element->type == '#') {
  Reference* ref = (Reference*)match->element;
  if (ref->cardinality == '1' || ref->cardinality == '=' || ref->cardinality == '?') {
   Match__writeJSON(match->children, fd, flags);
  } else {
   dprintf(fd,"%s","[");
   Match__childrenWriteJSON(match, fd, flags);
   dprintf(fd,"%s","]");
  }
 }
 else if (element->type != '#') {
  int i = 0;
  int count = 0;
  char* word = NULL;
  switch(element->type) {
   case 'W':
    word = String_escape(Word_word(element));
    if (element->name) {dprintf(fd,"%s","{\"name\":\"");dprintf(fd,"%s",element->name);dprintf(fd,"%s","\"");} else {dprintf(fd,"%s","{\"id\":");dprintf(fd,"%d",element->id);};
    dprintf(fd,"%s",",\"value\":\"");dprintf(fd,"%s",word);dprintf(fd,"%s","\"");
    dprintf(fd,"%s","}");
    free(word);
    break;
   case 'T':
    count = TokenMatch_count(match);
    if (count == 0) {
     if (element->name) {dprintf(fd,"%s","{\"name\":\"");dprintf(fd,"%s",element->name);dprintf(fd,"%s","\"");} else {dprintf(fd,"%s","{\"id\":");dprintf(fd,"%d",element->id);};
     dprintf(fd,"%s","}");
    } else if (count == 1) {
     if (element->name) {dprintf(fd,"%s","{\"name\":\"");dprintf(fd,"%s",element->name);dprintf(fd,"%s","\"");} else {dprintf(fd,"%s","{\"id\":");dprintf(fd,"%d",element->id);};
     word = String_escape(TokenMatch_group(match, 0));
     dprintf(fd,"%s",",\"value\":\"");dprintf(fd,"%s",word);dprintf(fd,"%s","\"");
     free(word);
     dprintf(fd,"%s","}");
    } else {
     if (element->name) {dprintf(fd,"%s","{\"name\":\"");dprintf(fd,"%s",element->name);dprintf(fd,"%s","\"");} else {dprintf(fd,"%s","{\"id\":");dprintf(fd,"%d",element->id);};
     dprintf(fd,"%s",",\"content\":[");
     for (i=0 ; i < count ; i++) {
      word = String_escape(TokenMatch_group(match, i));
      dprintf(fd,"%s","\"");dprintf(fd,"%s",word);dprintf(fd,"%s","\"");
      if (i+1 < count) {dprintf(fd,"%s",",");}
      free(word);
     }
     dprintf(fd,"%s","]");
     dprintf(fd,"%s","}");
    }
    break;
   case 'G':
   case 'R':
    if (match->children == NULL) {
     if (element->name) {dprintf(fd,"%s","{\"name\":\"");dprintf(fd,"%s",element->name);dprintf(fd,"%s","\"");} else {dprintf(fd,"%s","{\"id\":");dprintf(fd,"%d",element->id);};
     dprintf(fd,"%s","}");
    } else {
     if (element->name) {dprintf(fd,"%s","{\"name\":\"");dprintf(fd,"%s",element->name);dprintf(fd,"%s","\"");} else {dprintf(fd,"%s","{\"id\":");dprintf(fd,"%d",element->id);};
     dprintf(fd,"%s",",\"content\":[");
     Match__childrenWriteJSON(match, fd, flags);
     dprintf(fd,"%s","]");
     dprintf(fd,"%s","}");
    }
    break;
   case 'p':
    break;
   case 'c':
    break;
   default:
    dprintf(fd,"\"ERROR:undefined element type=%c\"",element->type);
  }
 }
}

void Match_writeJSON(Match* this, int fd) {
 Match__writeJSON(this, fd, 0);
}


void Match_printJSON(Match* this) {
 return Match_writeJSON(this, 1);
}
void Match__childrenWriteXML(Match* match, int fd, int flags) {
 int count = 0 ;
 Match* child = match->children;
 while (child != NULL) {
  ParsingElement* element = ParsingElement_Ensure(child->element);
  if (element->type != 'p' && element->type != 'c') {
   count += 1;
  }
  child = child->next;
 }
 child = match->children;
 int i = 0;
 while (child != NULL) {
  ParsingElement* element = ParsingElement_Ensure(child->element);
  if (element->type != 'p' && element->type != 'c') {
   Match__writeXML(child, fd, flags);
   i += 1;
  }
  child = child->next;
 }
}

void Match__writeXML(Match* match, int fd, int flags) {
 if (match == NULL || match->element == NULL) {
  return;
 }
 ParsingElement* element = (ParsingElement*)match->element;

 if (element->type == '#') {
  Reference* ref = (Reference*)match->element;
  if (ref->cardinality == '1' || ref->cardinality == '=' || ref->cardinality == '?') {
   Match__writeXML(match->children, fd, flags);
  } else {
   Match__childrenWriteXML(match, fd, flags);
  }
 }

 else if (element->type != '#') {
  int i = 0;
  int count = 0;
  switch(element->type) {
   case 'W':
    if (element->name != NULL) {
     dprintf(fd,"%s","<");
     if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);};
     dprintf(fd,"%s","/>");
    } else {


    }
    break;
   case 'T':
    count = TokenMatch_count(match);
    if (count == 0) {
     if (element->name != NULL) {
      dprintf(fd,"%s","<");
      if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);};
      dprintf(fd,"%s","/>");
     }
    } else if (count == 1) {
     if (element->name != NULL) {
      dprintf(fd,"%s","<");
      if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);};
      dprintf(fd,"%s"," t=\"");
      dprintf(fd,"%s",TokenMatch_group(match, i));
      dprintf(fd,"%s","\"/>");
     } else {
      dprintf(fd,"%s",TokenMatch_group(match, i));
     }
    } else {
     if (element->name != NULL) {
      if (element->name != NULL) {dprintf(fd,"%s","<") ; if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);} ; dprintf(fd,"%s",">");};
      for (i=0 ; i < count ; i++) {
       dprintf(fd,"%s","<g t=\"");
       dprintf(fd,"%s",TokenMatch_group(match, i));
       dprintf(fd,"%s","\"/>");
      }
      if (element->name != NULL) {dprintf(fd,"%s","</") ; if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);} ; dprintf(fd,"%s",">");};
     } else {

     }
    }
    break;
   case 'G':
    if (match->children == NULL) {

    } else {
     if (element->name != NULL) {
      if (element->name != NULL) {dprintf(fd,"%s","<") ; if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);} ; dprintf(fd,"%s",">");};
      Match__writeXML(match->children, fd, flags);
      if (element->name != NULL) {dprintf(fd,"%s","</") ; if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);} ; dprintf(fd,"%s",">");};
     } else {
      Match__writeXML(match->children, fd, flags);
     }
    }
    break;
   case 'R':
    if (match->children == NULL) {
    } else {
     if (element->name != NULL) {
      if (element->name != NULL) {dprintf(fd,"%s","<") ; if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);} ; dprintf(fd,"%s",">");};
      Match__childrenWriteXML(match, fd, flags);
      if (element->name != NULL) {dprintf(fd,"%s","</") ; if (element->name != NULL) { dprintf(fd,"%s",element->name); } else {dprintf(fd,"E%d",element->id);} ; dprintf(fd,"%s",">");};
     } else {
      Match__childrenWriteXML(match, fd, flags);
     }
    }
    break;
   case 'p':
    break;
   case 'c':
    break;
   default:
    dprintf(fd,"<error value=\"Undefined element type\" type=\"%c\" />",element->type);
 }
 }
}

void Match_printXML(Match* this) {
 Match_writeXML(this, 1);
}

void Match_writeXML(Match* this, int fd ) {
 dprintf(fd,"%s","<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\" ?>\n");
 Match__writeXML(this, fd, 0);
}







bool ParsingElement_Is(void *this) {
 if (this == NULL) { return 0; }
 switch (((ParsingElement*)this)->type) {

  case 'E':
  case 'W':
  case 'T':
  case 'G':
  case 'R':
  case 'c':
  case 'p':
   return 1;
  default:
   return 0;
 }
}

ParsingElement* ParsingElement_Ensure(void* elementOrReference) {
 void * element = elementOrReference;
 assert(element!=NULL);
 assert(Reference_Is(element) || ParsingElement_Is(element));
 return Reference_Is(element) ? ((Reference*)element)->element : (ParsingElement*)element;
}

ParsingElement* ParsingElement_new(Reference* children[]) {
 ParsingElement* this = (ParsingElement*) gc_new(sizeof(ParsingElement)); assert (this!=NULL); ;
 this->type = 'E';
 this->id = -10;
 this->name = NULL;
 this->config = NULL;
 this->children = NULL;
 this->recognize = NULL;
 this->process = NULL;
 if (children != NULL && *children != NULL) {
  Reference* r = Reference_Ensure(*children);
  while ( r != NULL ) {
   ;

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


 if (this == NULL) {return;}
 switch (this->type) {
  case 'T':

   if (this->recognize == RangeToken_recognize) {
    RangeToken_free(this);
   } else {
    Token_free(this);
   }
   break;
  case 'W':
   Word_free(this);
   break;
  default:
   if (this!=NULL) {if (this->name!=NULL) {; gc_free(this->name); } };
   if (this!=NULL) {; gc_free(this); } ;
 }
}

ParsingElement* ParsingElement_insert(ParsingElement* this, int index, Reference* child) {
 assert(!Reference_hasNext(child));
 assert(child->next == NULL);
 assert(child->element->recognize!=NULL);
 assert(index >= 0);
 if (index == 0) {
  child->next = this->children;
  this->children = child;
 } else {
  Reference* current = this->children;
  Reference* previous = NULL;
  while (current && index > 0) {
   previous = current;
   current = current->next;
   index -= 1;
  }
  assert (index == 0);
  assert (current != NULL);
  assert (previous != NULL);
  previous->next = child;
  child->next = current;
 }
 return this;
}

ParsingElement* ParsingElement_replace(ParsingElement* this, int index, Reference* child) {
 assert(!Reference_hasNext(child));
 assert(child->next == NULL);
 assert(child->element->recognize!=NULL);
 assert(index >= 0);
 if (index == 0) {
  assert (this->children !=NULL );
  child->next = this->children->next;
  Reference_free(this->children);
  this->children = child;
 } else {
  Reference* current = this->children;
  Reference* previous = NULL;
  while (current && index > 0) {
   previous = current;
   current = current->next;
   index -= 1;
  }
  assert (index == 0);
  assert (current != NULL);
  assert (previous != NULL);
  previous->next = child;
  child->next = current->next;
  Reference_free(current);
 }
 return this;
}

ParsingElement* ParsingElement_add(ParsingElement* this, Reference* child) {
 assert(!Reference_hasNext(child));
 assert(child->next == NULL);
 assert(child->element->recognize!=NULL);
 if (this->children) {

  Reference* ref = this->children;
  while (ref->next != NULL) {ref = ref->next;}
  ref->next = child;
 } else {

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

Match* ParsingElement_process( const ParsingElement* this, Match* match ) {
 return match;
}

size_t ParsingElement_skip( const ParsingElement* this, ParsingContext* context) {
 return ParsingElement_skipFast(this, context);
}




size_t ParsingElement_skipFast( const ParsingElement* this, ParsingContext* context) {
 if (this == NULL || context == NULL || context->grammar->skip == NULL || context->flags & 0x1) {return 0;}
 context->flags=context->flags|0x1;;
 ParsingElement* skip = context->grammar->skip;
 size_t offset = context->iterator->offset;
 size_t skipped = 0;



 if (context->grammar->skipWhitespace) {
  const unsigned char* p = (const unsigned char*)context->iterator->current;
  const unsigned char* end = (const unsigned char*)context->iterator->buffer + context->iterator->available;
  while (p < end && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) {
   p++;
  }
  size_t n = p - (const unsigned char*)context->iterator->current;
  if (n > 0) {
   context->iterator->move(context->iterator, n);
   skipped = n;
  }
 }

 else if (skip->type == 'T' && skip->recognize == RangeToken_recognize && skip->config != NULL) {
  RangeTokenConfig* config = (RangeTokenConfig*)skip->config;
  const char* line = (const char*)context->iterator->current;
  int available = (int)(context->iterator->available - (context->iterator->current - context->iterator->buffer));
  int r = TokenPattern_match(config->pattern, line, available);
  if (r > 0) {
   context->iterator->move(context->iterator, r);
   skipped = r;
  }
 }
 else {

  Match* match = skip->recognize(skip, context);
  match = Match_free(match);
  skipped = context->iterator->offset - offset;
 }

 if (skipped > 0) {
  if(context->grammar->isVerbose){fprintf(stdout, " %s   ►►►skipped %zu", context->indent, skipped);fprintf(stdout, "\n");;}
 }
 context->flags = context->flags & ~0x1;
 return skipped;
}

ParsingElement* ParsingElement_name( ParsingElement* this, const char* name ) {
 if (this == NULL) {return this;}
 if (this->name!=NULL) {; gc_free(this->name); } ;
 this->name = gc_strdup(name) ; assert (this->name!=NULL); ;
 return this;
}

const char* ParsingElement_getName( const ParsingElement* this ) {
 return this == NULL ? NULL : (const char*)this->name;
}

int ParsingElement_walk( ParsingElement* this, ElementWalkingCallback callback, void* context ) {
 return ParsingElement__walk(this, callback, 0, context);
}

int ParsingElement__walk( ParsingElement* this, ElementWalkingCallback callback, int step, void* context ) {
 ;;
 int i = step;
 step = callback((Element*)this, step, context);
 Reference* child = this->children;
 while ( child != NULL && step >= 0) {


  assert(Reference_Is(child));
  int j = Reference__walk(child, callback, ++i, context);

  if (j > 0) { step = i = j; }
  else {break;}
  child = child->next;
 }
 return (step > 0) ? step : i;
}







int Element_walk( Element* this, ElementWalkingCallback callback, void* context ) {
 return Element__walk(this, callback, 0, context);
}

int Element__walk( Element* this, ElementWalkingCallback callback, int step, void* context ) {
 assert (callback != NULL);
 ;;
 if (this!=NULL) {
  if (Reference_Is(this)) {
   step = Reference__walk((Reference*)this, callback, step, context);
  } else if (ParsingElement_Is(this)) {
   step = ParsingElement__walk((ParsingElement*)this, callback, step, context);
  } else {
   assert(0);
  }
 }
 return step;
}







bool Reference_Is(void * this) {
 return this!=NULL && ((Reference*)this)->type == '#';
}

bool Reference_IsMany(void * this) {
 return Reference_Is(this) && (((Reference*)this)->cardinality == '+' || ((Reference*)this)->cardinality == '*');
}

Reference* Reference_Ensure(void* elementOrReference) {
 void * element = elementOrReference;
 assert(element!=NULL);
 assert(Reference_Is(element) || ParsingElement_Is(element));
 return ParsingElement_Is(element) ? Reference_FromElement(element) : element;
}

Reference* Reference_FromElement(ParsingElement* element){
 Reference* this = Reference_new();
 assert(element!=NULL);
 this->element = element;
 this->name = NULL;
 ;
 return this;
}

Reference* Reference_new(void) {
 Reference* this = (Reference*) gc_new(sizeof(Reference)); assert (this!=NULL); ;
 this->type = '#';
 this->id = -10;
 this->cardinality = '1';
 this->name = NULL;
 this->element = NULL;
 this->next = NULL;
 assert(!Reference_hasElement(this));
 assert(!Reference_hasNext(this));

 return this;
}

void Reference_free(Reference* this) {



 if (this != NULL) {if (this->name!=NULL) {; gc_free(this->name); } ;}
 if (this!=NULL) {; gc_free(this); }
}

bool Reference_hasElement(const Reference* this) {
 return this->element != NULL;
}

bool Reference_hasNext(const Reference* this) {
 return this->next != NULL;
}

bool Reference_isMany(const Reference* this) {

 return this != NULL && (this->cardinality == '+' || this->cardinality == '*');
}

Reference* Reference_cardinality(Reference* this, char cardinality) {
 assert(this!=NULL);
 this->cardinality = cardinality;
 return this;
}

Reference* Reference_name(Reference* this, const char* name) {
 assert(this!=NULL);
 if (this->name!=NULL) {; gc_free(this->name); } ;
 this->name = gc_strdup(name) ; assert (this->name!=NULL); ;
 return this;
}

int Reference__walk( Reference* this, ElementWalkingCallback callback, int step, void* context ) {
 ;;
 step = callback((Element*)this, step, context);
 if (step >= 0) {
  assert(!Reference_Is(this->element));
  step = ParsingElement__walk(this->element, callback, step + 1, context);
 }
 return step;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {





 assert(this->element != NULL);
 Match* result = FAILURE;
 Match* tail = NULL;
 int count = 0;
 int offset = context->iterator->offset;
 int match_end_offset = offset;
 size_t match_end_lines = context->iterator->lines;



 assert(this->element->type != 'p' || this->cardinality == '1' || this->cardinality == '?' );


 size_t current_offset = offset;
 while ((Iterator_hasMore(context->iterator) || this->element->type == 'p' || this->element->type == 'c')) {


  ;
  if (this->cardinality != '1' && this->cardinality != '?') {
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "   %s ├┈" "\033[1m\033[33m" "[%d](%c)" "\033[0m", context->indent, count, this->cardinality);fprintf(stdout, "\n");;}

    ;
  }


  int iteration_offset = context->iterator->offset;
  Match* match = this->element->recognize(this->element, context);
  int parsed = context->iterator->offset - iteration_offset;


  if (Match_isSuccess(match)) {
   match_end_offset = Match_getEndOffset(match);

   match_end_lines = context->iterator->lines;
   if (count == 0) {


    assert(result == FAILURE);
    assert(tail == NULL);
    result = match;
    tail = match;
    if (parsed == 0 || this->cardinality == '1' || this->cardinality == '?') {


     count += 1;
     break;
    }
   } else {


    assert(result);
    tail->next = match;
    tail = match;
    if (parsed == 0) {
     break;
    }
   }
   count++;

  } else {

   match = Match_free(match);


   size_t skipped = ParsingElement_skip((ParsingElement*)this, context);

   if (skipped == 0) {
    break;
   }
  }
  if (current_offset == context->iterator->offset) {
   break;
  }
 }





 if (context->iterator->offset != match_end_offset) {

  Iterator_backtrack(context->iterator, match_end_offset, match_end_lines);
 }

 ;;


 bool is_success = Match_isSuccess(result) ? 1 : 0;
 switch (this->cardinality) {
  case '1':
   break;
  case '?':


   is_success = 1;
   break;
  case '+':
   assert(count > 0 || result == FAILURE);
   break;
  case '*':
   assert(count > 0 || result == FAILURE);
   is_success = 1;
   break;
  case '=':
   if (is_success && result->length == 0) {
    result = Match_fail(result);
    return ParsingContext_registerMatch(context, (Element*)this, result);
   }
   break;
  default:

   fprintf(stderr, "ERR ");fprintf(stderr, "Unsupported cardinality %c", this->cardinality);fprintf(stderr, "\n");;
   result = Match_fail(result);
   return ParsingContext_registerMatch(context, (Element*)this, result);
 }



 if (is_success == 1) {




  int length = context->iterator->offset - offset;
  Match* m = Match_SuccessFromReference(length, this, context);

  m->children = result == FAILURE ? NULL : result;
  m->offset = offset;
  assert(m->children == NULL || m->children->element != NULL);

  return ParsingContext_registerMatch(context, (Element*)this, m);
 } else {

  result = Match_fail(result);
  return ParsingContext_registerMatch(context, (Element*)this, FAILURE);
 }
}







ParsingElement* Word_new(const char* word) {
 WordConfig* config = (WordConfig*) gc_new(sizeof(WordConfig)); assert (config!=NULL); ;
 ParsingElement* this = ParsingElement_new(NULL);
 this->type = 'W';
 this->recognize = Word_recognize;
 assert(word != NULL);
 config->length = strlen(word);



 config->word = gc_strdup(word) ; assert (config->word!=NULL); ;
 assert(config->length>0);
 this->config = config;
 assert(this->config != NULL);
 assert(this->recognize != NULL);
 return this;
}


void Word_free(ParsingElement* this) {

 WordConfig* config = (WordConfig*)this->config;
 if (config != NULL) {

  if (config->word!=NULL) {; gc_free(config->word); } ;
  if (config!=NULL) {; gc_free(config); } ;
 }
 if (this!=NULL) {if (this->name!=NULL) {; gc_free(this->name); } };
 if (this!=NULL) {; gc_free(this); } ;
}


const char* Word_word(ParsingElement* this) {
 return ((WordConfig*)this->config)->word;
}

Match* Word_recognize(ParsingElement* this, ParsingContext* context) {
 WordConfig* config = ((WordConfig*)this->config);
 if (strncmp(config->word, context->iterator->current, config->length) == 0) {


  Match* success = ParsingContext_registerMatch(context, (Element*)this, Match_Success(config->length, this, context));
 
  context->iterator->move(context->iterator, config->length);
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ Word %s#%d:`" "\033[36m" "%s" "\033[0m" "` matched %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, ((WordConfig*)this->config)->word, context->iterator->lines, context->iterator->offset - config->length, context->iterator->offset, context->depth);fprintf(stdout, "\n");;};
  return success;
 } else {
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s└ Word %s#%d:" "\033[36m" "`%s`" "\033[0m" " failed at %zu:%zu[→%d]", context->indent, this->name, this->id, ((WordConfig*)this->config)->word, context->iterator->lines, context->iterator->offset, context->depth);fprintf(stdout, "\n");;};
  return ParsingContext_registerMatch(context, (Element*)this, FAILURE);
 }
}

const char* WordMatch_group(Match* match) {
 return ((WordConfig*)((ParsingElement*)match->element)->config)->word;
}

void Word_print(ParsingElement* this) {
 WordConfig* config = (WordConfig*)this->config;
 printf("Word:%c:%s#%d<%s>\n", this->type, this->name != NULL ? this->name : "unnamed", this->id, config->word);
}







ParsingElement* Token_new(const char* expr) {
 TokenConfig* config = (TokenConfig*) gc_new(sizeof(TokenConfig)); assert (config!=NULL); ;
 ParsingElement* this = ParsingElement_new(NULL);
 this->type = 'T';
 this->recognize = Token_recognize;



 config->expr = gc_strdup(expr) ; assert (config->expr!=NULL); ;
 config->customRecognize = NULL;


 {
  const char* p = expr;
  bool is_literal = 1;
  while (*p) {
   char c = *p;
   if (c == '[' || c == ']' || c == '(' || c == ')' ||
       c == '|' || c == '*' || c == '+' || c == '?' ||
       c == '.' || c == '^' || c == '$' || c == '{' ||
       c == '}' || c == '\\') {
    is_literal = 0;
    break;
   }
   p++;
  }
  if (is_literal && (p - expr) > 0) {
   config->literal = config->expr;
   config->literalLen = (int)(p - expr);
  } else {
   config->literal = NULL;
   config->literalLen = 0;
  }
 }
 this->config = config;
 assert(strcmp(config->expr, expr) == 0);
 assert(strcmp(Token_expr(this), expr) == 0);
 return this;
}


void Token_free(ParsingElement* this) {
 TokenConfig* config = (TokenConfig*)this->config;
 if (config != NULL) {





  if (config->expr!=NULL) {; gc_free(config->expr); } ;
  if (config!=NULL) {; gc_free(config); } ;
 }
 if (this!=NULL) {if (this->name!=NULL) {; gc_free(this->name); } };
 if (this!=NULL) {; gc_free(this); } ;
}

void Token_setCustomRecognize(ParsingElement* this, TokenCustomRecognize recognizer) {
 if (this && this->config) {
  ((TokenConfig*)this->config)->customRecognize = recognizer;
 }
}




int Token_recognizeJSONString(const char* input, int available, int* ovector, int* out_count) {
 if (available < 2 || input[0] != '"') return 0;
 int i = 1;
 while (i < available) {
  char c = input[i];
  if (c == '"') {

   int len = i + 1;
   ovector[0] = 0;
   ovector[1] = len;
   ovector[2] = 1;
   ovector[3] = i;
   *out_count = 2;
   return len;
  }
  if (c == '\\') {

   i += 2;
   if (i > available) return 0;
  } else {
   i++;
  }
 }
 return 0;
}



int Token_recognizeJSONNumber(const char* input, int available, int* ovector, int* out_count) {
 if (available <= 0) return 0;
 int i = 0;


 if (i < available && (input[i] == '+' || input[i] == '-')) {
  i++;
 }

 int has_digits = 0;
 int has_dot = 0;

 if (i < available && input[i] == '.') {

  has_dot = 1;
  i++;
  if (i >= available || input[i] < '0' || input[i] > '9') return 0;
  while (i < available && input[i] >= '0' && input[i] <= '9') { i++; has_digits = 1; }
 } else if (i < available && input[i] >= '0' && input[i] <= '9') {

  while (i < available && input[i] >= '0' && input[i] <= '9') { i++; has_digits = 1; }
  if (i < available && input[i] == '.') {
   has_dot = 1;
   i++;
   while (i < available && input[i] >= '0' && input[i] <= '9') { i++; }
  }
 } else {
  return 0;
 }

 if (!has_digits) return 0;


 if (i < available && (input[i] == 'e' || input[i] == 'E')) {
  i++;
  if (i < available && (input[i] == '+' || input[i] == '-')) {
   i++;
  }
  if (i >= available || input[i] < '0' || input[i] > '9') return 0;
  while (i < available && input[i] >= '0' && input[i] <= '9') { i++; }
 }

 if (i == 0) return 0;



 ovector[0] = 0;
 ovector[1] = i;

 *out_count = 1;
 return i;
}

const char* Token_expr(ParsingElement* this) {
 return ((TokenConfig*)this->config)->expr;
}

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
 assert(this->config);
 if(this->config == NULL) {return FAILURE;}
 Match* result = NULL;
 TokenConfig* config = (TokenConfig*)this->config;


 if (config->literal != NULL) {
  if (config->literalLen <= (int)context->iterator->available &&
      strncmp(config->literal, (const char*)context->iterator->current, config->literalLen) == 0) {
   result = Match_Success(config->literalLen, this, context);

   TokenMatch* data = (TokenMatch*)Arena_alloc(context->arena, sizeof(TokenMatch));
   data->count = 1;
   data->groups = NULL;
   data->extracted = 0;
   data->ovector = (int*)Arena_alloc(context->arena, sizeof(int) * 2);
   data->ovector[0] = 0;
   data->ovector[1] = config->literalLen;
   data->input = (const char*)context->iterator->current;
   result->data = data;
   context->iterator->move(context->iterator, result->length);
   assert(result->data != NULL);
   assert(Match_isSuccess(result));
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ Token " "\033[1m\033[32m" "%s" "\033[0m" "#%d:" "\033[36m" "`%s`" "\033[0m" " literal-matched %zu:%zu-%zu", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset - result->length, context->iterator->offset);fprintf(stdout, "\n");;};
  } else {
   result = FAILURE;
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s└ Token %s#%d:" "\033[36m" "`%s`" "\033[0m" " literal-failed at %zu:%zu", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset);fprintf(stdout, "\n");;};
  }
  return ParsingContext_registerMatch(context, (Element*)this, result);
 }


 if (config->customRecognize != NULL) {
  int vector[30];
  int count = 0;
  const char* line = (const char*)context->iterator->current;
  int match_len = config->customRecognize(line, (int)context->iterator->available, vector, &count);
  if (match_len > 0) {
   result = Match_Success(match_len, this, context);
   TokenMatch* data = (TokenMatch*)Arena_alloc(context->arena, sizeof(TokenMatch));
   data->count = count;
   data->groups = NULL;
   data->extracted = 0;
   int ovector_size = count * 2;
   data->ovector = (int*)Arena_alloc(context->arena, sizeof(int) * ovector_size);
   for (int j = 0; j < ovector_size; j++) {
    data->ovector[j] = vector[j];
   }
   data->input = line;
   result->data = data;
   context->iterator->move(context->iterator, result->length);
   assert(result->data != NULL);
   assert(Match_isSuccess(result));
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ Token " "\033[1m\033[32m" "%s" "\033[0m" "#%d:" "\033[36m" "`%s`" "\033[0m" " custom-matched %zu:%zu-%zu", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset - result->length, context->iterator->offset);fprintf(stdout, "\n");;};
  } else {
   result = FAILURE;
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s└ Token %s#%d:" "\033[36m" "`%s`" "\033[0m" " custom-failed at %zu:%zu", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset);fprintf(stdout, "\n");;};
  }
  return ParsingContext_registerMatch(context, (Element*)this, result);
 }
 return ParsingContext_registerMatch(context, (Element*)this, result);
}

const char* TokenMatch_group(Match* match, int index) {
 assert (match != NULL);
 assert (match->data != NULL);
 assert (Match_getElementType(match) == 'T');
 TokenMatch* m = (TokenMatch*)match->data;
 if (m) {
  assert (index >= 0);
  assert (index < m->count);

  if (!m->extracted && m->ovector != NULL) {
   {



    m->groups = (const char**)calloc(m->count, sizeof(const char*));
    assert(m->groups != NULL);
    for (int j = 0; j < m->count; j++) {
     int start = m->ovector[j * 2];
     int end = m->ovector[j * 2 + 1];
     if (start >= 0 && end >= start) {
      int len = end - start;
      char* s = (char*)malloc(len + 1);
      memcpy(s, m->input + start, len);
      s[len] = '\0';
      m->groups[j] = s;
     } else {
      m->groups[j] = NULL;
     }
    }
    m->extracted = 1;
   }
  }
  return m->groups != NULL ? m->groups[index] : NULL;
 } else {
  return NULL;
 }
}


int TokenMatch_count(Match* match) {
 assert (match != NULL);
 assert (match->data != NULL);
 assert (Match_getElementType(match) == 'T');
 TokenMatch* m = (TokenMatch*)match->data;
 if (m != NULL) {
  return m->count;
 } else {
  return 0;
 }
}

void Token_print(ParsingElement* this) {
 TokenConfig* config = (TokenConfig*)this->config;
 printf("Token:%c:%s#%d<%s>\n", this->type, this->name != NULL ? this->name : "unnamed", this->id, config->expr);
}


void TokenMatch_free(Match* match) {
 assert (match != NULL);
 assert (Match_getElementType(match) == 'T');
 match->data = NULL;
}
static inline void bitmap_set(unsigned char bitmap[32], unsigned char b) {
 bitmap[b >> 3] |= (1 << (b & 7));
}


static inline int bitmap_test(const unsigned char bitmap[32], unsigned char b) {
 return bitmap[b >> 3] & (1 << (b & 7));
}



static TokenPattern* TokenPattern_new_bitmap(void) {
 TokenPattern* p = (TokenPattern*)calloc(1, sizeof(TokenPattern));
 p->type = 'B';
 p->quantifier = '1';
 return p;
}

TokenPattern* tp_char(char c) {
 TokenPattern* p = TokenPattern_new_bitmap();
 bitmap_set(p->bitmap, (unsigned char)c);
 return p;
}

TokenPattern* tp_range(char lo, char hi) {
 TokenPattern* p = TokenPattern_new_bitmap();
 for (int i = (unsigned char)lo; i <= (unsigned char)hi; i++) {
  bitmap_set(p->bitmap, (unsigned char)i);
 }
 return p;
}

TokenPattern* tp_set(const char* chars) {
 TokenPattern* p = TokenPattern_new_bitmap();
 while (*chars) {
  bitmap_set(p->bitmap, (unsigned char)*chars);
  chars++;
 }
 return p;
}

TokenPattern* tp_not_set(const char* chars) {
 TokenPattern* p = TokenPattern_new_bitmap();

 memset(p->bitmap, 0xFF, 32);

 while (*chars) {
  p->bitmap[(unsigned char)*chars >> 3] &= ~(1 << ((unsigned char)*chars & 7));
  chars++;
 }

 p->bitmap[0] &= ~1;
 return p;
}

TokenPattern* tp_any(void) {
 TokenPattern* p = TokenPattern_new_bitmap();
 memset(p->bitmap, 0xFF, 32);

 p->bitmap[0] &= ~1;
 return p;
}

TokenPattern* tp_digit(void) {
 return tp_range('0', '9');
}

TokenPattern* tp_alpha(void) {
 TokenPattern* p = TokenPattern_new_bitmap();
 for (int i = 'a'; i <= 'z'; i++) { bitmap_set(p->bitmap, i); }
 for (int i = 'A'; i <= 'Z'; i++) { bitmap_set(p->bitmap, i); }
 return p;
}

TokenPattern* tp_word(void) {
 TokenPattern* p = TokenPattern_new_bitmap();
 for (int i = 'a'; i <= 'z'; i++) { bitmap_set(p->bitmap, i); }
 for (int i = 'A'; i <= 'Z'; i++) { bitmap_set(p->bitmap, i); }
 for (int i = '0'; i <= '9'; i++) { bitmap_set(p->bitmap, i); }
 bitmap_set(p->bitmap, '_');
 return p;
}

TokenPattern* tp_space(void) {
 TokenPattern* p = TokenPattern_new_bitmap();
 bitmap_set(p->bitmap, ' ');
 bitmap_set(p->bitmap, '\t');
 bitmap_set(p->bitmap, '\n');
 bitmap_set(p->bitmap, '\r');
 return p;
}



TokenPattern* tp_seq(TokenPattern* children[]) {

 int count = 0;
 while (children[count] != NULL) { count++; }

 if (count == 1) { return children[0]; }
 TokenPattern* p = (TokenPattern*)calloc(1, sizeof(TokenPattern));
 p->type = 'S';
 p->quantifier = '1';
 p->childCount = count;
 p->children = (TokenPattern**)malloc(sizeof(TokenPattern*) * count);
 for (int i = 0; i < count; i++) {
  p->children[i] = children[i];
 }
 return p;
}

TokenPattern* tp_alt(TokenPattern* children[]) {

 int count = 0;
 while (children[count] != NULL) { count++; }

 if (count == 1) { return children[0]; }
 TokenPattern* p = (TokenPattern*)calloc(1, sizeof(TokenPattern));
 p->type = 'A';
 p->quantifier = '1';
 p->childCount = count;
 p->children = (TokenPattern**)malloc(sizeof(TokenPattern*) * count);
 for (int i = 0; i < count; i++) {
  p->children[i] = children[i];
 }
 return p;
}






static TokenPattern* tp_quantify(TokenPattern* p, char q) {
 if (p->type == 'B' && p->quantifier == '1') {
  p->quantifier = q;
  return p;
 }
 if (p->type == 'L' && p->quantifier == '1') {
  p->quantifier = q;
  return p;
 }

 TokenPattern* g = (TokenPattern*)calloc(1, sizeof(TokenPattern));
 g->type = 'G';
 g->quantifier = q;
 g->childCount = 1;
 g->children = (TokenPattern**)malloc(sizeof(TokenPattern*));
 g->children[0] = p;
 return g;
}

TokenPattern* tp_many(TokenPattern* p) {
 return tp_quantify(p, '+');
}

TokenPattern* tp_optional(TokenPattern* p) {
 return tp_quantify(p, '?');
}

TokenPattern* tp_many_optional(TokenPattern* p) {
 return tp_quantify(p, '*');
}



TokenPattern* tp_literal(const char* str) {
 TokenPattern* p = (TokenPattern*)calloc(1, sizeof(TokenPattern));
 p->type = 'L';
 p->quantifier = '1';
 int len = (int)strlen(str);
 char* copy = (char*)malloc(len + 1);
 memcpy(copy, str, len + 1);
 p->literal = copy;
 p->literalLen = len;
 return p;
}



void TokenPattern_free(TokenPattern* this) {
 if (this == NULL) { return; }
 switch (this->type) {
  case 'S':
  case 'A':
  case 'G':
   if (this->children != NULL) {
    for (int i = 0; i < this->childCount; i++) {
     TokenPattern_free(this->children[i]);
    }
    free(this->children);
   }
   break;
  case 'L':
   if (this->literal != NULL) {
    free((void*)this->literal);
   }
   break;
  case 'B':
  default:
   break;
 }
 free(this);
}




static int TokenPattern_matchInternal(const TokenPattern* pattern, const char* input, int available);



static inline int TokenPattern_matchBitmapOnce(const unsigned char bitmap[32], const char* input, int available) {
 if (available <= 0) { return 0; }
 return bitmap_test(bitmap, (unsigned char)*input) ? 1 : 0;
}



static int TokenPattern_matchBitmap(const TokenPattern* p, const char* input, int available) {
 switch (p->quantifier) {
  case '1': {
   return TokenPattern_matchBitmapOnce(p->bitmap, input, available) ? 1 : -1;
  }
  case '?': {
   return TokenPattern_matchBitmapOnce(p->bitmap, input, available) ? 1 : 0;
  }
  case '+': {
   if (!TokenPattern_matchBitmapOnce(p->bitmap, input, available)) { return -1; }
   int n = 1;
   while (n < available && bitmap_test(p->bitmap, (unsigned char)input[n])) { n++; }
   return n;
  }
  case '*': {
   int n = 0;
   while (n < available && bitmap_test(p->bitmap, (unsigned char)input[n])) { n++; }
   return n;
  }
 }
 return -1;
}



static int TokenPattern_matchLiteral(const TokenPattern* p, const char* input, int available) {
 if (p->quantifier == '1' || p->quantifier == '+') {

  if (p->literalLen > available) { return -1; }
  if (strncmp(p->literal, input, p->literalLen) != 0) { return -1; }
  if (p->quantifier == '1') { return p->literalLen; }

  int total = p->literalLen;
  while (total + p->literalLen <= available &&
         strncmp(p->literal, input + total, p->literalLen) == 0) {
   total += p->literalLen;
  }
  return total;
 }
 if (p->quantifier == '?') {
  if (p->literalLen <= available && strncmp(p->literal, input, p->literalLen) == 0) {
   return p->literalLen;
  }
  return 0;
 }
 if (p->quantifier == '*') {
  int total = 0;
  while (total + p->literalLen <= available &&
         strncmp(p->literal, input + total, p->literalLen) == 0) {
   total += p->literalLen;
  }
  return total;
 }
 return -1;
}



static int TokenPattern_matchSeq(const TokenPattern* p, const char* input, int available) {
 int total = 0;
 for (int i = 0; i < p->childCount; i++) {
  int r = TokenPattern_matchInternal(p->children[i], input + total, available - total);
  if (r < 0) { return -1; }
  total += r;
 }
 return total;
}



static int TokenPattern_matchAlt(const TokenPattern* p, const char* input, int available) {
 for (int i = 0; i < p->childCount; i++) {
  int r = TokenPattern_matchInternal(p->children[i], input, available);
  if (r >= 0) { return r; }
 }
 return -1;
}



static int TokenPattern_matchGroup(const TokenPattern* p, const char* input, int available) {

 const TokenPattern* child = p->children[0];
 switch (p->quantifier) {
  case '1': {
   return TokenPattern_matchInternal(child, input, available);
  }
  case '?': {
   int r = TokenPattern_matchInternal(child, input, available);
   return (r < 0) ? 0 : r;
  }
  case '+': {
   int r = TokenPattern_matchInternal(child, input, available);
   if (r < 0) { return -1; }
   int total = r;
   while (total < available) {
    r = TokenPattern_matchInternal(child, input + total, available - total);
    if (r <= 0) { break; }
    total += r;
   }
   return total;
  }
  case '*': {
   int total = 0;
   while (total < available) {
    int r = TokenPattern_matchInternal(child, input + total, available - total);
    if (r <= 0) { break; }
    total += r;
   }
   return total;
  }
 }
 return -1;
}



static int TokenPattern_matchInternal(const TokenPattern* pattern, const char* input, int available) {
 switch (pattern->type) {
  case 'B':
   return TokenPattern_matchBitmap(pattern, input, available);
  case 'L':
   return TokenPattern_matchLiteral(pattern, input, available);
  case 'S':
   return TokenPattern_matchSeq(pattern, input, available);
  case 'A':
   return TokenPattern_matchAlt(pattern, input, available);
  case 'G':
   return TokenPattern_matchGroup(pattern, input, available);
 }
 return -1;
}


int TokenPattern_match(const TokenPattern* pattern, const char* input, int available) {
 int r = TokenPattern_matchInternal(pattern, input, available);
 return (r < 0) ? 0 : r;
}



ParsingElement* RangeToken_new(TokenPattern* pattern) {
 RangeTokenConfig* config = (RangeTokenConfig*) gc_new(sizeof(RangeTokenConfig)); assert (config!=NULL); ;
 ParsingElement* this = ParsingElement_new(NULL);
 this->type = 'T';
 this->recognize = RangeToken_recognize;
 this->freeMatch = TokenMatch_free;
 config->pattern = pattern;
 config->expr = NULL;
 config->customRecognize = NULL;
 this->config = config;
 return this;
}

void RangeToken_free(ParsingElement* this) {
 RangeTokenConfig* config = (RangeTokenConfig*)this->config;
 if (config != NULL) {
  if (config->pattern != NULL) { TokenPattern_free(config->pattern); }
  if (config->expr != NULL) { free(config->expr); }
  free(config);
 }
 if (this != NULL) { if (this->name!=NULL) {; gc_free(this->name); } ; }
 if (this!=NULL) {; gc_free(this); } ;
}

void RangeToken_setCustomRecognize(ParsingElement* this, TokenCustomRecognize recognizer) {
 if (this && this->config) {
  ((RangeTokenConfig*)this->config)->customRecognize = recognizer;
 }
}

Match* RangeToken_recognize(ParsingElement* this, ParsingContext* context) {
 assert(this->config);
 if (this->config == NULL) { return FAILURE; }
 Match* result = NULL;
 RangeTokenConfig* config = (RangeTokenConfig*)this->config;


 if (config->customRecognize != NULL) {
  int vector[30];
  int count = 0;
  const char* line = (const char*)context->iterator->current;
  int available = (int)(context->iterator->available - (context->iterator->current - context->iterator->buffer));
  int match_len = config->customRecognize(line, available, vector, &count);
  if (match_len > 0) {
   result = Match_Success(match_len, this, context);
   TokenMatch* data = (TokenMatch*)Arena_alloc(context->arena, sizeof(TokenMatch));
   data->count = count;
   data->groups = NULL;
   data->extracted = 0;
   int ovector_size = count * 2;
   data->ovector = (int*)Arena_alloc(context->arena, sizeof(int) * ovector_size);
   for (int j = 0; j < ovector_size; j++) {
    data->ovector[j] = vector[j];
   }
   data->input = line;
   result->data = data;
   context->iterator->move(context->iterator, result->length);
   assert(result->data != NULL);
   assert(Match_isSuccess(result));
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ RangeToken " "\033[1m\033[32m" "%s" "\033[0m" "#%d custom-matched %zu:%zu-%zu", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset - result->length, context->iterator->offset);fprintf(stdout, "\n");;};
  } else {
   result = FAILURE;
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s└ RangeToken %s#%d custom-failed at %zu:%zu", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset);fprintf(stdout, "\n");;};
  }
  return ParsingContext_registerMatch(context, (Element*)this, result);
 }


 const char* line = (const char*)context->iterator->current;
 int available = (int)(context->iterator->available - (context->iterator->current - context->iterator->buffer));
 int match_len = TokenPattern_match(config->pattern, line, available);

 if (match_len > 0) {
  result = Match_Success(match_len, this, context);

  TokenMatch* data = (TokenMatch*)Arena_alloc(context->arena, sizeof(TokenMatch));
  data->count = 1;
  data->groups = NULL;
  data->extracted = 0;
  data->ovector = (int*)Arena_alloc(context->arena, sizeof(int) * 2);
  data->ovector[0] = 0;
  data->ovector[1] = match_len;
  data->input = line;
  result->data = data;
  context->iterator->move(context->iterator, result->length);
  assert(result->data != NULL);
  assert(Match_isSuccess(result));
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ RangeToken " "\033[1m\033[32m" "%s" "\033[0m" "#%d matched %zu:%zu-%zu", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset - result->length, context->iterator->offset);fprintf(stdout, "\n");;};
 } else {
  result = FAILURE;
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s└ RangeToken %s#%d failed at %zu:%zu", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset);fprintf(stdout, "\n");;};
 }
 return ParsingContext_registerMatch(context, (Element*)this, result);
}







ParsingElement* Group_new(Reference* children[]) {
 ParsingElement* this = ParsingElement_new(children);
 this->type = 'G';
 this->recognize = Group_recognize;
 return this;
}

Match* Group_recognize(ParsingElement* this, ParsingContext* context){


 size_t memo_offset = context->iterator->offset;
 size_t memo_lines = context->iterator->lines;
 Match* cached = ParsingContext_memoGet(context, this->id, memo_offset);
 if (cached == FAILURE) {
  return ParsingContext_registerMatch(context, (Element*)this, FAILURE);
 } else if (cached != NULL) {
  return ParsingContext_registerMatch(context, (Element*)this, cached);
 }


 if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "??? %s┌── Group " "\033[1m\033[33m" "%s" "\033[0m" ":#%d at %zu:%zu[→%d]", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset, context->depth);fprintf(stdout, "\n");;};
 Match* result = NULL;
 size_t offset = context->iterator->offset;
 size_t lines = context->iterator->lines;
 int step = 0;


 size_t iteration_offset = context->iterator->offset;
 Reference* child = this->children;
 Match* match = NULL;
 step = 0;

 while (child != NULL ) {
  assert (match == NULL);
  match = Reference_recognize(child, context);

  if (Match_isSuccess(match)) {

   assert(result == NULL);
   result = Match_Success(match->length, this, context);
   result->offset = iteration_offset;
   result->children = match;
   child = NULL;
  } else {

   match = Match_free(match);
   child = child->next;
   step += 1;
  }
 }


 if (Match_isSuccess(result)) {
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s╘═⇒ Group " "\033[1m\033[32m" "%s" "\033[0m" "#%d[%d] matched" "\033[1m\033[32m" "%zu:%zu-%zu" "\033[0m" "[%zu][→%d]", context->indent, this->name, this->id, step, context->iterator->lines, result->offset, context->iterator->offset, result->length, context->depth);fprintf(stdout, "\n");;}

  ParsingContext_memoSet(context, this->id, memo_offset, result, context->iterator->offset, context->iterator->lines);
  return ParsingContext_registerMatch(context, (Element*)this, result);
 } else {

  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s╘═⇒ Group " "\033[1m\033[31m" "%s" "\033[0m" "#%d[%d] failed at %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, step, context->iterator->lines, context->iterator->offset, offset, context->depth);fprintf(stdout, "\n");;}
  Match_fail(result);
  if (context->iterator->offset != offset ) {
   Iterator_backtrack(context->iterator, offset, lines);
   assert( context->iterator->offset == offset );
  }

  ParsingContext_memoSet(context, this->id, memo_offset, FAILURE, memo_offset, memo_lines);
  return ParsingContext_registerMatch(context, (Element*)this, FAILURE);
 }

}
ParsingElement* Rule_new(Reference* children[]) {
 ParsingElement* this = ParsingElement_new(children);
 this->type = 'R';
 this->recognize = Rule_recognize;

 return this;
}

Match* Rule_recognize (ParsingElement* this, ParsingContext* context){


 size_t memo_offset = context->iterator->offset;
 size_t memo_lines = context->iterator->lines;
 Match* cached = ParsingContext_memoGet(context, this->id, memo_offset);
 if (cached == FAILURE) {
  return ParsingContext_registerMatch(context, (Element*)this, FAILURE);
 } else if (cached != NULL) {
  return ParsingContext_registerMatch(context, (Element*)this, cached);
 }



 Match* result = FAILURE;
 Match* last = NULL;
 int step = 0;
 const char* step_name = NULL;
 size_t offset = context->iterator->offset;
 size_t lines = context->iterator->lines;
 Reference* child = this->children;

 if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "??? %s┌── Rule:" "\033[1m\033[33m" "%s" "\033[0m" " at %zu:%zu[→%d]", context->indent, this->name, context->iterator->lines, context->iterator->offset, context->depth);fprintf(stdout, "\n");;};


 ParsingContext_push(context);



 while (child != NULL) {

  if (child->next != NULL) {
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " ‥%s├─" "\033[1m\033[33m" "%d" "\033[0m", context->indent, step);fprintf(stdout, "\n");;};
  } else {
   if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " ‥%s└─" "\033[1m\033[33m" "%d" "\033[0m", context->indent, step);fprintf(stdout, "\n");;};
  }



  Match* match = Reference_recognize(child, context);



  if (!Match_isSuccess(match)) {


   match = Match_free(match);
   size_t skipped = ParsingElement_skip(this, context);



   if (skipped > 0) {



    match = Reference_recognize(child, context);


    if (!Match_isSuccess(match)) {

     match = Match_free(match);
     result = Match_fail(result);




     break;
    }

   } else {


    match = Match_free(match);
    result = Match_fail(result);
    break;
   }
  }


  assert(Match_isSuccess(match));
  if (last == NULL) {
   assert(result == FAILURE);




   result = Match_Success(match->length, this, context);
   result->offset = offset;
   result->children = last = match;
  } else {
   assert(last->next == NULL);
   last = last->next = match;
  }


  step_name = child->name;

  child = child->next;

  step++;
 }


 ParsingContext_pop(context);


 if (Match_isSuccess(result)) {
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s╘═⇒ Rule " "\033[1m\033[32m" "%s" "\033[0m" "#%d[%d] matched " "\033[1m\033[32m" "%zu:%zu-%zu" "\033[0m" "[%zub][→%d]", context->indent, this->name, this->id, step, context->iterator->lines, offset, context->iterator->offset, result->length, context->depth);fprintf(stdout, "\n");;}



  result->length = last->offset - result->offset + last->length;

  ParsingContext_memoSet(context, this->id, memo_offset, result, context->iterator->offset, context->iterator->lines);
 } else {
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s╘ Rule " "\033[1m\033[31m" "%s" "\033[0m" "#%d failed on step %d=%s at %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, step, step_name == NULL ? "-" : step_name, context->iterator->lines, offset, context->iterator->offset, context->depth);fprintf(stdout, "\n");;}

  result = Match_fail(result);

  if (offset != context->iterator->offset) {
   Iterator_backtrack(context->iterator, offset, lines);
   assert( context->iterator->offset == offset );
  }

  ParsingContext_memoSet(context, this->id, memo_offset, FAILURE, memo_offset, memo_lines);
 }

 return ParsingContext_registerMatch(context, (Element*)this, result);
}







ParsingElement* Procedure_new(ProcedureCallback c) {
 ParsingElement* this = ParsingElement_new(NULL);
 this->type = 'p';
 this->config = c;
 this->recognize = Procedure_recognize;
 return this;
}

Match* Procedure_recognize(ParsingElement* this, ParsingContext* context) {
 if (this->config != NULL) {

  ((ProcedureCallback)(this->config))(this, context);
 }
 if(context->grammar->isVerbose && !(context->flags & 0x1) && this->name){fprintf(stdout, "[✓] %sProcedure " "\033[1m\033[32m" "%s" "\033[0m" "#%d executed at %zu", context->indent, this->name, this->id, context->iterator->offset);fprintf(stdout, "\n");;}
 return ParsingContext_registerMatch(context, (Element*)this, Match_Success(0, this, context));
}







ParsingElement* Condition_new(ConditionCallback c) {
 ParsingElement* this = ParsingElement_new(NULL);
 this->type = 'c';
 this->config = c;
 this->recognize = Condition_recognize;
 return this;
}

Match* Condition_recognize(ParsingElement* this, ParsingContext* context) {
 if (this->config != NULL) {
  bool value = ((ConditionCallback)this->config)(this, context);
  Match* result = value == 1 ? Match_Success(0, this, context) : FAILURE;
  if(context->grammar->isVerbose && !(context->flags & 0x1) && Match_isSuccess(result)){fprintf(stdout, "[✓] %s└ Condition " "\033[1m\033[32m" "%s" "\033[0m" "#%d matched %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset - result->length, context->iterator->offset, context->depth);fprintf(stdout, "\n");;}
  if(context->grammar->isVerbose && !(context->flags & 0x1) && !Match_isSuccess(result)){fprintf(stdout, " !  %s└ Condition " "\033[1m\033[31m" "%s" "\033[0m" "#%d failed at %zu:%zu[→%d]", context->indent, this->name, this->id, context->iterator->lines, context->iterator->offset, context->depth);fprintf(stdout, "\n");;}
  return ParsingContext_registerMatch(context, (Element*)this, result);
 } else {
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ Condition %s#%d matched by default at %zu", context->indent, this->name, this->id, context->iterator->offset);fprintf(stdout, "\n");;};
  Match* result = Match_Success(0, this, context);
  assert(Match_isSuccess(result));
  return ParsingContext_registerMatch(context, (Element*)this, result);
 }
}







ParsingVariable* ParsingVariable_new(int depth, const char* key, void* value) {
 ParsingVariable* this = (ParsingVariable*) gc_new(sizeof(ParsingVariable)); assert (this!=NULL); ;
 this->depth = depth;
 this->key = gc_strdup(key) ; assert (this->key!=NULL); ;
 this->value = value;
 this->previous = NULL;
 return this;
}

void ParsingVariable_free(ParsingVariable* this) {
 if (this!=NULL) {
  if (this->key!=NULL) {; gc_free(this->key); } ;
  if (this!=NULL) {; gc_free(this); } ;
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

const char* ParsingVariable_getName(const ParsingVariable* this) {
 return (const char*)this->key;
}

void* ParsingVariable_get(ParsingVariable* this, const char* name) {
 ParsingVariable* found = ParsingVariable_find(this, name, 0);
 return found != NULL ? found->value : NULL;
}

bool ParsingVariable_is(const ParsingVariable* this, const char* key) {
 if (this == NULL || key == NULL) {return 0;}
 return (key == this->key || strcmp(this->key, key)) == 0 ? 1 : 0;
}

ParsingVariable* ParsingVariable_find(ParsingVariable* this, const char* key, bool local) {
 ParsingVariable* current=this;
 while (current!=NULL) {
  if (ParsingVariable_is(current, key)) {
   return current;
  }
  if (current->previous!=NULL) {

   current = (local && current->previous->depth != current->depth) ? NULL : current->previous;
  } else {
   current = NULL;
  }
 }
 return current;
}

ParsingVariable* ParsingVariable_set(ParsingVariable* this, const char* key, void* value) {
 ParsingVariable* found = ParsingVariable_find(this, key, 1);
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
 int depth = this == NULL ? 0 : ParsingVariable_getDepth(this) + 1;
 ParsingVariable* res = ParsingVariable_new(depth, "depth", (void*)(long)depth);
 res->previous = this;
 return res;
}

ParsingVariable* ParsingVariable_pop(ParsingVariable* this) {
 if (this == NULL) {return NULL;}
 ParsingVariable* current = this;
 int depth = this->depth;
 while (current != NULL && current->depth >= depth) {
  ParsingVariable* to_free = current;
  current = current->previous;
  ParsingVariable_free(to_free);
 }
 return current;
}

int ParsingVariable_count(ParsingVariable* this) {
 ParsingVariable* current = this;
 int count = 0;
 while (current!=NULL) {
  current = current->previous;
  count++;
 }
 return count;
}







ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator ) {
 ParsingContext* this = (ParsingContext*) gc_new(sizeof(ParsingContext)); assert (this!=NULL); ;
 this->grammar = g;
 this->iterator = iterator;
 this->stats = ParsingStats_new();
 this->freeIterator = 0;
 if (g != NULL) {
  ParsingStats_setSymbolsCount(this->stats, g->axiomCount + g->skipCount);
 }
 this->depth = 0;
 this->variables = ParsingVariable_new(0, "depth", 0);
 this->callback = NULL;
 this->indent = INDENT + (40 * 2);
 this->flags = 0;
 this->lastMatchOffset = 0;
 this->lastMatchLength = 0;
 this->lastMatchElementID = -1;

 this->arena = Arena_new();


 if (g != NULL && g->noMemo) {
  this->memoTable = NULL;
  this->memoCapacity = 0;
  this->inputLength = 0;
 } else {


  this->inputLength = iterator != NULL ? iterator->available : 0;
  size_t symbolCount = g != NULL ? (size_t)(g->axiomCount + g->skipCount) : 0;

  size_t memoSize = symbolCount > 0 ? (this->inputLength * symbolCount < 1024 * 1024 ? this->inputLength * symbolCount : 1024 * 1024) : 0;

  if (memoSize < 4096) { memoSize = 4096; }
  size_t power = 1;
  while (power < memoSize) { power <<= 1; }
  this->memoCapacity = power;
  if (this->memoCapacity > 0) {
   this->memoTable = (MemoEntry*)calloc(this->memoCapacity, sizeof(MemoEntry));
   assert(this->memoTable != NULL);
  } else {
   this->memoTable = NULL;
  }
 }
 return this;
}

void ParsingContext_free( ParsingContext* this ) {

 if (this!=NULL) {
  if (this->freeIterator) {Iterator_free(this->iterator);}
  ParsingVariable_freeAll(this->variables);
  ParsingStats_free(this->stats);

  if (this->memoTable != NULL) { free(this->memoTable); this->memoTable = NULL; }

  Arena_free(this->arena);
  this->arena = NULL;
  if (this!=NULL) {; gc_free(this); } ;
 }
}

char* ParsingContext_text( ParsingContext* this ) {
 return this->iterator->buffer;
}

char ParsingContext_charAt ( ParsingContext* this, size_t offset ) {
 return Iterator_charAt(this->iterator, offset);
}


void ParsingContext_push ( ParsingContext* this ) {
 this->variables = ParsingVariable_push(this->variables);
 if (this->callback != NULL) {this->callback(this, '+');}
 this->depth += 1;
 if (this->depth >= 0) {
  int d = this->depth % 40;
  this->indent = INDENT + (40 - d) * 2;
 }
}

void ParsingContext_pop ( ParsingContext* this ) {
 if (this->callback != NULL) {this->callback(this, '-');}
 this->variables = ParsingVariable_pop(this->variables);
 this->depth -= 1;
 if (this->depth <= 0) {
  this->indent = INDENT + 40 * 2;
 } else {
  int d = this->depth % 40;
  this->indent = INDENT + (40 - d) * 2;
 }
}

void* ParsingContext_get(ParsingContext* this, const char* name) {
 return ParsingVariable_get(this->variables, name);
}

intptr_t ParsingContext_getInt(ParsingContext* this, const char* name) {
 return (intptr_t)(ParsingVariable_get(this->variables, name));
}

void ParsingContext_set(ParsingContext* this, const char* name, void* value) {
 this->variables = ParsingVariable_set(this->variables, name, value);
}

void ParsingContext_setInt(ParsingContext* this, const char* name, int value) {
 this->variables = ParsingVariable_set(this->variables, name, (void*)(long)value);
}

void ParsingContext_on(ParsingContext* this, ContextCallback callback) {
 this->callback = callback;
}

int ParsingContext_getVariableCount(ParsingContext* this) {
 return ParsingVariable_count(this->variables);
}

size_t ParsingContext_getOffset(ParsingContext* this) {
 return this->iterator->offset;
}

Match* ParsingContext_registerMatch(ParsingContext* this, Element* e, Match* m) {

 if ((this->flags & 0x1)) {return m;}


 if (m != NULL && Match_isSuccess(m)) {
  if ( (this->lastMatchOffset + this->lastMatchLength) < (m->offset + m->length) && m->length > 0) {
   this->lastMatchOffset = m->offset;
   this->lastMatchLength = m->length;
   this->lastMatchElementID = m->element->id;
  }
 }
 return m;
}







static inline size_t memo_hash(int elementId, size_t offset, size_t mask) {
 size_t h = (size_t)elementId * 2654435761u;
 h ^= offset;
 h *= 2246822519u;
 h ^= h >> 16;
 return h & mask;
}

Match* ParsingContext_memoGet(ParsingContext* this, int elementId, size_t offset) {
 if (this->memoTable == NULL || elementId < 0) { return NULL; }
 size_t mask = this->memoCapacity - 1;
 size_t idx = memo_hash(elementId, offset, mask);

 for (int probe = 0; probe < 8; probe++) {
  MemoEntry* e = &this->memoTable[(idx + probe) & mask];
  if (e->status == 0) {
   return NULL;
  }

  if (e->match != NULL && e->match->element != NULL &&
      e->match->element->id == elementId &&
      e->match->offset == offset &&
      e->status == 1) {

   Iterator_backtrack(this->iterator, e->end_offset, e->end_lines);
   return e->match;
  }
  if (e->status == 2 &&
      e->end_offset == offset &&
      e->end_lines == (size_t)elementId) {


   return FAILURE;
  }
 }
 return NULL;
}

void ParsingContext_memoSet(ParsingContext* this, int elementId, size_t offset,
                           Match* match, size_t endOffset, size_t endLines) {
 if (this->memoTable == NULL || elementId < 0) { return; }
 size_t mask = this->memoCapacity - 1;
 size_t idx = memo_hash(elementId, offset, mask);

 for (int probe = 0; probe < 8; probe++) {
  MemoEntry* e = &this->memoTable[(idx + probe) & mask];
  if (e->status == 0) {
   if (Match_isSuccess(match)) {
    e->status = 1;
    e->match = match;
    e->end_offset = endOffset;
    e->end_lines = endLines;
   } else {
    e->status = 2;
    e->match = NULL;
    e->end_offset = offset;
    e->end_lines = (size_t)elementId;
   }
   return;
  }
 }

}







ParsingStats* ParsingStats_new(void) {
 ParsingStats* this = (ParsingStats*) gc_new(sizeof(ParsingStats)); assert (this!=NULL); ;
 this->bytesRead = 0;
 this->parseTime = 0;
 this->successBySymbol = NULL;
 this->failureBySymbol = NULL;
 this->failureOffset = 0;
 this->matchOffset = 0;
 this->matchLength = 0;
 this->failureElement = NULL;
 return this;
}

void ParsingStats_free(ParsingStats* this) {
 if (this != NULL) {
  if (this->successBySymbol!=NULL) {; gc_free(this->successBySymbol); } ;
  if (this->failureBySymbol!=NULL) {; gc_free(this->failureBySymbol); } ;
 }
 if (this!=NULL) {; gc_free(this); } ;
}

void ParsingStats_setSymbolsCount(ParsingStats* this, size_t t) {
 this->successBySymbol=gc_realloc(this->successBySymbol,t * sizeof(size_t)); ;
 this->failureBySymbol=gc_realloc(this->failureBySymbol,t * sizeof(size_t)); ;
 this->symbolsCount = t;
}







ParsingResult* ParsingResult_new(Match* match, ParsingContext* context) {
 ParsingResult* this = (ParsingResult*) gc_new(sizeof(ParsingResult)); assert (this!=NULL); ;
 assert(match != NULL);
 assert(context != NULL);
 assert(context->iterator != NULL);
 this->match = match;
 this->context = context;
 if (match != FAILURE && context->iterator->offset > 0) {
  if (Iterator_hasMore(context->iterator) && Iterator_remaining(context->iterator) > 0) {
   if(context->grammar->isVerbose){fprintf(stderr, "--- ");fprintf(stderr, "Partial success, parsed %zu bytes, %zu remaining", context->iterator->offset, Iterator_remaining(context->iterator));fprintf(stderr, "\n");;};
   this->status = 'p';
  } else {
   if(context->grammar->isVerbose){fprintf(stderr, "--- ");fprintf(stderr, "Succeeded, iterator at %zu, parsed %zu bytes, %zu remaining", context->iterator->offset, context->stats->bytesRead, Iterator_remaining(context->iterator));fprintf(stderr, "\n");;};
   this->status = 'S';
  }
 } else {
  if(context->grammar->isVerbose){fprintf(stderr, "--- ");fprintf(stderr, "Failed, parsed %zu bytes, %zu remaining", context->iterator->offset, Iterator_remaining(context->iterator));fprintf(stderr, "\n");;}
  this->status = 'F';
 }
 return this;
}


bool ParsingResult_isFailure(const ParsingResult* this) {
 return this->status == 'F';
}

bool ParsingResult_isPartial(const ParsingResult* this) {
 return this->status == 'p';
}

bool ParsingResult_isSuccess(const ParsingResult* this) {
 return this->status == 'S';
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


  this->match = Match_free(this->match);

  ParsingContext_free(this->context);
 }
 if (this!=NULL) {; gc_free(this); } ;
}







int Grammar__resetElementIDs(Element* e, int step, void* nothing) {
 if (Reference_Is(e)) {
  Reference* r = (Reference*)e;
  if (r->id != -1) {
   ;
   r->id = -1;
   return step;
  } else {
   return -1;
  }
 } else {
  ParsingElement * r = (ParsingElement*)e;
  if (r->id != -1) {
   ;
   r->id = -1;
   return step;
  } else {
   return -1;
  }
 }
}

int Grammar__assignElementIDs(Element* e, int step, void* nothing) {
 if (Reference_Is(e)) {
  Reference* r = (Reference*)e;
  if (r->id == -1) {
   r->id = step;
   ;;
   return step;
  } else {
   return -1;
  }
 } else {
  ParsingElement * r = (ParsingElement*)e;
  if (r->id == -1) {
   r->id = step;
   ;;
   return step;
  } else {
   return -1;
  }
 }
}

int Grammar__registerElement(Element* e, int step, void* grammar) {
 Reference* r = (Reference*)e;
 Grammar* g = (Grammar*)grammar;
 Element* ge = g->elements[r->id];
 if (ge == NULL) {
  ;;
  g->elements[r->id] = e;
  return step;
 } else {
  return -1;
 }
}

void Grammar_prepare ( Grammar* this ) {
 if (this->skip!=NULL) {
  this->skip->id = 0;
 }
 if (this->axiom!=NULL) {

  if (this->elements) { if (this->elements!=NULL) {; gc_free(this->elements); } ; this->elements = NULL; }
  assert(this->elements == NULL);

  ;
  ParsingElement_walk(this->axiom, Grammar__resetElementIDs, NULL);
  if (this->skip != NULL) {
   ParsingElement_walk(this->skip, Grammar__resetElementIDs, NULL);
  }

  ;
  int count = ParsingElement_walk(this->axiom, Grammar__assignElementIDs, NULL);
  this->axiomCount = count;
  if (this->skip != NULL) {
   this->skipCount = ParsingElement__walk(this->skip, Grammar__assignElementIDs, count + 1, NULL) - count;
  }


  Element** elements = (Element**) gc_calloc((size_t)this->skipCount + (size_t)this->axiomCount + 1, sizeof(Element*)) ; assert (elements!=NULL); ;
  this->elements = elements;

  count = ParsingElement_walk(this->axiom, Grammar__registerElement, this);
  if (this->skip != NULL) {
   ParsingElement__walk(this->skip, Grammar__registerElement, count, this);
  }
 }
}

ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator ) {

 if (this->elements == NULL) {Grammar_prepare(this);}
 assert(this->axiom != NULL);
 ParsingContext* context = ParsingContext_new(this, iterator);
 assert(this->axiom->recognize != NULL);
 clock_t t1 = clock();
 Match* match = this->axiom->recognize(this->axiom, context);
 context->stats->parseTime = ((double)clock() - (double)t1) / CLOCKS_PER_SEC;
 context->stats->bytesRead = iterator->offset;
 return ParsingResult_new(match, context);
}

ParsingResult* Grammar_parsePath( Grammar* this, const char* path ) {
 Iterator* iterator = Iterator_Open(path);
 if (iterator != NULL) {
  ParsingResult* result = Grammar_parseIterator(this, iterator);
  result->context->freeIterator = 1;
  return result;
 } else {
  errno = ENOENT;
  return NULL;
 }
}

ParsingResult* Grammar_parseString( Grammar* this, const char* text ) {
 Iterator* iterator = Iterator_FromString(text);
 if (iterator != NULL) {
  ParsingResult* result = Grammar_parseIterator(this, iterator);
  result->context->freeIterator = 1;
  return result;
 } else {
  errno = ENOENT;
  return NULL;
 }
}







Processor* Processor_new() {
 Processor* this = (Processor*) gc_new(sizeof(Processor)); assert (this!=NULL); ;
 this->callbacksCount = 100;
 ProcessorCallback* callbacks = (ProcessorCallback*) gc_calloc((size_t)this->callbacksCount, sizeof(ProcessorCallback)) ; assert (callbacks!=NULL); ;
 this->callbacks = callbacks;
 this->fallback = NULL;
 return this;
}

void Processor_free(Processor* this) {
 if (this!=NULL) {; gc_free(this); } ;
}

void Processor_register (Processor* this, int symbolID, ProcessorCallback callback ) {
 if (this->callbacksCount < (symbolID + 1)) {
  int cur_count = this->callbacksCount;
  int new_count = symbolID + 100;
  this->callbacks=gc_realloc(this->callbacks,new_count * sizeof(ProcessorCallback)); ;
  this->callbacksCount = new_count;

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
   step = Processor_process(this, child, step);
   child = child->next;
  }
 }
 return step;
}
void Utilities_indent( ParsingElement* this, ParsingContext* context ) {}
void Utilities_dedent( ParsingElement* this, ParsingContext* context ) {}
bool Utilites_checkIndent( ParsingElement *this, ParsingContext* context ) { return 1; }







static int Match_flatten_recursive(Match* match, MatchFlatNode* buffer, int offset, int bufferSize) {
 if (!match || offset >= bufferSize) { return offset; }

 MatchFlatNode* node = &buffer[offset];
 node->type = match->element->type;
 node->id = match->element->id;
 node->match = match;
 node->wordValue = NULL;
 node->isMany = 0;


 int childCount = 0;
 Match* child = match->children;
 while (child) { childCount++; child = child->next; }
 node->numChildren = childCount;


 if (node->type == '#') {
  node->isMany = Reference_isMany((Reference*)match->element) ? 1 : 0;
 }


 if (node->type == 'W') {
  WordConfig* config = (WordConfig*)((ParsingElement*)match->element)->config;
  if (config && match->data) {
   node->wordValue = (const char*)match->data;
  }
 }

 offset++;


 child = match->children;
 while (child && offset < bufferSize) {
  offset = Match_flatten_recursive(child, buffer, offset, bufferSize);
  child = child->next;
 }

 return offset;
}

int Match_flatten(Match* this, MatchFlatNode* buffer, int bufferSize) {
 if (!this || !buffer || bufferSize <= 0) { return 0; }
 return Match_flatten_recursive(this, buffer, 0, bufferSize);
}
static int Match_flattenPost_recursive(Match* match, MatchPostNode* buffer, int offset, int bufferSize) {
 if (!match || offset >= bufferSize) { return offset; }

 Element* element = match->element;
 char type = element->type;


 if (type == '#') {
  bool isMany = Reference_isMany((Reference*)element);
  if (!isMany) {

   Match* child = match->children;
   if (child) {
    return Match_flattenPost_recursive(child, buffer, offset, bufferSize);
   } else {

    if (offset < bufferSize) {
     MatchPostNode* node = &buffer[offset];
     node->type = 'N';
     node->id = element->id;
     node->numChildren = 0;
     node->wordValue = NULL;
     node->match = NULL;
     offset++;
    }
    return offset;
   }
  } else {

   int childCount = 0;
   Match* child = match->children;
   while (child) {
    offset = Match_flattenPost_recursive(child, buffer, offset, bufferSize);
    childCount++;
    child = child->next;
   }

   if (offset < bufferSize) {
    MatchPostNode* node = &buffer[offset];
    node->type = 'L';
    node->id = element->id;
    node->numChildren = childCount;
    node->wordValue = NULL;
    node->match = NULL;
    offset++;
   }
   return offset;
  }
 }


 int childCount = 0;
 Match* child = match->children;
 while (child) {
  offset = Match_flattenPost_recursive(child, buffer, offset, bufferSize);
  childCount++;
  child = child->next;
 }


 if (offset < bufferSize) {
  MatchPostNode* node = &buffer[offset];
  node->type = type;
  node->id = element->id;
  node->numChildren = childCount;
  node->match = match;
  node->wordValue = NULL;


  if (type == 'W') {
   if (match->data) {
    node->wordValue = (const char*)match->data;
   }
  }
  offset++;
 }

 return offset;
}

int Match_flattenPost(Match* this, MatchPostNode* buffer, int bufferSize) {
 if (!this || !buffer || bufferSize <= 0) { return 0; }
 return Match_flattenPost_recursive(this, buffer, 0, bufferSize);
}





static int Match_flattenPostArrays_recursive(Match* match,
    char* types, int* ids, int* nchildren, const char** words, Match** matches,
    int offset, int bufferSize) {
 if (!match || offset >= bufferSize) { return offset; }

 Element* element = match->element;
 char type = element->type;

 if (type == '#') {
  bool isMany = Reference_isMany((Reference*)element);
  if (!isMany) {
   Match* child = match->children;
   if (child) {
    return Match_flattenPostArrays_recursive(child,
     types, ids, nchildren, words, matches, offset, bufferSize);
   } else {
    if (offset < bufferSize) {
     types[offset] = 'N';
     ids[offset] = element->id;
     nchildren[offset] = 0;
     words[offset] = NULL;
     matches[offset] = NULL;
     offset++;
    }
    return offset;
   }
  } else {
   int childCount = 0;
   Match* child = match->children;
   while (child) {
    offset = Match_flattenPostArrays_recursive(child,
     types, ids, nchildren, words, matches, offset, bufferSize);
    childCount++;
    child = child->next;
   }
   if (offset < bufferSize) {
    types[offset] = 'L';
    ids[offset] = element->id;
    nchildren[offset] = childCount;
    words[offset] = NULL;
    matches[offset] = NULL;
    offset++;
   }
   return offset;
  }
 }

 int childCount = 0;
 Match* child = match->children;
 while (child) {
  offset = Match_flattenPostArrays_recursive(child,
   types, ids, nchildren, words, matches, offset, bufferSize);
  childCount++;
  child = child->next;
 }

 if (offset < bufferSize) {
  types[offset] = type;
  ids[offset] = element->id;
  nchildren[offset] = childCount;
  matches[offset] = match;
  words[offset] = NULL;
  if (type == 'W' && match->data) {
   words[offset] = (const char*)match->data;
  }
  offset++;
 }
 return offset;
}

int Match_flattenPostArrays(Match* this, char* types, int* ids, int* nchildren,
                            const char** words, Match** matches, int bufferSize) {
 if (!this || !types || bufferSize <= 0) { return 0; }
 return Match_flattenPostArrays_recursive(this, types, ids, nchildren, words, matches, 0, bufferSize);
}
static int Match_flattenPostArraysEx_recursive(Match* match,
    char* types, int* ids, int* nchildren, const char** words, Match** matches,
    const char* action_codes, int max_id,
    char* strbuf, int strbufSize, int* strbufOffset,
    int offset, int bufferSize) {
 if (!match || offset >= bufferSize) { return offset; }

 Element* element = match->element;
 char type = element->type;
 int eid = element->id;

 if (type == '#') {
  bool isMany = Reference_isMany((Reference*)element);
  if (!isMany) {
   Match* child = match->children;
   if (child) {
    return Match_flattenPostArraysEx_recursive(child,
     types, ids, nchildren, words, matches,
     action_codes, max_id, strbuf, strbufSize, strbufOffset,
     offset, bufferSize);
   } else {
    if (offset < bufferSize) {
     types[offset] = 'N';
     ids[offset] = eid;
     nchildren[offset] = 0;
     words[offset] = NULL;
     matches[offset] = NULL;
     offset++;
    }
    return offset;
   }
  } else {
   int childCount = 0;
   Match* child = match->children;
   while (child) {
    offset = Match_flattenPostArraysEx_recursive(child,
     types, ids, nchildren, words, matches,
     action_codes, max_id, strbuf, strbufSize, strbufOffset,
     offset, bufferSize);
    childCount++;
    child = child->next;
   }
   if (offset < bufferSize) {
    types[offset] = 'L';
    ids[offset] = eid;
    nchildren[offset] = childCount;
    words[offset] = NULL;
    matches[offset] = NULL;
    offset++;
   }
   return offset;
  }
 }


 char emitted = type;
 if (eid >= 0 && eid <= max_id && action_codes[eid] != 0) {
  emitted = action_codes[eid];
 }




 if (emitted == 'P') {
  Match* child = match->children;
  if (child) {
   return Match_flattenPostArraysEx_recursive(child,
    types, ids, nchildren, words, matches,
    action_codes, max_id, strbuf, strbufSize, strbufOffset,
    offset, bufferSize);
  }

  if (offset < bufferSize) {
   types[offset] = 'N';
   ids[offset] = eid;
   nchildren[offset] = 0;
   words[offset] = NULL;
   matches[offset] = NULL;
   offset++;
  }
  return offset;
 }

 int childCount = 0;
 Match* child = match->children;
 while (child) {
  offset = Match_flattenPostArraysEx_recursive(child,
   types, ids, nchildren, words, matches,
   action_codes, max_id, strbuf, strbufSize, strbufOffset,
   offset, bufferSize);
  childCount++;
  child = child->next;
 }

 if (offset < bufferSize) {
  types[offset] = emitted;
  ids[offset] = eid;
  nchildren[offset] = childCount;
  matches[offset] = match;
  words[offset] = NULL;
  if (type == 'W' && match->data) {
   words[offset] = (const char*)match->data;
  } else if (type == 'T' && match->data) {




   TokenMatch* m = (TokenMatch*)match->data;
   if (m && m->ovector && m->count > 0) {
    int start = m->ovector[0];
    int end = m->ovector[1];
    int len = end - start;
    int soff = *strbufOffset;
    if (len > 0 && soff + len + 1 <= strbufSize) {
     memcpy(strbuf + soff, m->input + start, len);
     strbuf[soff + len] = '\0';
     words[offset] = strbuf + soff;
     *strbufOffset = soff + len + 1;
    } else if (len == 0) {

     words[offset] = "";
    }


    nchildren[offset] = m->count;
   }
  }
  offset++;
 }
 return offset;
}

int Match_flattenPostArraysEx(Match* this, char* types, int* ids, int* nchildren,
                              const char** words, Match** matches,
                              const char* action_codes, int max_id,
                              char* strbuf, int strbufSize,
                              int* out_strbuf_used,
                              int bufferSize) {
 if (!this || !types || bufferSize <= 0) { return 0; }
 int strbufOffset = 0;
 int result = Match_flattenPostArraysEx_recursive(this, types, ids, nchildren,
  words, matches, action_codes, max_id,
  strbuf, strbufSize, &strbufOffset,
  0, bufferSize);
 if (out_strbuf_used) {
  *out_strbuf_used = strbufOffset;
 }
 return result;
}
