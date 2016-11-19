Ideas for Performance improvement
=================================

Fast line-based parsing
-----------------------

One cheap way to improve performance is to design parsers so that that don't 
recurse too much. One way to do this is to split the parser grammar in different
bits.

For instance, in PCSS, parsing blocks is recursive, so the longer the block
the longer it takes to parse (because of backtracking). However, if you're able
to split the parsing/processing in two phases:

1) Parse lines, yielding (indent, line)
2) Combine lines together in blocks

You would probably get better performance, while also being able to discard input
as soon as a line has matched.

This does not require any change in the current library but requires building the 
parses differently.

Terminals look-ahead
--------------------

Currently parsing goes top-down, from the axiom to the terminal, and checks
if the current iterated element matches the terminal. An optimization would
be to know which terminals are reachable from every symbol, returning them
in order and then testing them first. 

The parsing engine would then test each terminal until there is a match, recursively
finding each first child that reaches the matching terminal and then going up
in the hierarchy.

This would save the initial deep traversal from the axiom or close-to-axiom
symbols, which can happen a lot with complex grammars.

Parsing tables
--------------

At the end of the day, the PEG grammar should be "compilable" to a state machine,
and using a similiar infrastructure as terminals look-ahead, should be able
to precompile 256-chars matching tables for each of the state, allowing to quickly
know which rule would match for a given ASCII character input. Non-ascii characters
would need special handling.
