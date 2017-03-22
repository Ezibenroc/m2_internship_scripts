#!/usr/bin/env python3

import sys
import re
from pandas import DataFrame
import statsmodels.formula.api as statsmodels

str_reg   = '[a-zA-Z0-9/_.-]+'
int_reg   = '-?[0-9]+'
float_reg = '-?[0-9]+.[0-9]+'

class_to_reg = {
    str:   str_reg,
    int:   int_reg,
    float: float_reg,
}

parameters = [
    ('function', str),
    ('file', str),
    ('line', int),
    ('rank', int),
    ('m', int),
    ('n', int),
    ('k', int),
    ('lead_A', int),
    ('lead_B', int),
    ('lead_C', int),
    ('real_time', float)
]

functions = {
    'dgemm' : 'I(m * n * k)',
    'dtrsm' : 'I(m * n)'
}

def func_name_to_var(name):
    return '-DSMPI_%s_COEFF' % (name.upper())

def generate_regexp_chunk(name, regexp):
    return '%s\s*=\s*(?P<%s>%s)' % (name, name, regexp)

def generate_whole_regexp():
    return '\s*%s\s*' % '\s+'.join(generate_regexp_chunk(name, class_to_reg[cls]) for name, cls in parameters)

reg = re.compile(generate_whole_regexp())

def get_results(in_file):
    results = []
    with open(in_file, 'r') as in_f:
        for line in in_f:
            match = reg.match(line)
            if match is not None:
                result = {name:cls(match.group(name)) for name, cls in parameters}
                result['file'] = result['file'][result['file'].index('/hpl'):].lower()
                results.append(result)
    return DataFrame(results)

def get_regression_coefficients(dataframe, func_name, model):
    data = dataframe[dataframe.function==func_name]
    regression = statsmodels.ols(formula=model, data=data).fit()
    return regression

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Syntax: %s <file_name>' % sys.argv[0])
        sys.exit(1)
    dataframe = get_results(sys.argv[1])
    regressions = []
    for func_name, model in functions.items():
        model = 'real_time ~ %s' % model
        reg = get_regression_coefficients(dataframe, func_name, model)
        regressions.append((func_name, reg.params[functions[func_name]]))
        rsquared = reg.rsquared
        if rsquared < 0.95:
            print('WARNING: bad R-squared for function %s with model %s: got %f.' % (func_name, model, rsquared))
    c_args = ' '.join(['%s=%e' % (func_name_to_var(func_name), coeff) for func_name, coeff in regressions])
    print(c_args)
