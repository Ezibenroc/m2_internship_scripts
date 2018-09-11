#!/usr/bin/env python3

from subprocess import Popen
from time import sleep
import json
from os.path import basename
from curses import wrapper
import sys

TMP_FILE = '/tmp/memstat.json'

def mem_to_human(size):
    size = float(size)
    units = {1: 'B', 1e3: 'kB', 1e6: 'MB', 1e9: 'GB', 1e12: 'TB'}
    for s in reversed(sorted(units)):
        if size/s >= 1:
            return '%.3f %s' % (size/s, units[s])

def get_memory_usage(process_names):
    process = Popen(['./smemstat', '-q', '-o', TMP_FILE, '-p', ','.join(process_names)])
    assert process.wait() == 0
    with open(TMP_FILE, 'r') as f:
        result = json.load(f)
    result = result['smemstat']['smem-per-process']
    return result

def format_entry(columns, column_sizes):
    return ' '.join(str(col).ljust(column_sizes[i]) for i, col in enumerate(columns))

def format_output(result):
    column_sizes = [5, 15, 15, 10]
    columns = ['PID', 'USS', 'RSS', 'command']
    output = []
    output.append(format_entry(columns, column_sizes))
    for entry in result:
        output.append(format_entry([entry['pid'],
                                    mem_to_human(entry['uss']),
                                    mem_to_human(entry['rss']),
                                    entry['command']
                                    ],
                                    column_sizes))
    return output


def main(stdscr, process_names):
    while True:
        stdscr.clear()
        output = format_output(get_memory_usage(process_names))
        for i, line in enumerate(output):
            stdscr.addstr(i, 0, line)
        stdscr.refresh()
        sleep(1)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.stderr.write('Syntax: %s <process_names>\n' % sys.argv[0])
        sys.exit(1)
    wrapper(main, sys.argv[1:])
