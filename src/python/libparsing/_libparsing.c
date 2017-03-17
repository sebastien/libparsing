typedef struct Iterator {
 char status;
 char* buffer;
 char* current;
 char separator;
 size_t offset;
 size_t lines;
 size_t capacity;
 size_t available;
 
_Bool 
               freeBuffer;

 void* input;
 void (*freeInput) (void*);
 
_Bool 
              (*move) (struct Iterator*, int n);
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






_Bool 
    Iterator_open( Iterator* this, const char* path );





_Bool 
    Iterator_hasMore( Iterator* this );





size_t Iterator_remaining( Iterator* this );




_Bool 
    Iterator_moveTo ( Iterator* this, size_t offset );




_Bool 
    Iterator_backtrack ( Iterator* this, size_t offset, size_t lines );



char Iterator_charAt ( Iterator* this, size_t offset );



_Bool 
    String_move ( Iterator* this, int offset );
FileInput* FileInput_new(const char* path );


void FileInput_free(void* this);




size_t FileInput_preload( Iterator* this );






_Bool 
    FileInput_move ( Iterator* this, int n );
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
 
_Bool 
                 isVerbose;
} Grammar;


Grammar* Grammar_new(void);


void Grammar_free(Grammar* this);


void Grammar_prepare ( Grammar* this );


void Grammar_setVerbose ( Grammar* this );


void Grammar_setSilent ( Grammar* this );


int Grammar_symbolsCount ( Grammar* this );


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



_Bool 
    Match_isSuccess(Match* this);



_Bool 
    Match_hasNext(Match* this);


Match* Match_getNext(Match* this);



_Bool 
    Match_hasChildren(Match* this);


Match* Match_getChildren(Match* this);


int Match_getOffset(Match* this);


int Match_getLength(Match* this);


int Match_getEndOffset(Match* this);





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




_Bool 
            ParsingElement_Is(void* this);





ParsingElement* ParsingElement_new(Reference* children[]);


void ParsingElement_freeChildren(ParsingElement* this);


void ParsingElement_free(ParsingElement* this);

ParsingElement* ParsingElement_Ensure(void* referenceOfElement);




ParsingElement* ParsingElement_add(ParsingElement* this, Reference* child);


ParsingElement* ParsingElement_clear(ParsingElement* this);




size_t ParsingElement_skip(ParsingElement* this, ParsingContext* context);





Match* ParsingElement_process( ParsingElement* this, Match* match );




ParsingElement* ParsingElement_name( ParsingElement* this, const char* name );


const char* ParsingElement_getName( ParsingElement* this );


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
typedef struct TokenConfig {
 char* expr;

 pcre* regexp;
 pcre_extra* extra;

} TokenConfig;


typedef struct TokenMatch {
 int count;
 const char** groups;
} TokenMatch;




ParsingElement* Token_new(const char* expr);


void Token_free(ParsingElement*);



Match* Token_recognize(ParsingElement* this, ParsingContext* context);


const char* Token_expr(ParsingElement* this);



void TokenMatch_free(Match* match);


const char* TokenMatch_group(Match* match, int index);


int TokenMatch_count(Match* match);
typedef struct Reference {
 char type;
 int id;
 char* name;
 char cardinality;
 struct ParsingElement* element;
 struct Reference* next;
} Reference;

_Bool 
    Reference_Is(void* this);





_Bool 
    Reference_IsMany(void* this);



Reference* Reference_Ensure(void* elementOrReference);



Reference* Reference_FromElement(ParsingElement* element);



Reference* Reference_new(void);


void Reference_free(Reference* this);



Reference* Reference_cardinality(Reference* this, char cardinality);


Reference* Reference_name(Reference* this, const char* name);



_Bool 
    Reference_hasNext(Reference* this);



_Bool 
    Reference_hasElement(Reference* this);



_Bool 
    Reference_isMany(Reference* this);


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
typedef 
       _Bool 
            (*ConditionCallback)(ParsingElement*, ParsingContext*);


ParsingElement* Condition_new(ConditionCallback c);


Match* Condition_recognize(ParsingElement* this, ParsingContext* context);
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


