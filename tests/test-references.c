#include "../src/parsing.h"

void test_reference_creation() {
	ParsingElement*  word = Word_new("HELLO");
	Reference*        ref = Reference_New(word);
	if (ref->element == NULL) {
			printf("GFUCK\n");
	}
	// ASSERT(ref->element != (ParsingElement*)NULL, "Reference element is NULL")
}

int main () {
	test_reference_creation();
	return 0;
}

