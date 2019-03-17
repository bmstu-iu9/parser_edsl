#!/usr/bin/env python3

import sys
from enum import Enum, auto
from typing import Callable
from abc import ABC
from inspect import signature
from ordered_set import OrderedSet

class Symbol:
    def __lshift__(self, other):
        t = TempRule()
        t.items[-1]['rule'].append(self)
        if isinstance(other, Callable):
            t.items[-1]['action'] = other
        else:
            t.items[-1]['rule'].append(other)
        return t
    def __or__(self, other):
        t = TempRule()
        if isinstance(other, TempRule):
            t.items[-1]['rule'].append(self)
            t.items.extend(other.items)
        else:
            t.items[-1]['rule'].append(self)
            t = t | other
        return t

class Fragment:
    def __init__(self, starting, ending):
        self._starting = starting
        self._ending = ending
    def __str__(self) -> str:
        return f"{self._starting} - {self._ending}"

class Token(ABC):
    def __init__(self, tag, starting, following):
        self._tag = tag
        self._coords = Fragment(starting, following)
        self.value = None
    def __eq__(self, other):
        return self._tag == other._tag
    def __str__(self):
        return f'{self._tag} {str(self._coords)}'
    def __hash__(self):
        return hash(self._tag)

class DomainTag(Symbol, Enum):
    END_OF_TEXT = auto()
    EPSILON = auto()

class ParserException(Exception):
    def __init__(self, message, unexpected_token=None, expected_symbol_set=None):
        super(ParserException, self).__init__(message)
        self.unexpected_token = unexpected_token
        self.expected_symbol_set = expected_symbol_set

class TempRule:
    def __init__(self):
        self.items = [{ 'rule': [], 'action': None }]
    def __lshift__(self, other):
        if isinstance(other,Callable):
            self.items[-1]['action'] = other
        else:
            self.items[-1]['rule'].append(other)
        return self
    def __or__(self, other):
        if isinstance(other, TempRule):
            self.items.extend(other.items)
            return self
        else:
            self.items.append({ 'rule': [other], 'action': None })
            return self

class ActionType(Enum):
    ACCEPT = 0
    SHIFT = 1
    REDUCE = 2

class Action:
    def __init__(self, type, extra):
        self.type = type
        self.extra = extra
    def __eq__(self, other):
        return self.type == other.type and self.extra == other.extra

class Rule:
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side
        self.action = None
    def __str__(self):
        return "%s -> %s" % (self.left_side, ' '.join([str(x) for x in self.right_side]))
    def __eq__(self, other):
        return self.left_side == other.left_side and self.right_side == other.right_side

class NTerm:
    pass

class StartNTerm(NTerm):
    def __eq__(self, other):
        return isinstance(other, StartNTerm)
    def __hash__(self):
        return 42

class Grammar:
    def __init__(self, rules, terminals, nonterminals, start_nonterminal):
        self.rules = [Rule(StartNTerm(), [start_nonterminal])]
        self.rules.extend(rules)
        self.terminals = terminals
        self.nonterminals = nonterminals
        self.start_nonterminal = start_nonterminal
        self.compute_first_sets()
        self.compute_follow_sets()
    def compute_first_set(self, s, index):
        first = set()
        if index == len(s):
            return first
        if s[index] in self.terminals:
            first.add(s[index])
            return first
        if s[index] in self.nonterminals:
            for t in self.first_sets[s[index]]:
                first.add(t)
        if DomainTag.EPSILON in first:
            if index != len(s) - 1:
                first |= self.compute_first_set(s, index + 1)
                first.remove(DomainTag.EPSILON)
        return first
    def compute_first_sets(self):
        self.first_sets = {}
        for s in self.nonterminals:
            self.first_sets[s] = set()
        while True:
            is_changed = False
            for nonterminal in self.nonterminals:
                first_set = set()
                for rule in self.rules:
                    if rule.left_side == nonterminal:
                        to_add = self.compute_first_set(rule.right_side, 0)
                        first_set |= to_add
                if not self.first_sets[nonterminal] >= first_set:
                    is_changed = True
                    self.first_sets[nonterminal] |= first_set
            if not is_changed:
                break
        self.first_sets[StartNTerm()] = self.first_sets[self.start_nonterminal]
    def compute_follow_sets(self):
        self.follow_sets = {}
        for s in self.nonterminals:
            self.follow_sets[s] = set()
        self.follow_sets[StartNTerm()] = set([DomainTag.END_OF_TEXT])
        while True:
            is_changed = False
            for nonterminal in self.nonterminals:
                for rule in self.rules:
                    for i in range(len(rule.right_side)):
                        if rule.right_side[i] == nonterminal:
                            if i == len(rule.right_side) - 1:
                                self.follow_sets[nonterminal] |= self.follow_sets[rule.left_side]
                            else:
                                first = self.compute_first_set(
                                    rule.right_side, i + 1)
                                if DomainTag.EPSILON in first:
                                    first.remove(DomainTag.EPSILON)
                                    first |= self.follow_sets[rule.left_side]
                                if not self.follow_sets[nonterminal] >= first:
                                    is_changed = True
                                    self.follow_sets[nonterminal] |= first
            if not is_changed:
                break
    def rule_index(self, rule):
        for i in range(len(self.rules)):
            if self.rules[i] == rule:
                return i
        return None
    def rules_for_nonterminal(self, n):
        return [x for x in self.rules if x.left_side == n]
    def is_nonterminal(self, s):
        return s in self.nonterminals
    def is_terminal(self, s):
        return s in self.terminals