Match* ParsingStats_registerMatch(ParsingStats* this, Element* e, Match* m);
typedef struct ParsingVariable {
 int depth;
 char* key;
 void* value;
 struct ParsingVariable* previous;
} ParsingVariable;


ParsingVariable* ParsingVariable_new(int depth, const char* key, void* value);


void ParsingVariable_free(ParsingVariable* this);


void ParsingVariable_freeAll(ParsingVariable* this);



_Bool 
    ParsingVariable_is(ParsingVariable* this, const char* key);


ParsingVariable* ParsingVariable_set(ParsingVariable* this, const char* name, void* value);


void* ParsingVariable_get(ParsingVariable* this, const char* name);


ParsingVariable* ParsingVariable_find(ParsingVariable* this, const char* key, 
                                                                             _Bool 
                                                                                  local);


int ParsingVariable_getDepth(ParsingVariable* this);


const char* ParsingVariable_getName(ParsingVariable* this);


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
 
_Bool 
                        freeIterator;
} ParsingContext;






ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator );


char* ParsingContext_text( ParsingContext* this );



char ParsingContext_charAt ( ParsingContext* this, size_t offset );


size_t ParsingContext_getOffset( ParsingContext* this );


void ParsingContext_free( ParsingContext* this );



void ParsingContext_push ( ParsingContext* this );




void ParsingContext_pop ( ParsingContext* this );



void* ParsingContext_get(ParsingContext* this, const char* name);


int ParsingContext_getInt(ParsingContext* this, const char* name);


void ParsingContext_set(ParsingContext* this, const char* name, void* value);


void ParsingContext_setInt(ParsingContext* this, const char* name, int value);


void ParsingContext_on(ParsingContext* this, ContextCallback callback);


int ParsingContext_getVariableCount(ParsingContext* this);


Match* ParsingContext_registerMatch(ParsingContext* this, Element* e, Match* m);


typedef struct ParsingResult {
 char status;
 Match* match;
 ParsingContext* context;
} ParsingResult;


ParsingResult* ParsingResult_new(Match* match, ParsingContext* context);



void ParsingResult_free(ParsingResult* this);



_Bool 
    ParsingResult_isSuccess(ParsingResult* this);



_Bool 
    ParsingResult_isFailure(ParsingResult* this);



_Bool 
    ParsingResult_isPartial(ParsingResult* this);


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



_Bool 
    Utilites_checkIndent( ParsingElement* this, ParsingContext* context );
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

void gc_acquire( void* ptr );

void gc_release( void* ptr );
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


