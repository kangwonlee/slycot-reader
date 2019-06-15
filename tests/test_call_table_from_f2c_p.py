import os
import sys

import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import slycot_reader.call_table_from_f2c_p as mut


def test_get_slycot_path():

    expected = os.path.dirname(__file__)
    input_list = [expected, 'a', 'b', 'c']

    result = mut.get_slycot_path(input_list)

    assert expected == result


def test_unique_list_ordered():
    input_list = list('abcdabcd')

    result = mut.unique_list_ordered(input_list)

    expected = list('abcd')

    assert expected == result, result


def test_SetMdQuote():
    s = mut.SetMdQuote(('a', 'b', 'c'))

    s_str = str(s)
    assert s_str.startswith('{'), s_str
    assert s_str.endswith('}'), s_str
    assert s_str.count('`') == 2 * len(s)
