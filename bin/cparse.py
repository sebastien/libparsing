#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : cparse
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2014-12-18
# Last modification : 2016-11-15
# -----------------------------------------------------------------------------
import os, sys, re, fnmatch
import reporter, texto, templating

VERSION = "0.0.0"
LICENSE = "http://ffctn.com/doc/licenses/bsd"

# TODO: The parser has some issues with comment-out functions

# START:DOC
__doc__ = """
== cparse
-- A C documentation and FFI generation utility

`cparse` extracts structure from specifically formatted C header files,
allowing to generate API documentation & Python CFFI data files.

The format is relatively simple: documentation and API is extracted from
comment strings put in the given header files. The documentation is expected to
be formatted in the `texto` (markdown-like) markup language.

You can see an example here <http://github.com/sebastien/parsing/src/parsing.h>
and the generated documentation <http://github.com/sebastien/parsing/parsing.html>.

Usage
=====

```
cparse include/header1.h include/header2.h
cparse include/header1.h include/header2.h
cparse include/header1.h include/header2.h  documentation.texto
cparse include/header1.h include/header2.h  documentation.html
cparse include/header1.h include/header2.h  documentation.ffi
```

Outputs
=======

`.ffi`::
	outputs a subset of the header that should be parseable by Python's CFFI

`.html`::
	outputs an HTML-formatted document designed ass an API reference

`.md`::
	outputs `markdown`-formatted text with the annotated bits of code embedded

Annotation `.h` files
=====================

The way to annotate structural elements within the header file is to use
one-line comments of the following form:

>	// @<CLASSIFIER>

where `<CLASSIFIER>` is one of the following:

- `@define`
- `@macro`
- `@callback`
- `@singleton`
- `@shared`
- `@type`
- `@operation`
- `@constructor`
- `@destructor`
- `@method`

Here's an example:

>	// @type ParsingContext
>	typedef struct ParsingContext {
>		struct Grammar*       grammar;      // The grammar used to parse
>		struct Iterator*      iterator;     // Iterator on the input data
>		struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
>		struct ParsingOffset* current;      // The current parsing offset
>	} ParsingContext;

"""
# END:DOC

RE_DOC_LINE    = re.compile("\s*//(.*)")
RE_DOC_START   = re.compile("/\*\*?(.*)")
RE_DOC_BODY    = re.compile("\s*\*+\s*(.*)")
RE_DOC_END     = re.compile("\s*\*+/()")
RE_STRUCTURE   = re.compile("\s*@(\w+)\s*")
RE_EMPTY       = re.compile("^\s*$")
RE_ANNOTATION  = re.compile("^\s*(TODO|FIXME|SEE|NOTE).+")
RE_DELIMITER   = re.compile("^\s*\[(START|END)\:[A-Z]+\]\s*$")

RE_MACRO       = re.compile("#define\s+(\w+)")
RE_RETURN      = re.compile("\s*(\w+)")
RE_FUNCTION    = re.compile("\s*(static|const|extern|inline)?\s*[\w_]+\s*[\*]*\s+([\w\_]+)")
RE_STRUCT      = re.compile("\s*typedef\s+struct\s+([\w_]+)")
RE_CALLBACK    = re.compile("\s*typedef\s+\w[\w\d_]*\s*\*?\s+\(\s*\*([\w\_]+)\s*\)")
RE_TYPEDEF     = re.compile("\s*typedef\s+\w[\w\d_]*\s*\*?\s+\s*([\w\_]+)\s*")
RE_SINGLE      = re.compile("\s*(static|extern)\s+\w+\s+([\w_]+)")

TYPE_SYMBOL    = "SYM"
TYPE_DOC       = "DOC"
TYPE_CODE      = "CDE"
TYPE_FILE      = "FLE"

SYMBOL_EXTRACTORS = dict(
	define      = RE_MACRO,
	macro       = RE_MACRO,
	singleton   = RE_SINGLE,
	callback    = RE_CALLBACK,
	shared      = RE_FUNCTION,
	type        = RE_STRUCT,
	typedef     = RE_TYPEDEF,
	operation   = RE_FUNCTION,
	constructor = RE_RETURN,
	destructor  = RE_FUNCTION,
	method      = RE_FUNCTION,
)

HTML_PAGE = """
<!DOCTYPE html>
<html>
	<head>
		<meta charset="utf-8" />
		<title>${library} &mdash; API</title>
		<!--
		<link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.4/styles/default.min.css">
		<script src="http://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.4/highlight.min.js"></script>
		-->
		<style>${css}</style>
		<script>${js}</script>

	<body>
		<div class="API use-texto use-base">
			<div class="documentation" style="margin-left:250px;">
				<div class="document">
				${body}
				</div>
			</div>
		</div>
	</body>
</html>
"""

def strip(lines):
	while lines and RE_EMPTY.match(lines[0]):  lines = lines[1:]
	while lines and RE_EMPTY.match(lines[-1]): lines = lines[:-1]
	return lines

