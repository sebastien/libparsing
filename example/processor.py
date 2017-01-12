from libparsing import *

__doc__ = """
Shows how to reference named parsing element children in the `Processor`
subclasses. This grammar parses a simple Lisp-like language.
"""

def grammar(verbose=False):
	g = Grammar(isVerbose=verbose)
	s = g.symbols

	g.word("LP",           "(")
	g.word("RP",           ")")
	g.token("WHITESPACE",  "[\s\n]+")
	g.token("STRING",      "\"(^\"|\\\")\"")
	g.token("NUMBER",      "-?\d+(\.\d+)")
	g.token("NAME",        "[\w_][\w\d-]*")

	g.group("Litteral",  s.STRING, s.NUMBER, s.NAME)
	g.group("Value")
	g.rule ("List",      s.LP, s.Value.zeroOrMore()._as("content"), s.RP)
	s.Value.set(s.Litteral, s.List)
	g.group("Code",      s.List.zeroOrMore())

	g.axiom = s.List
	g.skip  = s.WHITESPACE

	return g

class Writer(Processor):

	def createGrammar( self ):
		return grammar()

	def onNUMBER( self, match ):
		return match.value()

	def onSTRING( self, match ):
		return match.value()

	def onNAME( self, match ):
		return match.value()

	def onList( self, match, content ):
		return (self.process(content))

if __name__ == "__main__":
	EXAMPLE1 = "()"
	EXAMPLE2 = '(print "Hello, World")'
	g = grammar()
	# NOTE: This segfaults
	r = g.parseString(EXAMPLE1)
	print r
	# w = Writer()
	# w.parse(EXAMPLE1)

# EOF
