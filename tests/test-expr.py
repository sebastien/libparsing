import sys, os, reporter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from  parsing import Grammar, Token, Word, Rule, Group, Condition, Procedure, Processor, NOTHING

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

class EP(Processor):

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

if __name__ == "__main__":
	reporter.install()
	match = g.parsePath(__file__.replace(".py", ".txt"))
	p     = EP(g)
	p.process(match)

# EOF
