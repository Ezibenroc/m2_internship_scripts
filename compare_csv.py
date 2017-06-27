#! /usr/bin/env python3

import sys
from pandas import DataFrame

def compute_subset(df, row, variables):
    subset = df
    for var in variables:
        subset = subset[subset[var] == row[var]]
    return subset

def compare_row(control_rows, row, variables, delta=0.1):
    for var in control_rows.keys():
        if var in variables:
            continue
        min_expected = control_rows[var].min() * (1-delta)
        max_expected = control_rows[var].max() * (1+delta)
        real_value = row[var]
        if min_expected > real_value or max_expected < real_value:
            sys.stderr.write('ERROR for key %s\n' % var)
            sys.stderr.write('Expected a value in [%g, %g], got %g\n' % (min_expected, max_expected, real_value))
            sys.exit(1)

def compare(df, row, variables):
    subset = compute_subset(df, row, variables)
    compare_row(subset, row, variables)

def compare_all(df1, df2, variables):
    for row in df2.iterrows():
        compare(df1, row[1], variables)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write('Syntax: %s <CSV file> <CSV file> <control variables>\n' % sys.argv[0])
        sys.exit(1)
    df1 = DataFrame.from_csv(sys.argv[1], index_col=None)
    df2 = DataFrame.from_csv(sys.argv[2], index_col=None)
    variables = sys.argv[3:]
    compare_all(df1, df2, variables)
