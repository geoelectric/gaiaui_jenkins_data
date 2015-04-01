#!/usr/bin/env python

import os
import re
import sys

PATTERN = (r'<td class="col-result">([a-zA-Z]+)</td>\s*' +
           r'<td class="col-class">([\w\.]*)</td>\s*' +
           r'<td class="col-name">(.+)</td>')
PATTERN = re.compile(PATTERN)


def main():
    verbose = len(sys.argv) > 2
    if verbose:
        job = sys.argv[2]
    else:
        job = sys.argv[1]

    job_data = {}

    filename = 'output.html'

    builds = os.listdir(job)
    builds.sort(key=int)
    crunched = 0
    for build in builds:
        filepath = os.path.join(*[job, build, filename])
        if os.path.exists(filepath):
            crunched += 1
            # first_error = True

            with open(filepath, 'r') as f:
                output = f.read()

            suite = [
                {'class': match[1],
                 'name': match[2],
                 'result': match[0]}
                for match in PATTERN.findall(output)
            ]

            num_errors = reduce(lambda x, y: x +
                                (1 if y['result'] == 'Error' else 0), suite, 0)
            pct_errors = num_errors / float(len(suite))

            if pct_errors > 0.25:
                print '%s is possibly a bad run (%d%% errors)' % (
                    filepath, pct_errors*100)
                bad_run = True
            else:
                bad_run = False

            for test in suite:
                key = (test['class'] + ' ' + test['name']).strip()
                test_data = job_data.get(key,
                                         {'class': test['class'],
                                          'name': test['name'],
                                          'runs': 0, 'spurious': 0,
                                          'passes': 0, 'skips': 0,
                                          'errors': 0, 'failures': 0,
                                          'xfails': 0, 'upasses': 0,
                                          'unknown': 0})
                test_data['runs'] += 1

                if test['result'] == 'Skipped':
                    test_data['skips'] += 1
                elif test['result'] == 'Passed':
                    test_data['passes'] += 1
                elif test['result'] == 'Failure':
                    test_data['failures'] += 1
                elif test['result'] == 'Expected Failure':
                    test_data['xfails'] += 1
                elif test['result'] == 'Unexpected Pass':
                    test_data['upasses'] += 1
                elif test['result'] == 'Error':
                    if bad_run:
                        test_data['spurious'] += 1
                    else:
                        test_data['errors'] += 1

                # Attempted to remove blocks of errors as failed runs, but this
                # doesn't work right. Instead should probably do something more
                # like a percentage threshold.
                #
                # elif test['result'] == 'Error':
                #     if first_error:
                #         test_data['errors'] += 1
                #         first_error = False
                #     else:
                #         test_data['runs'] -= 1

                else:
                    print 'Unknown result: %s' % test['result']
                    test_data['unknown'] += 1
                    test_data['runs'] -= 1

                job_data[key] = test_data

    filtered_job_data = []
    for key in job_data:
        t = job_data[key]
        if t['runs'] != t['skips']:
            pct_failed = int(float(t['failures'] + t['errors']) / t['runs'] * 100)
            filtered_job_data.append({'class': t['class'],
                                      'name': t['name'],
                                      'runs': t['runs'],
                                      'skips': t['skips'],
                                      'passes': t['passes'],
                                      'failures': t['failures'],
                                      'xfails': t['xfails'],
                                      'upasses': t['upasses'],
                                      'errors': t['errors'],
                                      'spurious': t['spurious'],
                                      'unknown': t['unknown'],
                                      'pct_failed': pct_failed})

    def job_key(j):
        return j['pct_failed']

    filtered_job_data.sort(key=job_key)
    max_len = max([len(test['name']) for test in filtered_job_data]) + 2

    print
    print '%s' % ('-' * len(job))
    print '%s' % job
    print '%s' % ('-' * len(job))
    print
    print '%d tests found in %d runs.' % (len(filtered_job_data), crunched)
    print
    for test in filtered_job_data:
        padding = ' ' * (max_len - len(test['name']))
        if verbose:
            print '%s: ' % test['class']
        print ('  %s()%s: %4d runs, %4d skips, %4d passes, %4d failures, '
               '%4d xfails, %4d upasses, %4d errors, %4d spurious, (%d%% failed)') % (
            test['name'],
            padding,
            test['runs'],
            test['skips'],
            test['passes'],
            test['failures'],
            test['xfails'],
            test['upasses'],
            test['errors'],
            test['spurious'],
            test['pct_failed'])
    print

if __name__ == '__main__':
    main()
