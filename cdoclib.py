import sys, re
import reporter, texto, templating
from pygments            import highlight
from pygments.lexers     import CLexer
from pygments.formatters import HtmlFormatter


__doc__ = """
Extracts structure from specifically formatted C header files, allowing to
generate documentation & Python CFFI data files.

The format is relatively simple: documentation is extracted from comments,
and is formatted in the `texto` (markdown-like) markup language.

Structural elements within the code base are prefixed with a classifier
definition, expressed in a comment. For instance:

>	// @type ParsingContext
>	typedef struct ParsingContext {
>		struct Grammar*       grammar;      // The grammar used to parse
>		struct Iterator*      iterator;     // Iterator on the input data
>		struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
>		struct ParsingOffset* current;      // The current parsing offset
>	} ParsingContext;

Here @type is the classifier, which can be one of the following:

- `@define`
- `@macro`
- `@singleton`
- `@shared`
- `@type`
- `@operation`
- `@constructor`
- `@destructor`
- `@method`

"""

RE_DOC_LINE    = re.compile("\s*//(.*)")
RE_DOC_START   = re.compile("/\*\*?(.*)")
RE_DOC_BODY    = re.compile("\s*\*+\s*(.*)")
RE_DOC_END     = re.compile("\s*\*+/()")
RE_STRUCTURE   = re.compile("\s*@(\w+)\s*")
RE_EMPTY       = re.compile("^\s*$")
RE_ANNOTATION  = re.compile("^\s*(TODO|FIXME|SEE|NOTE).+")

RE_MACRO       = re.compile("#define\s+(\w+)")
RE_RETURN      = re.compile("\s*(\w+)")
RE_FUNCTION    = re.compile("\s*(extern|inline)?[\w_]+\s*[\*]*\s+([\w\_]+)")
RE_STRUCT      = re.compile("\s*typedef\s+struct\s+([\w_]+)")
RE_SINGLE      = re.compile("\s*static\s+\w+\s+([\w_]+)")

TYPE_SYMBOL    = "S"
TYPE_DOC       = "D"
TYPE_CODE      = "C"
TYPE_FILE      = "F"

SYMBOL_EXTRACTORS = dict(
	define      = RE_MACRO,
	macro       = RE_MACRO,
	singleton   = RE_SINGLE,
	shared      = RE_FUNCTION,
	type        = RE_STRUCT,
	operation   = RE_FUNCTION,
	constructor = RE_RETURN,
	destructor  = RE_RETURN,
	method      = RE_FUNCTION,
)

