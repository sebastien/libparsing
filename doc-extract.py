import sys, re
import reporter

RE_DOC_LINE    = re.compile("\s*//(.*)")
RE_DOC_START   = re.compile("/\*\*?(.*)")
RE_DOC_BODY    = re.compile("\s*\*\s*(.*)")
RE_DOC_END     = re.compile("\*/()")
RE_STRUCTURE   = re.compile("\s*@(\w+)\s*")

RE_MACRO       = re.compile("#define\s+(\w+)")
RE_RETURN      = re.compile("\s*(\w+)")
RE_FUNCTION    = re.compile("\s*[\w_]+\s*[\*]*\s+([\w\_]+)")
RE_STRUCT      = re.compile("\s*typedef\s+struct\s+([\w_]+)")
RE_SINGLE      = re.compile("\s*static\s+\w+\s+([\w_]+)")

TYPE_SYMBOL    = "S"
TYPE_DOC       = "D"
TYPE_CODE      = "C"
TYPE_FILE      = "F"

SYMBOL_EXTRACTORS = dict(
	define      = RE_MACRO,
	macro       = RE_MACRO,
	constructor = RE_RETURN,
	destructor  = RE_RETURN,
	type        = RE_STRUCT,
	singleton   = RE_SINGLE,
	method      = RE_FUNCTION,
	operation   = RE_FUNCTION,
	shared      = RE_FUNCTION,
)

def split_text(text):
	counter = 0
	for line in text.split("\n"):
		m = [m.group(1) for m in (_.match(line) for _ in (RE_DOC_LINE, RE_DOC_START, RE_DOC_BODY, RE_DOC_END)) if m]
		if m:
			s = RE_STRUCTURE.match(m[0])
			if s:
				t,l = TYPE_SYMBOL, s.group(1)
			else:
				t,l = TYPE_DOC, m[0]
		else:
			print "ADDED CODE", repr(line)
			t,l = TYPE_CODE, line
		counter += 1
		yield counter, t, l

def create_groups( groups ):
	mode    = None
	current = dict(
		type = TYPE_FILE,
		name = None,
		doc  = [],
		code = [],
	)
	result = [current]
	for i,t,l in groups:
		if   t == TYPE_SYMBOL:
			current = dict(
				type       = TYPE_SYMBOL,
				classifier = l.strip(),
				name       = None,
				doc        = [],
				code       = [],
			)
			result.append(current)
		elif t == TYPE_DOC:
			if not current["code"]:
				current["doc"].append(l)
			else:
				current  = dict(
					type = TYPE_FILE,
					name = None,
					doc  = [l],
					code = [],
				)
				result.append(current)
		elif t == TYPE_CODE:
			current["code"].append(l)
	# Now we post_process groups
	for group in result:
		if group["type"] == TYPE_SYMBOL:
			try:
				first_line  = (_ for _ in group["code"] if _).next()
			except StopIteration:
				reporter.error("Cannot find code for type")
			match       = SYMBOL_EXTRACTORS[group["classifier"]].match(first_line)
			assert match, "Symbol extractor {0} cannot match {1}".format(group["classifier"], first_line)
			group["name"] = match.groups()[-1]
	return result

if __name__ == "__main__":
	import ipdb
	args = sys.argv[1:]
	reporter.install()
	for p in args:
		with open(p) as f:
			text   = f.read()
			groups = create_groups(split_text(text))
			for group in groups:
				if group["type"] == TYPE_SYMBOL:
					print "SYMBOL", group["classifier"], group["code"][0]

# EOF
