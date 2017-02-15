#! /usr/bin/env python3

import unittest
from topology import Parser, ParseError

def outlist_to_descr(out_l):
    return Parser.out_separator.join(inlist_to_descr(in_l) for in_l in out_l)

def inlist_to_descr(in_l):
    if not isinstance(in_l, list):
        return elt_to_descr(in_l)
    else:
        return Parser.in_separator.join(elt_to_descr(elt) for elt in in_l)

def elt_to_descr(elt):
    if isinstance(elt, tuple):
        return Parser.range_separator.join([str(elt[0]), str(elt[1])])
    else:
        return str(elt)

class TestParser(unittest.TestCase):

    def check_valid_descr(self, description):
        parsed = Parser.parse(description)
        result = outlist_to_descr(parsed)
        self.assertEqual(description, result)

    def test_valid(self):
        self.check_valid_descr('3;1,4,5;82,27;42;17,42')
        self.check_valid_descr('3:24;1,4,5;82,27:1000;42:42;17,42')

    def test_invalid(self):
        with self.assertRaises(ParseError):
            Parser.parse('3:24;1,4,5;-2,82,27:1000;0:42;17,42')     # negative number
        with self.assertRaises(ParseError):
            Parser.parse('3:24;1,4,5;1,82,27:1000;0:42;17,42')      # null number
        with self.assertRaises(ParseError):
            Parser.parse('3:24;1,4,5;abc,82,27:1000;42:42;17,42')   # not a number
        with self.assertRaises(ParseError):
            Parser.parse('3:24;1,4,5;82,27:10;42:42;17,42')         # empty range
        with self.assertRaises(ParseError):
            Parser.parse('3:24;1,4,5;82,27:100:1000;42:42;17,42')   # invalid range

if __name__ == '__main__':
    unittest.main()
