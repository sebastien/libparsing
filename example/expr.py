#!/usr/bin/env python2.7
# encoding: utf8
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from  libparsing import Grammar, Token, Word, Rule, Group, Condition, Procedure, Processor, NOTHING


def grammar( isVerbose=False ):
	"""Defines a grammar for simple artihmetic expressions calculation."""
	g = Grammar(isVerbose=isVerbose)
	s = g.symbols
	g.token("WS",       "\s+")
	g.token("NUMBER",   "\d+(\.\d+)?")
	g.token("VARIABLE", "\w+")
	g.token("OPERATOR", "[\+\-\*/]")
	g.group("Value",     s.NUMBER, s.VARIABLE)
	g.rule("Suffix",     s.OPERATOR._as("operator"), s.Value._as("value"))
	g.rule("Expression", s.Value, s.Suffix.zeroOrMore())
	g.axiom = s.Expression
	g.skip  = s.WS
	return g

class Processor(Processor):

	def onNUMBER( self, match ):
		return int(match.group())

	def onVARIABLE( self, match ):
		return match.group()

	def onOPERATOR( self, match ):
		return match.group()

	def onValue( self, match ):
		value = self.process(match[0])
		return value

	def onSuffix( self, match  ):
		return (match["value"], match["operator"])

	def onExpression( self, match ):
		value    = self.process(match[0])
		suffixes = self.process(match[1])
		return [value] + list(suffixes)

EXAMPLES = [
"10 + VAR"
]

if __name__ == "__main__":
	g      = grammar()
	g.prepare()
	p      = Processor(g)
	result = g.parseString(EXAMPLES[0])
	print (p.process(result))

# EOF