class Library:

	def __init__( self, path=None ):
		self.symbols = {}
		self.files   = []
		self.groups  = []
		self.parse(path)

	def parse( self, *paths ):
		for path in paths:
			if not path: continue
			with file(path, "r") as f:
				self.addGroups(Parser.Groups(Parser.Lines(f.read())))
		return self

	def addGroups( self, groups ):
		self.groups += groups
		for g in groups:
			if g.type == TYPE_SYMBOL:
				self.symbols.setdefault(g.name, {})[g.classifier] = g
		return self

	def getSymbols( self, pattern, classifiers=None ):
		if classifiers and type(classifiers) not in (list, tuple): classifiers = list(classifiers)
		assert type(pattern) in (unicode, str)
		symbols = [_ for _ in self.groups if _.type == TYPE_SYMBOL and fnmatch.fnmatch(_.name, pattern)]
		if classifiers: symbols = [_ for _ in symbols if _.classifier in classifiers]
		return symbols

	def getSymbolsCode( self, pattern, classifiers=None ):
		return "\n".join(("\n".join(_.code) for _ in self.getSymbols(pattern, classifiers)))

	def getCode( self, *args ):
		res = []
		for p,c in args:
			res.append(self.getSymbolsCode(p,c))
		return "\n".join(res)


class Group:

	ID = 0

	def __init__( self, type=None, name=None, code=None, doc=None, classifier=None, start=0):
		self.id   = Group.ID ; Group.ID += 1
		self.type = type
		self.name = name
		self.code = code
		self.start = start
		self.doc  = [] if doc  is None else doc
		self.code = [] if code is None else code
		self.classifier = classifier
		self.symbols    = {}

	def getCode( self, name ):
		return "\n".join(self.symbols[name].code)

	def __repr__( self ):
		return "<Group#{5}:type={0},name={1},classifier={2},start={3}@{4}>".format(self.type, self.name, self.classifier, self.start, id(self), self.id)

class Parser:

	@classmethod
	def Lines( cls, text ):
		"""Iterates through the given text's lines, yielding
		`(number, type, line)` triples."""
		counter = 0
		for line in text.split("\n"):
			m = [m.group(1) for m in (_.match(line) for _ in (RE_DOC_LINE, RE_DOC_START, RE_DOC_BODY, RE_DOC_END)) if m]
			if m:
				s = RE_STRUCTURE.match(m[0])
				if s:
					t,l = TYPE_SYMBOL, s.group(1)
				else:
					t,l = TYPE_DOC, m[0]
					if RE_ANNOTATION.match(l) or l == "/":
						t,l = None, None
			else:
				t,l = TYPE_CODE, line
			if t == TYPE_DOC and RE_DELIMITER.match(l):
				t = l = None
			if t == TYPE_DOC and l == "[END]":
				break
			counter += 1
			if t != None and l != None:
				yield counter, t, l

	@classmethod
	def Groups( cls, lines ):
		"""Creates groups out of the lines generated by `ParseLines`"""
		mode    = None
		current = root = Group(type=TYPE_FILE)
		result = [current]
		lines  = list(lines)
		for i,t,l in lines:
			if   t == TYPE_SYMBOL:
				current = Group(
					type       = TYPE_SYMBOL,
					classifier = l.strip(),
					start      = i,
				)
				result.append(current)
			elif t == TYPE_DOC:
				if not current.code:
					current.doc.append(l)
				else:
					current  = Group(
						type = TYPE_FILE,
						doc  = [l],
						start = i,
					)
					result.append(current)
			elif t == TYPE_CODE:
				current.code.append(l)
			else:
				assert None
		# Now we post_process groups
		r = []
		for i,group in enumerate(result):
			if group.type == TYPE_SYMBOL:
				first_line = None
				try:
					first_line  = (_ for _ in group.code if _).next()
				except StopIteration:
					reporter.error("Group has no code: {0}".format(group))
				if first_line:
					match       = SYMBOL_EXTRACTORS[group.classifier].match(first_line)
					assert match, "Symbol extractor {0} cannot match {1}".format(group.classifier, first_line)
					group.name = match.groups()[-1]
					root.symbols[group.name] = group
					r.append(group)
				else:
					reporter.warn("Filtered out empty group: {0} at {1}".format(group, lines[group.start]))
		return r

class Formatter:

	def format( self, library ):
		index = []
		body  = []
		# The .h file usually starts with a preamble that we'd like to skip
		has_doc = 0
		indent_doc = ""
		for group in library.groups:
			d = []
			if group.name:
				# l  = '\n[#%s_%s]<span class="classifier">%s</span> `%s`::' % (group.name, group.classifier, group.classifier, group.name)
				l  = '\n#### <a name="%s_%s"><span class="classifier">%s</span> `%s`</a>' % (group.name, group.classifier, group.classifier, group.name)
				d.append(l)
				d.append("")
				indent_doc = "\t"
			else:
				indent_doc = ""
			if group.doc:
				if has_doc > 0: d.append((u"\n" + indent_doc).join(group.doc))
				has_doc += 1
			if group.code and has_doc > 1:
				code = strip([] + group.code)
				if code:
					code = "\n".join(code)
					code = "```c\n" + code + "\n```"
					d.append("\n" + code + "\n")
			body.append("\n".join(d))
		# We skip leading whitespace
		body = strip(body)
		return "\n".join(body)

def parse( *paths ):
	lib = Library()
	for _ in paths:
		lib.parse(_)
	return lib

if __name__ == "__main__":
	args = sys.argv[1:]
	# reporter.install(reporter.StderrReporter)
	lib  = Library()
	for p in args:
		with open(p) as f:
			text   = f.read()
			groups = Parser.Groups(Parser.Lines(text))
			lib.addGroups(groups)
	body = Formatter().format(lib)
	# NOTE: This cannot be replicated as-is
	body = body.decode("utf-8")
	print (body)

# EOF - vim: ts=4 sw=4 noet