class Item:
    def __init__(self, rule, marker, lookahead):
        self.rule = rule
        self.marker = marker
        self.lookahead = lookahead
    def get_current(self):
        if self.marker >= len(self.rule.right_side):
            return None
        return self.rule.right_side[self.marker]
    def __hash__(self):
        return hash(tuple([self.marker, self.rule.left_side, *self.rule.right_side]))
    def __eq__(self, other):
        return self.rule == other.rule and self.marker == other.marker and self.lookahead == other.lookahead
    def eq_lr0(self, other):
        return self.rule == other.rule and self.marker == other.marker

class State:
    def __init__(self, grammar, core_items):
        self.items = core_items
        self.transition = {}
        self.closure(grammar)
    def __eq__(self, other):
        return self.items == other.items and self.transition == other.transition
    def closure(self, grammar):
        should_continue = True
        while should_continue:
            should_continue = False
            temp = set()
            for item in self.items:
                if item.marker != len(item.rule.right_side) and grammar.is_nonterminal(item.get_current()):
                    lookahead = set()
                    if item.marker == len(item.rule.right_side) - 1:
                        lookahead |= item.lookahead
                    else:
                        first_set = grammar.compute_first_set(
                            item.rule.right_side, item.marker + 1)
                        if DomainTag.EPSILON in first_set:
                            first_set.remove(DomainTag.EPSILON)
                            first_set |= item.lookahead
                        lookahead |= first_set
                    rules = grammar.rules_for_nonterminal(item.get_current())
                    for rule in rules:
                        temp.add(Item(rule, 0, lookahead))
            if not self.items >= temp:
                self.items |= temp
                should_continue = True

