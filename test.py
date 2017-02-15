#! /usr/bin/env python3

import unittest
from topology import *

def outlist_to_descr(out_l):
    return Parser.out_separator.join(inlist_to_descr(in_l) for in_l in out_l)

def inlist_to_descr(in_l):
    return Parser.in_separator.join(elt_to_descr(elt) for elt in in_l)

def elt_to_descr(elt):
    if isinstance(elt, int):
        elt = range(elt, elt+1)
    return Parser.range_separator.join([str(elt.start), str(elt.stop-1)])

class TestFatTree(unittest.TestCase):

    def test_eq(self):
        self.assertEqual(FatTree([1,2], [3,4], [5,6]),
                         FatTree([1,2], [3,4], [5,6]))
        self.assertNotEqual(FatTree([1,2], [3,4], [5,6]),
                         FatTree([1,20], [3,4], [5,6]))
        self.assertNotEqual(FatTree([1,2], [3,4], [5,6]),
                         FatTree([1,2], [3,40], [5,6]))
        self.assertNotEqual(FatTree([1,2], [3,4], [5,6]),
                         FatTree([1,2], [3,4], [5,60]))

class TestParser(unittest.TestCase):

    def check_valid_descr(self, description):
        parsed = Parser.parse(description)
        result = outlist_to_descr(parsed)
        reparsed = Parser.parse(result)
        self.assertEqual(parsed, reparsed)

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

class TestFatTreeParser(unittest.TestCase):

    def test_simple_valid(self):
        descr = '2;24,48;1,24;2,3'
        self.assertEqual(FatTreeParser.parse(descr),
                [FatTree([24,48],[1,24],[2,3])])

    def test_valid(self):
        descr = '2;1:5,6:10;11:15,16:20;21:25,26:30'
        trees = set(FatTreeParser.parse(descr))
        self.assertEqual(len(trees), 5**6)
        for t in [
                FatTree([1,6], [11,16], [21,26]),
                FatTree([5,10], [15,20], [25,30]),
                FatTree([3,8], [12,17], [23,28]),
                ]:
            self.assertIn(t, trees)

    def test_invalid(self):
        with self.assertRaises(ParseError):
            FatTreeParser.parse('1;1;1')                # wrong number of parts
        with self.assertRaises(ParseError):
            FatTreeParser.parse('1;1;1;1;1')            # wrong number of parts
        with self.assertRaises(ParseError):
            FatTreeParser.parse('1:2;1;1;1')            # wrong level descriptor
        with self.assertRaises(ParseError):
            FatTreeParser.parse('1,2;1;1;1')            # wrong level descriptor
        with self.assertRaises(ParseError):
            FatTreeParser.parse('2;1;1,5;1,5')          # wrong size of sublist
        with self.assertRaises(ParseError):
            FatTreeParser.parse('2;1,5;1;1,5')          # wrong size of sublist
        with self.assertRaises(ParseError):
            FatTreeParser.parse('2;1,5;1,5;1')          # wrong size of sublist

if __name__ == '__main__':
    unittest.main()
