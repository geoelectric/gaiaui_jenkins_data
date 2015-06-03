#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Analyzes Gaia Jenkins result reports for a given job and tabulates statistics per test"""

import logging
import os
import re
import sys


logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

RESULT_PATTERN = r'<td class="col-result">([a-zA-Z ]+)</td>\s*'
CLASS_PATTERN = r'<td class="col-class">([\w\.]*)</td>\s*'
NAME_PATTERN = r'<td class="col-name">(.+)</td>'

OLD_FORMAT = re.compile(RESULT_PATTERN + CLASS_PATTERN + NAME_PATTERN)
NEW_FORMAT = re.compile(RESULT_PATTERN + NAME_PATTERN)


def default_job_data(job):
    """Return the initial dictionary for the job"""
    return {'global': {'name': job, 'runs': 0}, 
            'tests': {}}


def default_test_data(name):
    """Return the initial dictionary for a given test"""
    
    return {'name': name,
            'results': 0, 'spurious': 0,
            'passes': 0, 'skips': 0,
            'errors': 0, 'failures': 0,
            'xfails': 0, 'upasses': 0,
            'unknown': 0}


def make_new_format_name(test_class, test_name):
    """Normalizes the old class/name format to the new name format"""

    # class is either blank or file.class
    class_components = test_class.split('.')
    if len(class_components) == 2:
        test_filename, test_classname = class_components
        final_name = '%s.py %s.%s' % (
               test_filename.strip(), test_classname.strip(), test_name.strip())
        return final_name

    return test_name.strip()


def build_report_paths(job_data):
    """Generates list of paths for report files to tabulate"""

    FILENAME = 'output.html'

    job = job_data['global']['name']

    builds = os.listdir(job)
    builds.sort(key=int)
    
    build_paths = (os.path.join(*[job, build, FILENAME]) for build in builds)
    return (build_path for build_path in build_paths if os.path.exists(build_path))


def extract_suite(output):
    """Parses the output to determine format and extract the suite information"""

    if 'col-class' in output:
        suite = [
            {'name': make_new_format_name(match[1], match[2]),
             'result': match[0].strip()}
            for match in OLD_FORMAT.findall(output)
        ]
    else:
        suite = [
            {'name': match[1].strip(),
             'result': match[0].strip()}
            for match in NEW_FORMAT.findall(output)
        ]

    return suite


def check_for_bad_run(build_report_path, suite):
    """Makes a call as to whether run is probably bad based on percentage of failures"""

    num_errors = reduce(lambda x, y: x +
                        (1 if y['result'] == 'Error' else 0), suite, 0)
    pct_errors = num_errors / float(len(suite))

    if pct_errors > 0.25:
        logging.warning('%s is possibly a bad run (%d%% errors)', 
                        build_report_path, pct_errors*100)
        return True 
    return False


def add_build_to_data(build_report_path, job_data):
    """Adds a single report to the cumulative job data"""

    with open(build_report_path, 'r') as build_report:
        output = build_report.read()

    suite = extract_suite(output)
    if len(suite) == 0:
        logging.warning('No tests found in %s', build_report_path)
        return

    is_bad_run = check_for_bad_run(build_report_path, suite)
    
    job_data['global']['runs'] += 1

    for test in suite:
        test_data = job_data['tests'].setdefault(test['name'], default_test_data(test['name']))
        test_data['results'] += 1

        if test['result'] == 'Skipped' or test['result'] == 'SKIP':
            test_data['skips'] += 1
        elif test['result'] == 'Passed' or test['result'] == 'PASS':
            test_data['passes'] += 1
        elif test['result'] == 'Failure' or test['result'] == 'FAIL':
            test_data['failures'] += 1
        elif test['result'] == 'Expected Failure':
            test_data['xfails'] += 1
        elif test['result'] == 'Unexpected Pass':
            test_data['upasses'] += 1
        elif test['result'] == 'Error':
            if is_bad_run:
                test_data['spurious'] += 1
            else:
                test_data['errors'] += 1
        else:
            logging.warning('Unknown result: %s for %s in %s', test['result'], test['name'], build_report_path)
            test_data['unknown'] += 1
            test_data['results'] -= 1


def remove_unran_tests(job_data):
    """Remove any tests that were skipped for the entire job"""

    filtered_tests = {}
    for key in job_data['tests']:
        t = job_data['tests'][key]
        if t['results'] != t['skips']:
            filtered_tests[key] = t
    job_data['tests'] = filtered_tests


def add_percentage_failed(job_data):
    """Calculate percentage failed for each test and update the data"""

    for key in job_data['tests']:
        t = job_data['tests'][key]
        t['pct_failed'] = int(float(t['failures'] + t['errors']) / t['results'] * 100)


def analyze_job(job):
    """Top level procedure for overall analysis"""

    job_data = default_job_data(job)
    
    for build_report_path in build_report_paths(job_data):
        add_build_to_data(build_report_path, job_data)

    remove_unran_tests(job_data)
    add_percentage_failed(job_data)

    return job_data


def abbreviate_test_name(name):
    """Return a shorter version of the test name for the report"""

    # Name could be one of:
    #   file.py class.method
    #   file.py
    #
    # We should only modify the first case

    name_parts = name.split(' ')
    if len(name_parts) == 2:
        name = name_parts[1].split('.')[-1]
    return name


def test_rows_sorted_by_percentage_failed(job_data, verbose):
    """Return the sorted list of tests formatted for display"""
    tests = job_data['tests'].values()
    
    if not verbose:
        for test in tests:
            test['name'] = abbreviate_test_name(test['name'])
        
    tests.sort(key=lambda t: t['pct_failed'])
    return tests


def report(job_data, verbose):
    """Outputs the final report"""

    sorted_tests = test_rows_sorted_by_percentage_failed(job_data, verbose)
    max_len = max((len(test['name']) for test in sorted_tests)) + 2

    job = job_data['global']['name']

    print
    print '%s' % ('-' * len(job))
    print '%s' % job
    print '%s' % ('-' * len(job))
    print
    print '%d tests found in %d runs.' % (len(sorted_tests), job_data['global']['runs'])
    print
    for test in sorted_tests:
        padding = ' ' * (max_len - len(test['name']))
        print ('  %s()%s: %4d results, %4d skips, %4d passes, %4d failures, '
               '%4d xfails, %4d upasses, %4d errors, %4d spurious, (%d%% failed)') % (
            test['name'],
            padding,
            test['results'],
            test['skips'],
            test['passes'],
            test['failures'],
            test['xfails'],
            test['upasses'],
            test['errors'],
            test['spurious'],
            test['pct_failed'])
    print


def main():
    if len(sys.argv) > 2:
        job = sys.argv[2]
        verbose = True
    else:
        job = sys.argv[1]
        verbose = False

    job_data = analyze_job(job)
    report(job_data, verbose)


if __name__ == '__main__':
    main()
