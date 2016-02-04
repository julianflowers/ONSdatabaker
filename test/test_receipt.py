import databaker.bake as bake
import unittest
import imp
import warnings
from databaker.constants import *
import xypath
from databaker.overrides import Receipt
import random

FUZZMAX = 1000
warnings.simplefilter("ignore")

t = xypath.Table.from_iterable(
       [['A', 'B', 'C'],
        ['D', 'E', 'F'],
        ['G', 'H', 'I'],
        ['J', 'K', 'L']])


def getcell(s):
    """returns bag containing named cells"""
    return t.filter(lambda x: x.value in s)

def nice_receipt(r):
    return list(''.join(sorted([i.value for i in row])) for row in r)

def same_as_lookup(r, cell):
    r_exception = None
    l_exception = None
    try:
        receipt_header_cell = r.get_item(cell)
    except xypath.XYPathError as r_exception:
        pass

    try:
        lookup_header_cell = cell._cell.lookup(r.bag, r.direction, r.strict)
    except xypath.XYPathError as l_exception:
        pass

    if not l_exception:
        print "Lookup said: ", lookup_header_cell
    if not r_exception:
        print "Receipt said: ", receipt_header_cell
    assert type(r_exception) == type(l_exception), "Got {!r} not {!r}".format(r_exception, l_exception)  # either both OK or both same error
    if r_exception:
        return  # no receipt to check
    assert type(receipt_header_cell) == xypath.xypath._XYCell, type(receipt_header_cell)
    assert receipt_header_cell == lookup_header_cell, \
          "Receipt gets {} not {}".format(receipt_header_cell, lookup_header_cell)

def print_receipt(r):
    print r.bag
    print r.strict, r.direction, r.index_letter
    print r.receipt, r.receipt_index

b = getcell("AC E GI")

def fuzz(strict, direction):
    diceroll = int(random.random()*7) + int(random.random()*6)
    letters = ''.join(random.sample("ABCDEFGHIJKL", diceroll))
    letter = random.choice("ABCDEFGHIJKL")
    bag = getcell(letters)
    cell = getcell(letter)
    print letters, letter
    r = Receipt(bag, strict, direction)
    print_receipt(r)
    same_as_lookup(r, cell)


class testcase(unittest.TestCase):
    def test_directly_above(self):
        bag = getcell("AC E GI")
        cell = getcell("H")
        r = Receipt(bag, DIRECTLY, ABOVE)
        same_as_lookup(r, cell)
        assert r.get_item(cell).value == "E"
        assert nice_receipt(r.receipt) == ['AG', 'E', 'CI']
        assert r.receipt_index == [0, 1, 2]

    def test_closest_above(self):
        bag = getcell("AG")
        cell = getcell("K")
        r = Receipt(bag, CLOSEST, ABOVE)
        same_as_lookup(r,cell)
        assert r.get_item(cell).value == "G"
        assert nice_receipt(r.receipt) == ['A', 'G']
        assert r.receipt_index == [0, 2]

    def test_directly_above_failure(self):
        bag = getcell("AG")
        cell = getcell("K")
        r = Receipt(bag, DIRECTLY, ABOVE)
        same_as_lookup(r, cell)

    def test_multiple_options_failure(self):
        bag = getcell("ABC")
        cell = getcell("E")
        r = Receipt(bag, CLOSEST, ABOVE)
        same_as_lookup(r, cell)

    def test_fuzzdl(self):
        for i in range(FUZZMAX):
            fuzz(DIRECTLY, LEFT)
    def test_fuzzda(self):
        for i in range(FUZZMAX):
            fuzz(DIRECTLY, ABOVE)
    def test_fuzzdr(self):
        for i in range(FUZZMAX):
            fuzz(DIRECTLY, RIGHT)
    def test_fuzzdb(self):
        for i in range(FUZZMAX):
            fuzz(DIRECTLY, BELOW)
    def test_fuzzcl(self):
        for i in range(FUZZMAX):
            fuzz(CLOSEST, LEFT)
    def test_fuzzca(self):
        for i in range(FUZZMAX):
            fuzz(CLOSEST, ABOVE)
    def test_fuzzcr(self):
        for i in range(FUZZMAX):
            fuzz(CLOSEST, RIGHT)
    def test_fuzzcb(self):
        for i in range(FUZZMAX):
            fuzz(CLOSEST, BELOW)