class LALRParser:
    def __init__(self, grammar):
        self.grammar = grammar
        self.goto_table = {}
        self.action_table = {}
        self.canonical_collection = []
        self.build_states()
        self.build_goto_table()
        self.build_action_table()
    def build_goto_table(self):
        self.goto_table = {}
        for i in range(len(self.canonical_collection)):
            self.goto_table[i] = {}
            for s in self.canonical_collection[i].transition.keys():
                if self.grammar.is_nonterminal(s):
                    self.goto_table[i][s] = self.state_index(
                        self.canonical_collection[i].transition[s])
    def build_action_table(self):
        self.action_table = {}
        for i in range(len(self.goto_table)):
            self.action_table[i] = {}
        for i in range(len(self.canonical_collection)):
            for s in self.canonical_collection[i].transition.keys():
                if s in self.grammar.terminals:
                    self.action_table[i][s] = Action(ActionType.SHIFT, self.state_index(
                        self.canonical_collection[i].transition[s]))
        for i in range(len(self.canonical_collection)):
            for item in self.canonical_collection[i].items:
                if item.marker == len(item.rule.right_side):
                    if isinstance(item.rule.left_side, StartNTerm):
                        self.action_table[i][DomainTag.END_OF_TEXT] = Action(
                            ActionType.ACCEPT, 0)
                    else:
                        rule = item.rule
                        index = self.grammar.rule_index(rule)
                        action = Action(ActionType.REDUCE, index)
                        for s in item.lookahead:
                            if not s in self.action_table[i]:
                                self.action_table[i][s] = action
    def build_clr_states(self):
        self.canonical_collection = []
        start = OrderedSet(
            [Item(self.grammar.rules[0], 0, set([DomainTag.END_OF_TEXT]))])
        self.canonical_collection.append(State(self.grammar, start))
        i = 0
        while i < len(self.canonical_collection):
            swd = OrderedSet()
            for item in self.canonical_collection[i].items:
                if item.get_current() != None:
                    swd.add(item.get_current())
            for s in swd:
                next_state_items = OrderedSet()
                for item in self.canonical_collection[i].items:
                    if item.get_current() != None and item.get_current() == s:
                        temp = Item(item.rule, item.marker + 1, item.lookahead)
                        next_state_items.add(temp)
                next_state = State(self.grammar, next_state_items)
                exists = False
                for j in range(len(self.canonical_collection)):
                    if self.canonical_collection[j].items == next_state.items:
                        exists = True
                        self.canonical_collection[i].transition[s] = self.canonical_collection[j]
                if not exists:
                    self.canonical_collection.append(next_state)
                    self.canonical_collection[i].transition[s] = next_state
            i += 1
    def build_states(self):
        self.build_clr_states()
        temp = []
        i = 0
        while i < len(self.canonical_collection):
            itemsi = set()
            for item in self.canonical_collection[i].items:
                itemsi.add(Item(item.rule, item.marker, set()))
            j = i + 1
            while j < len(self.canonical_collection):
                itemsj = set()
                for item in self.canonical_collection[j].items:
                    itemsj.add(Item(item.rule, item.marker, set()))
                if itemsi == itemsj:
                    for itemi in self.canonical_collection[i].items:
                        for itemj in self.canonical_collection[j].items:
                            if itemi.eq_lr0(itemj):
                                itemi.lookahead |= itemj.lookahead
                                break
                    for k in range(len(self.canonical_collection)):
                        for s in self.canonical_collection[k].transition.keys():
                            if self.canonical_collection[k].transition[s].items == self.canonical_collection[j].items:
                                self.canonical_collection[k].transition[s] = self.canonical_collection[i]
                    del self.canonical_collection[j]
                    j -= 1
                j += 1
            temp.append(self.canonical_collection[i])
            i += 1
        self.canonical_collection = temp
    def state_index(self, state):
        for i in range(len(self.canonical_collection)):
            if self.canonical_collection[i] == state:
                return i
        return None
    def parse(self, inputs):
        index = 0
        stack = []
        attr_stack = []
        stack.append((0, 0))
        result = None
        while index < len(inputs):
            state = stack[-1][1]
            next_input, attr = inputs[index]._tag, inputs[index].value
            if next_input not in self.action_table[state]:
                raise ParserException("Unexpected symbol: %s at %s. Expected: %s." % (str(next_input), inputs[index]._coords, ', '.join([str(x) for x in self.action_table[state]])),inputs[index], self.action_table[state])
            action = self.action_table[state][next_input]
            if action.type == ActionType.SHIFT:
                stack.append((next_input, action.extra))
                if attr != None:
                    attr_stack.append(attr)
                index += 1
            elif action.type == ActionType.REDUCE:
                rule_index = action.extra
                rule = self.grammar.rules[rule_index]
                for _ in range(len(rule.right_side)):
                    stack.pop()
                if rule.action != None:
                    attrs = []
                    for _ in range(len(signature(rule.action).parameters)):
                        attrs.append(attr_stack.pop())
                    attr_stack.append(rule.action(*attrs[::-1]))
                next_state = stack[-1][1]
                stack.append((rule.left_side, self.goto_table[next_state][rule.left_side]))
            elif action.type == ActionType.ACCEPT:
                if len(attr_stack) > 0:
                    result = attr_stack[-1]
                return result
        raise ParserException("Unknown error")

class NTerm(Symbol):
    instances_count = 0
    def __init__(self,name='Unnamed'):
        self.productions = []
        self.id = NTerm.instances_count
        self.name = name
        NTerm.instances_count += 1
        self.parser = None
    def __iadd__(self, other):
        if isinstance(other, TempRule):
            self.productions.extend(other.items)
        else:
            self.productions.append({'rule': [other], 'action': None})
        return self
    def __hash__(self):
        return self.id
    def __eq__(self, other):
        if isinstance(other, NTerm):
            return self.productions == other.productions
        return False
    def __str__(self):
        return self.name
    def parse(self, tokens):
        if self.parser == None:
            terminals = set()
            start_nonterminal = self
            rules = []
            def find_all_nonterminals(start, found_nonterminals):
                for production in start.productions:
                    for item in production['rule']:
                        if isinstance(item, NTerm) and item not in found_nonterminals:
                            found_nonterminals.add(item)
                            find_all_nonterminals(item, found_nonterminals)
            nonterminals = set([self])
            find_all_nonterminals(self, nonterminals)
            for nonterminal in nonterminals:
                for production in nonterminal.productions:
                    rule = Rule(nonterminal, production['rule'])
                    rule.action = production['action']
                    rules.append(rule)
                    for item in production['rule']:
                        if not isinstance(item, NTerm):
                            terminals.add(item)
            grammar = Grammar(rules, terminals, nonterminals, start_nonterminal)
            self.parser = LALRParser(grammar)
        return self.parser.parse(tokens)
