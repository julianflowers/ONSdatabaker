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

b = getcell("AEGCIK")


class testcase(unittest.TestCase):
    def test_foo(self):
        print b
        r = Receipt(b, DIRECTLY, ABOVE)
        h = getcell("H")
        print r.get_item(h)  # should be E
        print "**"
        raise SyntaxError

