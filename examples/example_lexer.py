#!/usr/bin/env python3

import sys
sys.path.append('..')

from enum import Enum, auto
import functools
from typing import Callable
from parser_edsl import Symbol, DomainTag, Token

class T(Symbol, Enum):
    PLUS = auto()
    MINUS = auto()
    MUL = auto()
    DIV = auto()
    SET = auto()
    SEMICOLON = auto()
    COMMA = auto()
    LP = auto()
    RP = auto()
    PRINT = auto()
    READ = auto()
    VARNAME = auto()
    NUMBER = auto()
    STRING = auto()

@functools.total_ordering
class Position:
    def __init__(self, text, line, pos, index):
        self._text = text
        self._line = line
        self._pos = pos
        self._index = index

    @classmethod
    def default_position(cls, text):
        return cls(text, 1, 1, 0)

    @property
    def line(self):
        return self._line

    @property
    def pos(self):
        return self._pos

    @property
    def index(self):
        return self._index

    def __lt__(self, other):
        return self.index < other.index

    def __eq__(self, other):
        return self.index == other.index

    def __str__(self):
        return f'({self._line}, {self._pos})'

    @property
    def cp(self):
        return -1 if self._index == len(self._text) else self._text[self._index]

    @property
    def is_white_space(self):
        cp = self.cp
        return cp != -1 and cp.isspace()

    @property
    def is_letter(self):
        cp = self.cp
        return cp != -1 and cp.isalpha()

    @property
    def is_letter_or_digit(self):
        cp = self.cp
        return cp != -1 and cp.isalnum()

    @property
    def is_digit(self):
        cp = self.cp
        return cp != -1 and cp.isdigit()

    @property
    def is_new_line(self):
        return self.cp in (-1, '\n')

    def __next__(self):
        line, pos, index = self._line, self._pos, self._index
        if index < len(self._text):
            if self.is_new_line:
                line += 1
                pos = 1
            else:
                pos += 1
            index += 1
        return Position(self._text, line, pos, index)

class EpsilonToken(Token):
    def __init__(self):
        super().__init__(DomainTag.EPSILON, 0, 0)
    def __hash__(self):
        return DomainTag.EPSILON.__hash__()

class NumberToken(Token):
    def __init__(self, number, starting, following):
        super().__init__(T.NUMBER, starting, following)
        self.value = number
    def __str__(self):
        return f'{self._tag} {str(self._coords)}: {self.value}'

class StringToken(Token):
    def __init__(self, string, starting, following):
        super().__init__(T.STRING, starting, following)
        self.value = string
    def __str__(self):
        return f'{self._tag} {str(self._coords)}: {self.value}'

class VariableToken(Token):
    def __init__(self, varname, starting, following):
        super().__init__(T.VARNAME, starting, following)
        self.value = varname
    def __str__(self):
        return f'{self._tag} {str(self._coords)}: {self.value}'

class KeywordToken(Token):
    domain_tags = { T.PLUS, T.MINUS, T.MUL, T.DIV, T.SET, T.SEMICOLON, T.COMMA, T.LP, T.RP, T.PRINT, T.READ }
    def __init__(self, tag, starting, following):
        assert tag in KeywordToken.domain_tags
        super().__init__(tag, starting, following)

class EOTToken(Token):
    def __init__(self, starting=0, following=0):
        super().__init__(DomainTag.END_OF_TEXT, starting, following)

def scan(text):
    single_character_strings = { '+': T.PLUS, '-': T.MINUS, '*' : T.MUL, '/': T.DIV, '=': T.SET, ';': T.SEMICOLON, ',': T.COMMA, '(': T.LP, ')': T.RP }
    keywords_strings = {'PRINT': T.PRINT, 'READ': T.READ }
    cur = Position.default_position(text)
    while cur.cp != -1:
        while cur.is_white_space:
            cur = next(cur)
        start = cur
        if cur.cp in single_character_strings:
            cur = next(cur)
            yield KeywordToken(single_character_strings[start.cp], start, start)
        elif cur.cp == '"':
            cur = next(cur)
            while cur.cp != '"':
                cur = next(cur)
            prev = cur
            cur = next(cur)
            string = text[start.index+1: cur.index-1]
            yield StringToken(string, start, prev)
        elif cur.is_letter:
            cur = next(cur)
            prev = start
            while cur.is_letter_or_digit:
                prev = cur
                cur = next(cur)
            ident_name = text[start.index: cur.index]
            if ident_name in keywords_strings:
                yield KeywordToken(keywords_strings[ident_name], start, prev)
            else: 
                yield VariableToken(ident_name, start, prev)
        elif cur.is_digit:
            cur = next(cur)
            prev = start
            while cur.is_digit:
                prev = cur
                cur = next(cur)
            number = int(text[start.index: cur.index])
            yield NumberToken(number, start, prev)
        elif cur.cp != -1:
            print(cur.cp)
            print("Lex error:", cur)
            cur = next(cur)
    yield EOTToken(cur, cur)
