#include "src/parsing.h"

/**
 * Tests the PCRE library
*/
int main()
{

	// SEE: http://www.mitchr.me/SS/exampleCode/AUPG/pcre_example.c.html

	pcre*       regexp;
	pcre_extra* regexp_x;
	const char* pcre_error;
	int         pcre_error_offset;


	// QUESTION: Not sure if we should use add PCRE_NEWLINE_ANY
	// Creates the Regexp
	regexp   = pcre_compile("\\d+(\\.\\d+)?", PCRE_UTF8, &pcre_error, &pcre_error_offset, NULL);
	// Optimize the Regexp
	regexp_x = pcre_study(regexp, 0, &pcre_error);

	int vector_length = 30;
	int vector[vector_length];
	char *lines[] = {
		"1",
		"100",
		"100.0",
		"VAR 1",
		"VAR 100",
		"VAR 100.0",
		NULL
	};

	// We iterate through the lines and look for matches
	for (char **l = lines ; *l != NULL ; l++ ) {
		char* line = *l;
		printf("Trying: %s", line);
		int r = pcre_exec(
				regexp, regexp_x,       // Regex
				line, strlen(line),     // Line
				0,                      // Offset
				PCRE_ANCHORED,          // OPTIONS -- we do not skip position
				vector,                 // Vector of matching offsets
				vector_length);         // Number of elements in the vector
		if (r <= 0) {
			switch(r) {
				case PCRE_ERROR_NOMATCH      : printf("String did not match the pattern\n");        break;
				case PCRE_ERROR_NULL         : printf("Something was null\n");                      break;
				case PCRE_ERROR_BADOPTION    : printf("A bad option was passed\n");                 break;
				case PCRE_ERROR_BADMAGIC     : printf("Magic number bad (compiled re corrupt?)\n"); break;
				case PCRE_ERROR_UNKNOWN_NODE : printf("Something kooky in the compiled re\n");      break;
				case PCRE_ERROR_NOMEMORY     : printf("Ran out of memory\n");                       break;
				default                      : printf("Unknown error\n");                           break;
			};
		} else {
			if(r == 0) {
				printf("[!] Too many substring matched\n");
				// Set rc to the max number of substring matches possible.
				// FIMXE: Not sure what r is
				r = vector_length / 3;
			}
			// PCRE contains a handy function to do the above for you:
			for( int j=0; j<r; j++ ) {
				const char *match;
				pcre_get_substring(line, vector, r, j, &match);
				printf("Match(%2d/%2d): (%2d,%2d): '%s'\n", j, r-1, vector[j*2], vector[j*2+1], match);
				pcre_free_substring(match);
			}
		}
	}
	return 0;
}

// EOF
