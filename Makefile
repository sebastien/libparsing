PROJECT  = parsing
VERSION  = $(shell grep VERSION src/parsing.h | cut -d'"' -f2)
MAJOR    = $(shell echo $(VERSION) | cut -d. -f1)
SOURCES  = $(wildcard src/*.c)
TESTS    = $(wildcard tests/test-*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
OBJECTS += $(TESTS:tests/%.c=build/%.o)
PRODUCTS = lib$(PROJECT).so.$(VERSION) $(TESTS:tests/%.c=%)
CC       = colorgcc
LIBS    := libpcre
CFLAGS  += -Isrc -std=c11 -g -O9 -Wall -fPIC 
#-DDEBUG_ENABLED
LDFLAGS := $(shell pkg-config --cflags --libs $(LIBS))

all: $(PRODUCTS)
	echo $(TESTS)

libparsing: lib$(PROJECT).so.$(VERSION)
	
# parsing: build/parsing.o
# 	$(CC) $< $(LDFLAGS) -o $@
# 	chmod +x $@

lib$(PROJECT).so.$(VERSION): build/parsing.o
	$(LD) -shared -lpcre $< -o $@

run: parsing
	./parsing

debug: parsing
	gdb ./parsing
	
experiment/%: build/%.o build/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

test-%: build/test-%.o build/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

clean:
	find . -name __pycache__ -exec rm -rf '{}' ';'
	rm $(OBJECTS) $(PRODUCTS) ; true


build:
	mkdir build

build/experiment-%.o: experiment/experiment-%.c src/parsing.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/test-%.o: tests/test-%.c src/parsing.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/%.c src/%.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@


# EOF
