#! /usr/bin/env python3

import sys
from pandas import DataFrame

def read_csv(filename):
    df = DataFrame.from_csv(filename, index_col=None)
    df['index'] = range(1, len(df)+1)
    df['filename'] = filename
    return df


def compute_subset(df, row, variables):
    subset = df
    for var in variables:
        subset = subset[subset[var] == row[var]]
    return subset

def compare_row(control_rows, row, variables, delta=0.1):
    error = 0
    for var in control_rows.keys():
        if var in variables or var in ['index', 'filename']:
            continue
        min_expected = control_rows[var].min() * (1-delta)
        max_expected = control_rows[var].max() * (1+delta)
        real_value = row[var]
        if min_expected > real_value or max_expected < real_value:
            sys.stderr.write('ERROR for key "%s"\n' % var)
            sys.stderr.write('Expected a value in [%g, %g] (file %s), got %g (file %s, line %d)\n\n' % (min_expected, max_expected, control_rows['filename'].unique()[0], real_value, row['filename'], row['index']))
            error += 1
    return error

def compare(df, row, variables):
    subset = compute_subset(df, row, variables)
    return compare_row(subset, row, variables)

def compare_all(df1, df2, variables):
    error = 0
    for row in df2.iterrows():
        error += compare(df1, row[1], variables)
    return error

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write('Syntax: %s <CSV file> <CSV file> <control variables>\n' % sys.argv[0])
        sys.exit(1)
    df1 = read_csv(sys.argv[1])
    df2 = read_csv(sys.argv[2])
    variables = sys.argv[3:]
    error = compare_all(df1, df2, variables)
    if error > 0:
        sys.stderr.write('Total number of errors: %d\n' % error)
        sys.exit(1)
