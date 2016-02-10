#define TRACE_ENABLED 1
#include "../src/testing.h"
#include "../src/parsing.h"

void test_reference_creation() {
	ParsingElement*  word = Word_new("HELLO");
	Reference*        ref = Reference_Ensure(word);
	ASSERT(ref->element != (ParsingElement*)NULL, "Reference element is NULL: %p", NULL)
	ASSERT(ref->element == word,                  "Reference should wrap parsing element: %p", NULL)
	Reference_free(ref);
	Word_free(word);
}

int main () {
	test_reference_creation();
	printf("[OK]");
	return 0;
}

