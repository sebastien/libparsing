# -----------------------------------------------------------------------------
#
# C+Python Project Makefile
# =========================
#
# Updated: 2016-11-10
# Author:  FFunction <ffctn.com>
#
# -----------------------------------------------------------------------------#
# NOTE: To do profiling, use operf & opreport

# === CONFIGURATION ===========================================================

PROJECT        :=parsing
PY_MODULE      :=lib$(PROJECT)
VERSION        :=$(shell grep VERSION $(SOURCES)h/parsing.h | cut -d'"' -f2)
MAJOR          :=$(shell echo $(VERSION) | cut -d. -f1)
FEATURES       :=WITH_PCRE #WITH_PYTHON

# === PATHS== =================================================================

BUILD          =.build
DIST           =dist
SOURCES        =src
TESTS          =tests

# === TOOLS ===================================================================

PYTHON         ?=python2.7

# === SOURCES =================================================================

SOURCES_C      =$(wildcard $(SOURCES)/c/*.c)
SOURCES_H      =$(wildcard $(SOURCES)/h/*.h)
TESTS_C        =$(wildcard $(TESTS)/test-*.c)

# === BUILD FILES =============================================================

OBJECTS         =$(SOURCES_C:$(SOURCES)/c/%.c=$(BUILD)/%.o)
OBJECTS        +=$(TESTS_C:$(TESTS)/%.c=$(BUILD)/%.o)

PY_MODULE_SO    :=__$(PYMODULE).so

# === DIST FILES ==============================================================

DIST_BIN      = $(TESTS_C:(TESTS)/%.c=$(DIST)/%)
DIST_SO       = lib$(PROJECT) lib$(PROJECT).so.$(VERSION) $(SOURCES)/python/$(PY_MODULE)/$(PY_MODULE_SO)
DIST_FILES    = $(DIST_BIN) $(DIST_SO)

# === COMPILER FILES ==========================================================
#
CC       = gcc
LIBS    := libpcre # libpython$(PYTHON_VERSION)
CFLAGS  += -I$(SOURCES)h -O6 -Wall -fPIC $(FEATURES:%=-D%) -g #-DMEMCHECK_ENABLED -pg # -DDEBUG_ENABLED -DTRACE_ENABLED
LDFLAGS :=  $(shell pkg-config --cflags --libs $(LIBS))

# =============================================================================
# MAIN RULES
# =============================================================================

all: $(PRODUCTS)
	

clean:
	@find . -name __pycache__ -exec rm -rf '{}' ';' ; true
	@rm -rf $(DIST) *.egg-info $(OBJECTS) $(PRODUCTS) $(TEST_PRODUCTS); true

help: ## Displays a description of the different Makefile rules
	@echo "$(CYAN)★★★ $(PROJECT) Makefile ★★★$(RESET)"
	@grep -E -o '((\w|-)+):[^#]+(##.*)$$'  $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":|##"}; {printf "make \033[01;32m%-15s\033[0m🕮 %s\n", $$1, $$3}'

build:
	mkdir $(BUILD)

dist: libparsing update-python-version $(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).so
	$(PYTHON) setup.py check clean sdist bdist_wheel

info:
	@echo libparsing: $(VERSION)

release: $(PRODUCT) update-python-version $(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).so
	$(PYTHON) setup.py check clean
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	$(PYTHON) setup.py sdist bdist_wheel register upload

tests: $(TEST_PRODUCTS)

update-python-version: $(SOURCES)parsing.h
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' $(SOURCES)python/$(PY_MODULE)/__init__.py 

cppcheck: $(SOURCES) $(HEADER)
	# SEE: http://sourceforge.net/p/cppcheck/wiki/ListOfChecks/
	cppcheck --suppress=unusedFunction -Isrc --enable=all $(SOURCES)parsing.c

# =============================================================================
# PRODUCTS
# =============================================================================

libparsing: lib$(PROJECT).so lib$(PROJECT).so.$(VERSION)
	
lib%.so: $(BUILD)/%.o
	$(LD) -shared -lpcre $< -o $@

lib%.so.$(VERSION): $(BUILD)/%.o
	$(LD) -shared -lpcre $< -o $@

README.html: bin/cdoclib.py $(SOURCES)h/parsing.h
	@python bin/cdoclib.py $(SOURCES)h/parsing.h > $@

experiment/%: $(BUILD)%.o $(BUILD)/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

test-%: $(BUILD)test-%.o $(BUILD)/parsing.o
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

# =============================================================================
# PYTHON MODULE
# =============================================================================

$(SOURCES)python/$(PY_MODULE)/$(PY_MODULE).ffi: $(SOURCES)python/$(PY_MODULE)/__init__.py $(SOURCES)h/parsing.h
	rm -f $@
	cd $(SOURCES)python && python $(PY_MODULE)/__init__.py

$(SOURCES)python/$(PY_MODULE)/$(PY_MODULE_SO): $(PRODUCT_SO)
	cp $< $@

# =============================================================================
# OBJECTS
# =============================================================================

$(BUILD)/experiment-%.o: experiment/experiment-%.c $(SOURCES)h/parsing.h $(SOURCES)h/oo.h
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/test-%.o: tests/test-%.c $(SOURCES)h/parsing.h $(SOURCES)h/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: $(SOURCES)c/%.c $(SOURCES)h/%.h $(SOURCES)h/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@


# === HELPERS =================================================================

print-%:
	@echo $*=
	@echo $($*) | xargs -n1 echo | sort -dr

# EOF
