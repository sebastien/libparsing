# NOTE: To do profiling, use operf & opreport
PROJECT  = parsing
VERSION  = $(shell grep VERSION src/parsing.h | cut -d'"' -f2)
MAJOR    = $(shell echo $(VERSION) | cut -d. -f1)
SOURCES  = $(wildcard src/*.c)
HEADERS  = $(wildcard src/*.h)
TESTS    = $(wildcard tests/test-*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
OBJECTS += $(TESTS:tests/%.c=build/%.o)
PRODUCTS = lib$(PROJECT) lib$(PROJECT).so.$(VERSION) python/lib$(PROJECT)/_lib$(PROJECT).so README.html
TEST_PRODUCTS = $(TESTS:tests/%.c=%)
CC       = gcc
LIBS    := libpcre
#CFLAGS  += -Isrc -std=c11 -O3 -Wall -fPIC -DWITH_PCRE -g -pg -DDEBUG_ENABLED
CFLAGS  += -Isrc -std=c11 -Wall -fPIC -DWITH_PCRE -g -pg -DDEBUG_ENABLED -DTRACE_ENABLED
LDFLAGS :=  $(shell pkg-config --cflags --libs $(LIBS))

# =============================================================================
# MAIN RULES
# =============================================================================

all: $(PRODUCTS)
	
clean:
	@find . -name __pycache__ -exec rm -rf '{}' ';' ; true
	@rm -rf dist *.egg-info $(OBJECTS) $(PRODUCTS) $(TEST_PRODUCTS); true

build:
	mkdir build

dist: libparsing update-python-version python/lib$(PROJECT)/_lib$(PROJECT).so
	python setup.py check clean sdist bdist 

info:
	@echo libparsing: $(VERSION)

release: $(PRODUCT) update-python-version python/lib$(PROJECT)/_lib$(PROJECT).so
	python setup.py check clean
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py sdist bdist register upload

tests: $(TEST_PRODUCTS)

update-python-version: src/parsing.h
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' python/libparsing/__init__.py 

cppcheck: $(SOURCES) $(HEADER)
	# SEE: http://sourceforge.net/p/cppcheck/wiki/ListOfChecks/
	cppcheck --suppress=unusedFunction -Isrc --enable=all src/parsing.c

# =============================================================================
# PRODUCTS
# =============================================================================

libparsing: lib$(PROJECT).so lib$(PROJECT).so.$(VERSION)
	
lib$(PROJECT).so: build/parsing.o
	$(LD) -shared -lpcre $< -o $@

lib$(PROJECT).so.$(VERSION): build/parsing.o
	$(LD) -shared -lpcre $< -o $@

README.html: python/cdoclib.py src/parsing.h
	@python python/cdoclib.py src/parsing.h > $@

experiment/%: build/%.o build/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

test-%: build/test-%.o build/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

python/lib$(PROJECT)/_lib$(PROJECT).so: lib$(PROJECT).so
	cp $< $@

# =============================================================================
# OBJECTS
# =============================================================================

build/experiment-%.o: experiment/experiment-%.c src/parsing.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/test-%.o: tests/test-%.c src/parsing.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/%.c src/%.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

# EOF
