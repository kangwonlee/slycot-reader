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

    t = mut.SetMdQuote(('d', 'b', 'c'))
    s_union_t = s.union(t)

    expected_union = mut.SetMdQuote(list('abcd'))

    assert expected_union == s_union_t, s_union_t


def test_get_f2c_path_dict():
    input_path = 'abc'
    result = mut.get_f2c_path_dict(input_path)

    assert isinstance(result, dict)
    assert 'f2c' in result, result
    assert 'src' in result, result

    result_f2c = result['f2c']

    assert isinstance(result_f2c, dict)


@pytest.fixture
def f2cp_reader():
    reader = mut.F2cpReader()

    yield reader

    del reader


def test_f2cp_reader_re_first_line_c_function_prototype(f2cp_reader):
    reader = f2cp_reader

    input_lines = 'extern int sb02sd_(char *job, char *fact, char *trana, char *uplo, char *lyapun, integer *n, doublereal *a, integer *lda, doublereal *t, integer *ldt, doublereal *u, integer *ldu, doublereal *g, integer *ldg, doublereal *q, integer *ldq, doublereal *x, integer *ldx, doublereal *sepd, doublereal *rcond, doublereal *ferr, integer *iwork, doublereal *dwork, integer *ldwork, integer *info, ftnlen job_len, ftnlen fact_len, ftnlen trana_len, ftnlen uplo_len, ftnlen lyapun_len);'

    result = reader.get_first_line_pattern().findall(input_lines)

    assert isinstance(result, (list, tuple))
    assert 'sb02sd_' in result[0], result
