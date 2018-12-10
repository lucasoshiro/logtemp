#!/usr/bin/env python3

from sys import argv, stderr
from time import sleep
from datetime import datetime
import sqlite3
import subprocess
import json
import re
import os

def get_temp():
    cmd = 'vcgencmd measure_temp'
    temp_regex = 'temp=([0-9.]+)\'C'
    p_cmd = os.popen(cmd)
    temp = float(re.match(temp_regex, p_cmd.read()).groups()[0])
    p_cmd.close()
    return temp

def sample(n, workers):
    stderr.write('{} {}\n'.format(n, workers))
    def _single_sample():
        s = {
            'timestamp':   datetime.now(),
            'temperature': get_temp(),
            'workers':     workers
        }
        sleep(1)
        return s

    stress = subprocess.Popen(
        ['stress', '-c', str(workers)], stdout=open(os.devnull, 'wb')) if workers > 0 else None
    results = [_single_sample() for i in range(n)]
    if stress: stress.kill()
    return results

def main():
    with sqlite3.connect('buffer.sqlite') as conn:
        conn.execute('DROP TABLE IF EXISTS logtemp')
        conn.execute('''CREATE TABLE logtemp
                           (timestamp TIMESTAMP,
                            iteration INTEGER, 
                            temp      FLOAT,
                            workers   INTEGER)''')

    for i in range(5):
        samples = sample(20, 0) + sample(40, i) + sample(1200, 0)
        with sqlite3.connect('buffer.sqlite') as conn:
            statement = 'INSERT INTO logtemp VALUES {}'.format(
                ', '.join(['({}, {}, {}, {})'.format(
                    sample['timestamp'], i, sample['temp'], sample['workers'])
                           for sample in samples]))

    with sqlite3.connect('buffer.sqlite') as conn:
        cursor = conn.execute('SELECT * FROM logtemp')
        sample_0_4 = [dict(zip(['timestamp', 'iteration', 'temp', 'workers'])) for t in cursor]

    # sample_0_4 = dict((i, sample(20, 0) + sample(40, i) + sample(1200, 0)) for i in range(5))
    print(json.dumps(sample_0_4))

if __name__ == '__main__':
    main()