_Bool 
    Iterator_open( Iterator* this, const char *path ) {
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


_Bool 
    Iterator_hasMore( Iterator* this ) {
 size_t remaining = Iterator_remaining(this);


 return remaining > 0;
}

size_t Iterator_remaining( Iterator* this ) {
 int buffer_offset = ((char*)this->current - this->buffer);

 int remaining = this->available - buffer_offset;
 assert(remaining >= 0);

 return (size_t)remaining;
}


_Bool 
    Iterator_moveTo ( Iterator* this, size_t offset ) {
 return this->move(this, offset - this->offset );
}


_Bool 
    Iterator_backtrack ( Iterator* this, size_t offset, size_t lines ) {
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

_Bool 
    String_move ( Iterator* this, int n ) {
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
  size_t read = fread((char*)this->buffer + this->available, sizeof(char), to_read, input->file);
  this->available += read;
  left += read;
  ;;
  assert(Iterator_remaining(this) == left);
  assert(Iterator_remaining(this) >= read);
  if (read == 0) {
    ;;
   this->status = '.';
  }
 }
 return left;
}


_Bool 
    FileInput_move ( Iterator* this, int n ) {
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


 

  n = ((int)this->capacity )+ n < 0 ? 0 - (int)this->capacity : n;
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
 return this;
}

void Grammar_setVerbose ( Grammar* this ) {
 this->isVerbose = 1;
}

void Grammar_setSilent ( Grammar* this ) {
 this->isVerbose = 0;
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
 Match* this = Match_new();
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
   assert(ParsingElement_Is(this->element));


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

  if (this!=NULL) {; gc_free(this); } ;
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


_Bool 
    Match_isSuccess(Match* this) {
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



_Bool 
    Match_hasNext(Match* this) {
 return this != NULL && this->next != NULL;
}

Match* Match_getNext(Match* this) {
 return this != NULL ? this->next : NULL;
}


_Bool 
    Match_hasChildren(Match* this) {
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
  if (ref->cardinality == '1' || ref->cardinality == '?') {
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
 } else {
  dprintf(fd,"\"ERROR:unsupported element type=%c\"",element->type);
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
  if (ref->cardinality == '1' || ref->cardinality == '?') {
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
 } else {
  dprintf(fd,"<error t=\"Unsupported element type\" type=\"%c\" />",element->type);
 }
}

void Match_printXML(Match* this) {
 Match_writeXML(this, 1);
}

void Match_writeXML(Match* this, int fd ) {
 dprintf(fd,"%s","<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\" ?>\n");
 Match__writeXML(this, fd, 0);
}








_Bool 
    ParsingElement_Is(void *this) {
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
 this->freeMatch = NULL;
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
   Token_free(this);
   break;
  case 'W':
   Word_free(this);
   break;
  default:
   if (this!=NULL) {if (this->name!=NULL) {; gc_free(this->name); } };
   if (this!=NULL) {; gc_free(this); } ;
 }
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

Match* ParsingElement_process( ParsingElement* this, Match* match ) {
 return match;
}

size_t ParsingElement_skip( ParsingElement* this, ParsingContext* context) {
 if (this == NULL || context == NULL || context->grammar->skip == NULL || context->flags & 0x1) {return 0;}
 context->flags=context->flags|0x1;;
 ParsingElement* skip = context->grammar->skip;
 size_t offset = context->iterator->offset;

 Match* match = skip->recognize(skip, context);
 match = Match_free(match);
 size_t skipped = context->iterator->offset - offset;
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

const char* ParsingElement_getName( ParsingElement* this ) {
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








_Bool 
    Reference_Is(void * this) {
 return this!=NULL && ((Reference*)this)->type == '#';
}


_Bool 
    Reference_IsMany(void * this) {
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


_Bool 
    Reference_hasElement(Reference* this) {
 return this->element != NULL;
}


_Bool 
    Reference_hasNext(Reference* this) {
 return this->next != NULL;
}


_Bool 
    Reference_isMany(Reference* this) {

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


 
_Bool 
     is_success = Match_isSuccess(result) ? 1 : 0;
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

  free((void*)config->word);
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
 this->freeMatch = TokenMatch_free;



 config->expr = gc_strdup(expr) ; assert (config->expr!=NULL); ;

 const char* pcre_error;
 int pcre_error_offset = -1;
 config->regexp = pcre_compile(config->expr, PCRE_UTF8, &pcre_error, &pcre_error_offset, NULL);
 if (pcre_error != NULL) {
  fprintf(stderr, "ERR ");fprintf(stderr, "Token: cannot compile regular expression `%s` at %d: %s", config->expr, pcre_error_offset, pcre_error);fprintf(stderr, "\n");;
  if (config!=NULL) {; gc_free(config); } ;
  if (this!=NULL) {; gc_free(this); } ;
  return NULL;
 }

 config->extra = pcre_study(config->regexp, PCRE_STUDY_JIT_COMPILE, &pcre_error);
 if (pcre_error != NULL) {
  fprintf(stderr, "ERR ");fprintf(stderr, "Token: cannot optimize regular expression `%s` at %d: %s", config->expr, pcre_error_offset, pcre_error);fprintf(stderr, "\n");;
  if (config!=NULL) {; gc_free(config); } ;
  if (this!=NULL) {; gc_free(this); } ;
  return NULL;
 }

 this->config = config;
 assert(strcmp(config->expr, expr) == 0);
 assert(strcmp(Token_expr(this), expr) == 0);
 return this;
}


void Token_free(ParsingElement* this) {
 TokenConfig* config = (TokenConfig*)this->config;
 if (config != NULL) {


  if (config->regexp != NULL) {pcre_free(config->regexp);}
  if (config->extra != NULL) {pcre_free_study(config->extra);}

  if (config->expr!=NULL) {; gc_free(config->expr); } ;
  if (config!=NULL) {; gc_free(config); } ;
 }
 if (this!=NULL) {if (this->name!=NULL) {; gc_free(this->name); } };
 if (this!=NULL) {; gc_free(this); } ;
}

const char* Token_expr(ParsingElement* this) {
 return ((TokenConfig*)this->config)->expr;
}

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
 assert(this->config);
 if(this->config == NULL) {return FAILURE;}
 Match* result = NULL;

 TokenConfig* config = (TokenConfig*)this->config;

 int vector_length = 30;
 int vector[vector_length];
 const char* line = (const char*)context->iterator->current;

 int r = pcre_exec(
  config->regexp, config->extra,
  line,
  context->iterator->available,
  0,
    PCRE_ANCHORED
  | PCRE_NO_UTF8_CHECK
  | PCRE_NO_UTF16_CHECK
  | PCRE_NO_UTF32_CHECK,
  vector,
  vector_length);
 if (r <= 0) {

  switch(r) {
   case PCRE_ERROR_NOMATCH : result = FAILURE; break;
   case PCRE_ERROR_NULL : fprintf(stderr, "ERR ");fprintf(stderr, "Token:%s Something was null", config->expr);fprintf(stderr, "\n");; break;
   case PCRE_ERROR_BADOPTION : fprintf(stderr, "ERR ");fprintf(stderr, "Token:%s A bad option was passed", config->expr);fprintf(stderr, "\n");; break;
   case PCRE_ERROR_BADMAGIC : fprintf(stderr, "ERR ");fprintf(stderr, "Token:%s Magic number bad (compiled re corrupt?)", config->expr);fprintf(stderr, "\n");; break;
   case PCRE_ERROR_UNKNOWN_NODE : fprintf(stderr, "ERR ");fprintf(stderr, "Token:%s Something kooky in the compiled re", config->expr);fprintf(stderr, "\n");; break;
   case PCRE_ERROR_NOMEMORY : fprintf(stderr, "ERR ");fprintf(stderr, "Token:%s Ran out of memory", config->expr);fprintf(stderr, "\n");; break;
   default : fprintf(stderr, "ERR ");fprintf(stderr, "Token:%s Unknown error", config->expr);fprintf(stderr, "\n");; break;
  };
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "    %s└✘Token " "\033[1m\033[31m" "%s" "\033[0m" "#%d:`" "\033[36m" "%s" "\033[0m" "` failed at %zu:%zu", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset);fprintf(stdout, "\n");;};
 } else {
  if(r == 0) {
   fprintf(stderr, "ERR ");fprintf(stderr, "Token: %s many substrings matched\n", config->expr);fprintf(stderr, "\n");;





   r = vector_length / 3;
  }

  result = Match_Success(vector[1], this, context);
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, "[✓] %s└ Token " "\033[1m\033[32m" "%s" "\033[0m" "#%d:" "\033[36m" "`%s`" "\033[0m" " matched " "\033[1m\033[32m" "%zu:%zu-%zu" "\033[0m", context->indent, this->name, this->id, config->expr, context->iterator->lines, context->iterator->offset, context->iterator->offset + result->length);fprintf(stdout, "\n");;};


  TokenMatch* data = (TokenMatch*) gc_new(sizeof(TokenMatch)); assert (data!=NULL); ;
  data->count = r;
  const char** groups = (const char**) gc_calloc(r, sizeof(const char*)) ; assert (groups!=NULL); ;
  data->groups = groups;



  for (int j=0 ; j<r ; j++) {
   const char* substring;


   pcre_get_substring(line, vector, r, j, &(substring));
   data->groups[j] = substring;
  }
  result->data = data;
  context->iterator->move(context->iterator,result->length);
  assert (result->data != NULL);
  assert(Match_isSuccess(result));
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
  return m->groups[index];
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

 ;;
 if (match->data != NULL) {
  TokenMatch* m = (TokenMatch*)match->data;
  if (m != NULL ) {
   for (int j=0 ; j<m->count ; j++) {
    pcre_free_substring(m->groups[j]);
   }
  }
  if (m->groups!=NULL) {; gc_free(m->groups); } ;
 }

 if (match->data!=NULL) {; gc_free(match->data); } ;

}







ParsingElement* Group_new(Reference* children[]) {
 ParsingElement* this = ParsingElement_new(children);
 this->type = 'G';
 this->recognize = Group_recognize;
 return this;
}

Match* Group_recognize(ParsingElement* this, ParsingContext* context){


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
  return ParsingContext_registerMatch(context, (Element*)this, result);
 } else {

  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s╘═⇒ Group " "\033[1m\033[31m" "%s" "\033[0m" "#%d[%d] failed at %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, step, context->iterator->lines, context->iterator->offset, offset, context->depth);fprintf(stdout, "\n");;}
  result = Match_fail(result);
  if (context->iterator->offset != offset ) {
   Iterator_backtrack(context->iterator, offset, lines);
   assert( context->iterator->offset == offset );
  }
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
 } else {
  if(context->grammar->isVerbose && !(context->flags & 0x1)){fprintf(stdout, " !  %s╘ Rule " "\033[1m\033[31m" "%s" "\033[0m" "#%d failed on step %d=%s at %zu:%zu-%zu[→%d]", context->indent, this->name, this->id, step, step_name == NULL ? "-" : step_name, context->iterator->lines, offset, context->iterator->offset, context->depth);fprintf(stdout, "\n");;}

  result = Match_fail(result);

  if (offset != context->iterator->offset) {
   Iterator_backtrack(context->iterator, offset, lines);
   assert( context->iterator->offset == offset );
  }
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
  
 _Bool 
      value = ((ConditionCallback)this->config)(this, context);
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

const char* ParsingVariable_getName(ParsingVariable* this) {
 return (const char*)this->key;
}

void* ParsingVariable_get(ParsingVariable* this, const char* name) {
 ParsingVariable* found = ParsingVariable_find(this, name, 0);
 return found != NULL ? found->value : NULL;
}


_Bool 
    ParsingVariable_is(ParsingVariable* this, const char* key) {
 if (this == NULL || key == NULL) {return 0;}
 return (key == this->key || strcmp(this->key, key)) == 0 ? 1 : 0;
}

ParsingVariable* ParsingVariable_find(ParsingVariable* this, const char* key, 
                                                                             _Bool 
                                                                                  local) {
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
 return this;
}

void ParsingContext_free( ParsingContext* this ) {

 if (this!=NULL) {
  if (this->freeIterator) {Iterator_free(this->iterator);}
  ParsingVariable_freeAll(this->variables);
  ParsingStats_free(this->stats);
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

int ParsingContext_getInt(ParsingContext* this, const char* name) {
 return (int)(long)(ParsingVariable_get(this->variables, name));
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
 ParsingStats_registerMatch(this->stats, e, m);



 if (m != NULL && Match_isSuccess(m)) {
  if ( (this->lastMatchOffset + this->lastMatchLength) < (m->offset + m->length) && m->length > 0) {
   this->lastMatchOffset = m->offset;
   this->lastMatchLength = m->length;
   this->lastMatchElementID = m->element->id;
  }
 }
 return m;
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

Match* ParsingStats_registerMatch(ParsingStats* this, Element* e, Match* m) {
 return m;
}







ParsingResult* ParsingResult_new(Match* match, ParsingContext* context) {
 ParsingResult* this = (ParsingResult*) gc_new(sizeof(ParsingResult)); assert (this!=NULL); ;
 assert(match != NULL);
 assert(context != NULL);
 assert(context->iterator != NULL);
 this->match = match;
 this->context = context;
 if (match != FAILURE) {
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



_Bool 
    ParsingResult_isFailure(ParsingResult* this) {
 return this->status == 'F';
}


_Bool 
    ParsingResult_isPartial(ParsingResult* this) {
 return this->status == 'p';
}


_Bool 
    ParsingResult_isSuccess(ParsingResult* this) {
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
 r->id = r->id;
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


  Element** elements = (Element**) gc_calloc(this->skipCount + this->axiomCount + 1, sizeof(Element*)) ; assert (elements!=NULL); ;
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







void Utilities_indent( ParsingElement* this, ParsingContext* context ) {


}

void Utilities_dedent( ParsingElement* this, ParsingContext* context ) {


}


_Bool 
    Utilites_checkIndent( ParsingElement *this, ParsingContext* context ) {
 return 1;
}
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

void gc_acquire( void* ptr ) {



}

void gc_release( void* ptr ) {



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