HTML_PAGE = """
<!DOCTYPE html>
<html>
	<head>
		<meta charset="utf-8" />
		<title>${library} &mdash; API</title>
		<link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.4/styles/default.min.css">
		<link rel="stylesheet" href="http://sebastienpierre.ca/lib/css/base.css">
		<script src="http://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.4/highlight.min.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/jquery-2.0.3.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/extend-2.5.0.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/html-5.0.3.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/texto.js"></script>
		<style>${css}</style>
	<body>
		<div class="API use-texto use-base">
			<div class="hidden index to-w expand-h" style="position:fixed;overflow:auto;width:250px;">
				<ol>
				${for:groups}
				<li class="${this.classifier}"><a href="#${this.name}_${this.classifier}">${this.name}</a></li>
				${end}
				</ol>
			</div>
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
		if path:
			with file(path, "r") as f:
				self.addGroups(Parser.Groups(Parser.Lines(f.read())))

	def addGroups( self, groups ):
		self.groups += groups
		for g in groups:
			if g.type == TYPE_SYMBOL:
				self.symbols.setdefault(g.name, {})[g.classifier] = g
		return self

	def getSymbolCode( self, symbol, classifier ):
		return "\n".join(self.symbols[symbol][classifier].code)

	def getCode( self, *args ):
		return "\n".join((self.getSymbolCode(s,c) for (s,c) in args))

class Group:

	def __init__( self, type=None, name=None, code=None, doc=None, classifier=None ):
		self.type = type
		self.name = name
		self.code = code
		self.doc  = [] if doc  is None else doc
		self.code = [] if code is None else code
		self.classifier = classifier
		self.symbols    = {}

	def getCode( self, name ):
		return "\n".join(self.symbols[name].code)

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
			counter += 1
			if t != None and l != None:
				yield counter, t, l

	@classmethod
	def Groups( cls, lines ):
		"""Creates groups out of the lines generated by `ParseLines`"""
		mode    = None
		current = root = Group(type=TYPE_FILE)
		result = [current]
		for i,t,l in lines:
			if   t == TYPE_SYMBOL:
				current = Group(
					type       = TYPE_SYMBOL,
					classifier = l.strip(),
				)
				result.append(current)
			elif t == TYPE_DOC:
				if not current.code:
					current.doc.append(l)
				else:
					current  = Group(
						type = TYPE_FILE,
						doc  = [l],
					)
					result.append(current)
			elif t == TYPE_CODE:
				current.code.append(l)
		# Now we post_process groups
		for group in result:
			if group.type == TYPE_SYMBOL:
				try:
					first_line  = (_ for _ in group.code if _).next()
				except StopIteration:
					reporter.error("Cannot find code for type")
				match       = SYMBOL_EXTRACTORS[group.classifier].match(first_line)
				assert match, "Symbol extractor {0} cannot match {1}".format(group.classifier, first_line)
				group.name = match.groups()[-1]
				root.symbols[group.name] = group
		return result

class Formatter:

	def __init__( self ):
		self._codeLexer     = CLexer()
		self._codeFormatter = HtmlFormatter()

	def format( self, library ):
		index = []
		body  = []
		# The .h file usually starts with a preamble that we'd like to skip
		has_doc = 0
		for group in library.groups:
			d = []
			if group.name:
				l  = '\n[#%s_%s]`%s`' % (group.name, group.classifier, group.name)
				d.append(l)
				d.append("-" * len(l))
				d.append("")
			if group.doc:
				if has_doc > 0: d.append(u"\n".join(group.doc))
				has_doc += 1
			if group.code and has_doc > 1:
				code = strip([] + group.code)
				if code:
					code = "\n".join(code)
					# code = highlight(code, self._codeLexer, self._codeFormatter)
					code = "```c\n" + code + "\n```"
					d.append("\n" + code + "\n")
			body.append("\n".join(d))
		# We skip leading whitespace
		body = strip(body)
		return "\n".join(body)

if __name__ == "__main__":
	import ipdb
	args = sys.argv[1:] or ["src/parsing.h"]
	# reporter.install(reporter.StderrReporter)
	lib  = Library()
	for p in args:
		with open(p) as f:
			text   = f.read()
			# for line in Parser.Lines(text):
			# 	print line
			groups = Parser.Groups(Parser.Lines(text))
			lib.addGroups(groups)
	body = Formatter().format(lib)
	if False:
		print templating.Template(HTML_PAGE).apply(dict(
			css  = open("texto.css").read(),
			body = texto.toHTML(body),
			groups = [_ for _ in lib.groups if _.type == TYPE_SYMBOL]
		))
	else:
		print body
	# print lib.getSymbolCode("Iterator", "type")
	# with file("src/parsing.ffi", "w") as f:
	# 	f.write(lib.getSymbolCode("Reference",      "type"))
	# 	f.write(lib.getSymbolCode("Match",          "type"))
	# 	f.write(lib.getSymbolCode("ParsingElement", "type"))
	# 	f.write(lib.getSymbolCode("Grammar",        "type"))
	# 	# f.write(lib.getCode("Token",          "constructor"))
	# 	# f.write(lib.getCode("Word",           "constructor"))
	# 	# f.write(lib.getCode("Grammar",        "constructor"))

# EOF
