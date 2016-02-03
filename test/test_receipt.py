import databaker.bake as bake
import unittest
import imp
import warnings
from databaker.constants import *
import xypath
from databaker.overrides import Receipt

warnings.simplefilter("ignore")

t = xypath.Table.from_iterable(
       [['A', 'B', 'C',
         'D', 'E', 'F',
         'G', 'H', 'I',
         'J', 'K', 'L']])

b = t.filter(lambda x: x.value in "AEGCIK")

class t(unittest.TestCase):
    def test_foo(self):
        Receipt(b, DIRECTLY, ABOVE)

