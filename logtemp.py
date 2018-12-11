#!/usr/bin/env python3

from sys import argv, stderr
from time import sleep
from datetime import datetime
import sqlite3
import subprocess
import json
import re
import os
import signal

BEFORE_SAMPLES = 40
STRESS_SAMPLES = 1200
AFTER_SAMPLES  = 2400
INTERVAL       = 0.5

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
        sleep(INTERVAL)
        return s

    stress = subprocess.Popen(
        ['stress', '-c', str(workers)], stdout=open(os.devnull, 'wb')) if workers > 0 else None
    results = [_single_sample() for i in range(n)]
    subprocess.Popen(
            ['killall', 'stress'], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
    return results

def main():
    with sqlite3.connect('buffer.sqlite') as conn:
        conn.execute('DROP TABLE IF EXISTS logtemp')
        conn.execute('''CREATE TABLE logtemp
                           (timestamp   TIMESTAMP,
                            iteration   INTEGER,
                            temperature FLOAT,
                            workers     INTEGER)''')

    for i in range(5):
        samples = sample(BEFORE_SAMPLES, 0) + sample(STRESS_SAMPLES, i) + sample(AFTER_SAMPLES, 0)

        with sqlite3.connect('buffer.sqlite') as conn:
            statement = 'INSERT INTO logtemp VALUES {}'.format(
                ', '.join(
                    ["('{}', {}, {}, {})".format(
                        sample['timestamp'], i, sample['temperature'], sample['workers'])
                     for sample in samples]))
            conn.execute(statement)

    with sqlite3.connect('buffer.sqlite') as conn:
        cursor = conn.execute('SELECT * FROM logtemp')
        sample_0_4 = [dict(zip(
            ['timestamp', 'iteration', 'temperature', 'workers'], t)) for t in cursor]

    print(json.dumps(sample_0_4))

if __name__ == '__main__':
    main()
