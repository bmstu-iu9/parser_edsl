#!/usr/bin/env python3

import sys
sys.path.append('..')

from example_lexer import scan, T as Tag
from parser_edsl import NTerm

tokens = list(scan("""
PRINT \"Hello, world!\";
READ X, Y;
Z = 50;
W = X * Y * Z - 20;
PRINT \"Complete\";
PRINT W
"""))

vars = { }

Operator = NTerm()
Program = NTerm()
InputOperator = NTerm()
PrintOperator = NTerm()
AssignOperator = NTerm()
Variable = NTerm()
Expression = NTerm()
ExprTerm = NTerm()
Factor = NTerm()

Program += Operator | Program << Tag.SEMICOLON << Operator
Operator += InputOperator | PrintOperator | AssignOperator
InputOperator += Tag.READ << Tag.VARNAME << (lambda x: vars.update({x: int(input(x + " = "))})) | InputOperator << Tag.COMMA << Tag.VARNAME << (lambda x: vars.update({x: int(input(x + " = "))})) 
PrintOperator += Tag.PRINT << Expression << (lambda x: print(x)) | Tag.PRINT << Tag.STRING << (lambda x: print(x)) | PrintOperator << Tag.COMMA << Expression << (lambda x: print(" " + str(x).strip())) | PrintOperator << Tag.COMMA << Tag.STRING << (lambda x: print(" " + str(x).strip()))
AssignOperator += Tag.VARNAME << Tag.SET << Expression << (lambda x, y: vars.update({x: y}))
Variable += Tag.VARNAME << (lambda x: vars[x])

Expression += ExprTerm | Expression << Tag.PLUS << ExprTerm << (lambda x, y: x + y) | Expression << Tag.MINUS << ExprTerm << (lambda x, y: x - y)
ExprTerm += Factor | ExprTerm << Tag.MUL << Factor << (lambda x, y: x * y) | ExprTerm << Tag.DIV << Factor << (lambda x, y: x / y)
Factor += Tag.NUMBER | Variable << (lambda x: x) | Tag.LP << Expression << Tag.RP

Program.parse(tokens)

