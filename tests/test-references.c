#include "../src/parsing.h"

void test_reference_creation() {
	ParsingElement*  word = Word_new("HELLO");
	Reference*        ref = Reference_New(word);
	ASSERT(ref->element != (ParsingElement*)NULL, "Reference element is NULL", NULL)
	ASSERT(ref->element == word,                  "Reference should wrap parsing element", NULL)
}

int main () {
	test_reference_creation();
	printf("[OK]");
	return 0;
}

