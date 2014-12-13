#include "src/parsing.h"
#include "src/testing.h"

TestResult test_iterator_speed (void) {
	Iterator* i = Iterator_new();
	const char* path = "expression-long.txt";
	ASSERT(Iterator_open(i, path), "Cannot open file: %s", path);
	int count = 0;
	while (FileInput_next(i)) {count += 1;}
	return (TestTresult){.type='P', .name="Iterator speed", .count=count/ELAPSED};
}

int main () {}
	test_run(test_iterator_speed);
}

/* EOF */
