import databaker.bake as bake
import unittest
import imp
import warnings
from databaker.constants import *
import xypath
from databaker.overrides import Receipt

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
    return r.get_item(cell) == cell._cell.lookup(r.bag, r.direction, r.strict)

b = getcell("AC E GI")


class testcase(unittest.TestCase):
    def test_directly_above(self):
        bag = getcell("AC E GI")
        cell = getcell("H")
        r = Receipt(bag, DIRECTLY, ABOVE)
        assert r.get_item(cell).value == "E"
        assert nice_receipt(r.receipt) == ['AG', 'E', 'CI']
        assert r.receipt_index == [0, 1, 2]
        assert same_as_lookup(r, cell)

    def test_closest_above(self):
        bag = getcell("AG")
        cell = getcell("K")
        r = Receipt(bag, CLOSEST, ABOVE)
        assert r.get_item(cell).value == "G"
        assert nice_receipt(r.receipt) == ['A', 'G']
        assert r.receipt_index == [0, 2]
        assert same_as_lookup(r, cell)

    def test_directly_above_failure(self):
        bag = getcell("AG")
        cell = getcell("K")
        #r = Receipt(bag, DIRECTLY, ABOVE) ## nothing to find return something useful
