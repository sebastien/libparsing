extern int started;

typedef struct {
	char        type;
	const char* name;
	float       value;
} TestResult;

typedef TestResult (test*) (void) test_t;

TestResult test_run (test_t);

