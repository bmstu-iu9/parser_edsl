#!/usr/bin/env python3

import sys
sys.path.append('..')

from example_lexer import scan, T as Tag
from parser_edsl import NTerm

tokens = list(scan("(3+2)*10+(42+15)*pi"))

E = NTerm()
T = NTerm()
F = NTerm()

vars = { "pi" : 3.14, "e" : 2.71 }

E += T | E << Tag.PLUS << T << (lambda x, y: x + y) | E << Tag.MINUS << T << (lambda x, y: x - y)
T += F | T << Tag.MUL << F << (lambda x, y: x * y)
F += Tag.NUMBER | Tag.LP << E << Tag.RP | Tag.VARNAME << (lambda name: vars[name])

result = E.parse(tokens)
print(result)

