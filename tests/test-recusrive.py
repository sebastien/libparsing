#!/usr/bin/env python2.7
# encoding: utf8
import os, sys ; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/python")
from libparsing import *

__doc__ = """
Ensures that `libparsing` detects situations that might make the parsing
engine loop infinitely.

The main criteria is that you'll have a loop if a rule can be reached by following
the children that do not consume input.
"""


# EOF - vim: ts=4 sw=4 noet
