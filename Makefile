PROJECT  = parsing
VERSION  = $(shell grep VERSION src/parsing.h | cut -d'"' -f2)
MAJOR    = $(shell echo $(VERSION) | cut -d. -f1)
SOURCES  = $(wildcard src/*.c)
TESTS    = $(wildcard tests/test-*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
OBJECTS += $(TESTS:tests/%.c=build/%.o)
PRODUCTS = lib$(PROJECT) lib$(PROJECT).so.$(VERSION) README.html
TEST_PRODUCTS = $(TESTS:tests/%.c=%)
CC       = colorgcc
LIBS    := libpcre
CFLAGS  += -Isrc -std=c11 -g -O9 -Wall -fPIC 
#-DDEBUG_ENABLED
LDFLAGS := $(shell pkg-config --cflags --libs $(LIBS))

# =============================================================================
# MAIN RULES
# =============================================================================

all: $(PRODUCTS)
	
clean:
	@find . -name __pycache__ -exec rm -rf '{}' ';'
	@rm -rf dist *.egg-info $(OBJECTS) $(PRODUCTS) $(TEST_PRODUCTS); true

build:
	mkdir build

dist: libparsing update-python-version python/libparsing/libparsing.ffi
	python setup.py check clean sdist bdist 

info:
	@echo libparsing: $(VERSION)

release: $(PRODUCT) update-python-version python/libparsing/libparsing.ffi
	python setup.py check clean
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py sdist bdist register upload

tests: $(TEST_PRODUCTS)

update-python-version: src/parsing.h
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' python/libparsing/__init__.py 

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

python/libparsing/libparsing.ffi: src/parsing.h
	rm -f $@
	cd python && python libparsing/__init__.py

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
