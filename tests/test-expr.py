import sys, reporter
sys.path.insert(0, "src")
from  parsing import Grammar, Token, Word, Rule, Group, Condition, Procedure, NOTHING

reporter.install()
g = Grammar()
s = g.symbols

g.token("WS",       "\s+")
g.token("NUMBER",   "\d+(\.\d+)?")
g.token("VARIABLE", "\w+")
g.token("OPERATOR", "[\+\-\*/]")
g.group("Value",     s.NUMBER, s.VARIABLE)
g.rule("Suffix",     s.OPERATOR._as("operator"), s.Value._as("value"))
g.rule("Expression", s.Value, s.Suffix.zeroOrMore())
g.axiom(s.Expression)
g.skip(s.WS)

class Processor:

	def __init__( self, grammar ):
		self.symbols = grammar.list()
		self.symbolByName = {}
		self.symbolByID   = {}
		self.handlerByID  = {}
		self._bindSymbols()
		self._bindHandlers()

	def _bindSymbols( self ):
		for n, s in self.symbols:
			if not s:
				reporter.error("[!] Name without symbol: %s" % (n))
				continue
			self.symbolByName[s.name()] = s
			self.symbolByID[s.id()]     = s

	def _bindHandlers( self ):
		for k in dir(self):
			if not k.startswith("on"): continue
			name = k[2:]
			# assert name in self.symbolByName, "Handler does not match any symbol: {0}".format(k)
			symbol = self.symbolByName[name]
			self.handlerByID[symbol.id()] = getattr(self, k)

	def process( self, match ):
		# res = [self.walk(_) for _ in match.children()]
		#print "MATCH", match.element().name(), ":", res, self._handle(match)
		return self._handle(match)

	def _handle( self, match ):
		eid = match.element().id()
		handler = self.handlerByID.get(eid)
		if handler:
			kwargs = {}
			for m in match.children():
				e = m.element()
				n = e.name()
				if n: kwargs[n] = self.process(m)
			if match.isFromReference():
				return handler(match, **kwargs)
			else:
				return handler(match, **kwargs)
		else:
			# If we don't have a handler, we recurse
			m = [self._handle(m) for m in match.children()]
			if match.isFromReference():
				r = match.element()
				if r.isOptional():
					return m[0]
				elif r.isOne():
					return m[0]
				else:
					return m
			else:
				return m

	def onNUMBER( self, match ):
		return int(match.group())

	def onVARIABLE( self, match ):
		return match.group()

	def onOPERATOR( self, match ):
		return match.group()

	def onValue( self, match ):
		value = self.process(match[0])
		return value

	def onSuffix( self, match, value, operator  ):
		return (value, operator)

	def onExpression( self, match ):
		value    = self.process(match[0])
		suffixes = self.process(match[1])
		print ("Expression", value, suffixes)

match = g.parsePath("expr.txt")
def walk(match, step):
	print step, match.element().id(), match.element().name(), match.range()
	return step
#match.walk(walk)
p = Processor(g)
p.process(match)
import ipdb
# ipdb.set_trace()

# EOF
