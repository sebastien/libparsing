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
PYMODULE       :=lib$(PROJECT)
FEATURES       :=pcre python2
ALL_FEATURES   :=pcre python2 python3 memcheck debug trace

# === FEATURES ================================================================

LIBS=
ifneq (,$(findstring pcre,$(FEATURES)))
	LIBS +=libpcre
endif
ifneq (,$(findstring python2,$(FEATURES)))
	LIBS +=python2
endif
ifneq (,$(findstring python3,$(FEATURES)))
	LIBS +=python3
endif

# === PATHS ===================================================================

BUILD          =.build
DIST           =dist
SOURCES        =src
TESTS          =test

# === TOOLS ===================================================================

PYTHON         ?=python2.7

# === SOURCES =================================================================

SOURCES_C      =$(wildcard $(SOURCES)/c/*.c)
SOURCES_H      =$(wildcard $(SOURCES)/h/*.h)
SOURCES_PY     =$(wildcard $(SOURCES)/py/*.py) $(wildcard $(SOURCES)/py/*/*.py)
TESTS_C        =$(wildcard $(TESTS)/test-*.c)
TESTS_PY       =$(wildcard $(TESTS)/test-*.py)

# === BUILD FILES =============================================================

OBJECTS         =$(SOURCES_C:$(SOURCES)/c/%.c=$(BUILD)/%.o)
OBJECTS        +=$(TESTS_C:$(TESTS)/%.c=$(BUILD)/%.o)

PY_MODULE_SO    :=__$(PYMODULE).so

# === DIST FILES ==============================================================

DIST_BIN      = $(TESTS_C:$(TESTS)/%.c=$(DIST)/%)
DIST_SO       = $(DIST)/lib$(PROJECT).so $(DIST)/lib$(PROJECT).so.$(VERSION) 
DIST_FILES    = $(DIST_BIN) $(DIST_SO)

PRODUCTS      = $(DIST_FILES)

# === COMPILER FILES ==========================================================

CC       ?= gcc
CFEATURES =`echo $(FEATURES:%=-DWITH_%) | tr a-z A-Z`
CFLAGS   +=$(shell pkg-config --cflags $(LIBS))
CFLAGS   +=-I$(SOURCES)/h -O6 -Wall -fPIC $(CFEATURES) -g #-DMEMCHECK_ENABLED -pg # -DDEBUG_ENABLED -DTRACE_ENABLED
LDFLAGS  +=$(shell pkg-config --cflags --libs $(LIBS))

# === META ====================================================================

VERSION        :=$(shell grep VERSION $(SOURCES)/h/parsing.h | cut -d'"' -f2)
MAJOR          :=$(shell echo $(VERSION) | cut -d. -f1)

# === HELPERS =================================================================

YELLOW           =`tput setaf 11`
GREEN            =`tput setaf 10`
CYAN             =`tput setaf 14`
RED              =`tput setaf 1`
GRAY             =`tput setaf 7`
RESET            =`tput sgr0`

TIMESTAMP       :=$(shell date +'%F')
BUILD_ID        :=$(shell git rev-parse --verify HEAD)
MAKEFILE_PATH   := $(abspath $(lastword $(MAKEFILE_LIST)))
MAKEFILE_DIR    := $(notdir $(patsubst %/,%,$(dir $(MAKEFILE_PATH))))

# From: http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL   :=all
.PHONY          : all info dist release tests update-python-version check clean help

# =============================================================================
# MAIN RULES
# =============================================================================

all: $(PRODUCTS) ## Builds all the products
	

info: ## Displays information about the project
	@echo libparsing: $(VERSION)


dist: $(PRODUCT) $(DIST_FILES) ## Creates source and binary Python distributions
	$(PYTHON) setup.py check clean sdist bdist_wheel

release: $(PRODUCT) update-python-version $(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).so
	@echo "$(CYAN)📦  dist: $(RESET)"
	$(PYTHON) setup.py check clean
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	$(PYTHON) setup.py sdist bdist_wheel register upload

tests: $(TEST_PRODUCTS)

update-python-version: $(SOURCES)parsing.h
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' $(SOURCES)python/$(PYMODULE)/__init__.py 

check: $(SOURCES_C) $(SOURCES_H) ## Runs checks on the source code
	@# SEE: http://sourceforge.net/p/cppcheck/wiki/ListOfChecks/
	@echo "$(CYAN)📦  Checking: $(SOURCES_C) $(RESET)"
	@echo "$(RED)"
	@cppcheck --suppress=unusedFunction -Isrc/h --enable=all $(SOURCES_C)
	@echo "$(RESET)"
	@echo "$(CYAN)📦  Checking: $(SOURCES_PY) $(RESET)"
	@echo "$(RED)"
	@pychecker $(SOURCES_PY)
	@echo "$(RESET)"

clean: ## Cleans the build files
	@find . -name __pycache__ -exec rm -rf '{}' ';' ; true
	@rm -rf $(DIST) *.egg-info $(OBJECTS) $(PRODUCTS) $(TEST_PRODUCTS); true

help: ## Displays a description of the different Makefile rules
	@echo "$(CYAN)★★★ $(PROJECT) makefile ★★★$(RESET)"
	@grep -E -o '((\w|-)+):[^#]+(##.*)$$'  $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":|##"}; {printf "make \033[01;32m%-15s\033[0m🕮 %s\n", $$1, $$3}'

# =============================================================================
# PRODUCTS
# =============================================================================

$(DIST)/lib%.so: $(BUILD)/%.o
	@echo "$(GREEN)📝  $@ [LD]$(RESET)"
	@mkdir -p `dirname $@`
	$(LD) -shared -lpcre $< -o $@

$(DIST)/lib%.so.$(VERSION): $(BUILD)/%.o
	@echo "$(GREEN)📝  $@ [LD]$(RESET)"
	@mkdir -p `dirname $@`
	$(LD) -shared -lpcre $< -o $@

$(DIST)/test-%: $(BUILD)/test-%.o $(BUILD)/parsing.o
	@echo "$(GREEN)📝  $@ [CC ]$(RESET)"
	@mkdir -p `dirname $@`
	$(CC) $? $(LDFLAGS) -o $@
	chmod +x $@

# =============================================================================
# PYTHON MODULE
# =============================================================================

$(SOURCES)/python/$(PYMODULE)/$(PYMODULE_SO): $(PRODUCT_SO)
	cp $< $@

# =============================================================================
# OBJECTS
# =============================================================================

$(BUILD)/test-%.o: $(TESTS)/test-%.c $(SOURCES_H)
	@echo "$(GREEN)📝  $@ [CC TEST]$(RESET)"
	@mkdir -p `dirname $@`
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: $(SOURCES)/c/%.c $(SOURCES)/h/%.h $(SOURCES)/h/oo.h
	@echo "$(GREEN)📝  $@ [CC SOURCE]$(RESET)"
	@mkdir -p `dirname $@`
	$(CC) $(CFLAGS) -c $< -o $@

# === HELPERS =================================================================

print-%:
	@echo $*=
	@echo $($*) | xargs -n1 echo | sort -dr

# EOF
