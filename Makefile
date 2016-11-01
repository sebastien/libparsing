# NOTE: To do profiling, use operf & opreport
PROJECT  = parsing
VERSION  = $(shell grep VERSION src/h/parsing.h | cut -d'"' -f2)
MAJOR    = $(shell echo $(VERSION) | cut -d. -f1)
SOURCES  = $(wildcard src/c/*.c)
HEADERS  = $(wildcard src/h/*.h)
TESTS    = $(wildcard tests/test-*.c)
OBJECTS  = $(SOURCES:src/c/%.c=build/%.o)
OBJECTS += $(TESTS:tests/%.c=build/%.o)
PY_MODULE:=libparsing
PY_MODULE_SO:=_libparsing.so
PRODUCT_SO:=lib$(PROJECT).so
TEST_PRODUCTS = $(TESTS:tests/%.c=%)
CC       = gcc
LIBS    := libpcre
#CFLAGS  += -Isrc/h -std=c11 -O3 -Wall -fPIC -DWITH_PCRE 
CFLAGS  += -Isrc/h -Wall -fPIC -DWITH_PCRE -g -pg -DDEBUG_ENABLED -DTRACE_ENABLED
LDFLAGS :=  $(shell pkg-config --cflags --libs $(LIBS))
PRODUCTS = lib$(PROJECT) lib$(PROJECT).so.$(VERSION) src/python/$(PY_MODULE)/$(PY_MODULE_SO)

# =============================================================================
# MAIN RULES
# =============================================================================

all: $(PRODUCTS)
	
clean:
	@find . -name __pycache__ -exec rm -rf '{}' ';' ; true
	@rm -rf dist *.egg-info $(OBJECTS) $(PRODUCTS) $(TEST_PRODUCTS); true

build:
	mkdir build

dist: libparsing update-python-version src/python/lib$(PROJECT)/_lib$(PROJECT).so
	python setup.py check clean sdist bdist_wheel

info:
	@echo libparsing: $(VERSION)

release: $(PRODUCT) update-python-version src/python/lib$(PROJECT)/_lib$(PROJECT).so
	python setup.py check clean
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py sdist bdist_wheel register upload

tests: $(TEST_PRODUCTS)

update-python-version: src/parsing.h
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' src/python/$(PY_MODULE)/__init__.py 

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

#README.html: tools/cdoclib.py src/h/parsing.h
#	@python tools/cdoclib.py src/h/parsing.h > $@

experiment/%: build/%.o build/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

test-%: build/test-%.o build/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

# =============================================================================
# PYTHON MODULE
# =============================================================================

src/python/$(PY_MODULE)/$(PY_MODULE).ffi: src/python/$(PY_MODULE)/__init__.py src/h/parsing.h
	rm -f $@
	cd src/python && python $(PY_MODULE)/__init__.py

src/python/$(PY_MODULE)/$(PY_MODULE_SO): $(PRODUCT_SO)
	cp $< $@

# =============================================================================
# OBJECTS
# =============================================================================

build/experiment-%.o: experiment/experiment-%.c src/h/parsing.h src/h/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/test-%.o: tests/test-%.c src/h/parsing.h src/h/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/c/%.c src/h/%.h src/h/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

# EOF
