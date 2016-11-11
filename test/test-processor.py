import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from libparsing import *

__doc__ = """
Tests the Python wrapper for the processing of matches. It should be
much faster than the pure-python processor.
"""

def grammar():
	"""We define a Lisp-ish grammar."""
	g = Grammar(isVerbose=False)
	s = g.symbols
	g.token("NUMBER",     "\d+(\.\d+)?")
	g.token("NAME",       "\w+")
	g.token("WHITESPACE", "\s+")
	g.token("SPACE", "\s*")
	g.word("LP",        "(")
	g.word("RP",        ")")
	g.group("Atom",     s.NUMBER, s.NAME)
	g.group("Value")
	g.rule ("List",    s.LP, s.Value.zeroOrMore(), s.RP)
	s.Value.set(s.List, s.Atom)
	g.axiom = s.Value
	g.skip  = s.WHITESPACE
	return g

def process( value=None, range=None, id=None ):
	"""The basic handler for `Match_processPython`, taking the matched
	value, the `(start,end)` range the corresponding element id."""
	return ("A:", value)

class Processor:

	def __init__(self, g):
		self._handlers = None
		self._grammar  = None
		self.setGrammar(g)

	def setGrammar( self, grammar ):
		g = grammar
		s = g.symbols
		h = {}
		n = 0
		l = []
		for k in dir(s):
			v = getattr(s,k)
			if isinstance(v, ParsingElement) and v.id >= 0:
				n = max(n, v.id + 1)
				h[v.id] = self._getHandler(v)
				l.append(v)
		self._handlers = [self._defaultHandler] * n
		for element in l:
			self._handlers[element.id] = self._getHandler(element)
		self._grammar  = grammar

	def process( self, match ):
		if isinstance(match, ParsingResult): match = match.match
		if isinstance(match, Match):
			return LIB.symbols.Match_processPython(match._cobject, self._handlers)
		else:
			return match

	def _defaultHandler( self, match=None, range=None, id=None ):
		return match

	def _getHandler( self, element ):
		name = element.name
		i    = element.id
		mname   = "on" + name[0].upper() + name[1:]
		mid     = "on" + str(i)
		handler = self._defaultHandler
		if hasattr(self, mname):
			handler = self._wrapHandler(getattr(self, mname))
		elif hasattr(self, mid):
			handler = self._wrapHandler(getattr(self, mid))
		return handler

	def _wrapHandler( self, function ):
		return lambda a,b,c:function(a)

	# CUSTOM HANDLERS

	def onNUMBER( self, match ):
		return int(match)

	def onNAME( self, match ):
		return repr(match)

	def onList( self, match ):
		return match[1]

def run():
	g = grammar() ; s = g.symbols
	p = g.parseString("((h as asdasds sadaasd) (w o r l d))")
	m = {} ; ids = 0
	callbacks = [lambda x,y,z:process(x)] * 100
	a = LIB.symbols.Match_processPython(p.match._cobject, callbacks)
	print ("a", a)
	b = Processor(g).process(p.match)
	print ("b", b)

if __name__ == "__main__":
	run()

# EOF
