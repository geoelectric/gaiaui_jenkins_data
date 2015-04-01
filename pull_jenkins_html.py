#!/usr/bin/env python

from ConfigParser import ConfigParser
import os
import sys
from urlparse import urljoin

from jenkins import Jenkins
import requests


cfg = ConfigParser()
cfg.read('./config.ini')
JENKINS_LOCATION = cfg.get('Jenkins', 'server')
USERNAME = cfg.get('Jenkins', 'user')
PASSWORD = cfg.get('Jenkins', 'password')

if len(sys.argv) > 1:
    JOBS = [sys.argv[1]]
else:
    JOBS = [
        "flame-kk-319.b2g-inbound.tinderbox.ui.functional.sanity",
        "flame-kk-319.b2g-inbound.tinderbox.ui.functional.smoke",
        "flame-kk-319.mozilla-aurora.nightly.ui.functional.non-smoke",
        "flame-kk-319.mozilla-aurora.nightly.ui.functional.sanity",
        "flame-kk-319.mozilla-aurora.nightly.ui.functional.smoke",
        "flame-kk-319.mozilla-b2g34_v2_1.nightly.ui.functional.non-smoke",
        "flame-kk-319.mozilla-b2g34_v2_1.nightly.ui.functional.sanity",
        "flame-kk-319.mozilla-b2g34_v2_1.nightly.ui.functional.smoke",
        "flame-kk-319.mozilla-central.nightly.ui.functional.non-smoke.1",
        "flame-kk-319.mozilla-central.nightly.ui.functional.non-smoke.2",
        "flame-kk-319.mozilla-central.nightly.ui.functional.sanity",
        "flame-kk-319.mozilla-central.nightly.ui.functional.smoke",
        "flame-kk-319.mozilla-central.tinderbox.ui.functional.non-smoke.1",
        "flame-kk-319.mozilla-central.tinderbox.ui.functional.non-smoke.2",
        "flame-kk-319.mozilla-central.tinderbox.ui.functional.sanity",
        "flame-kk-319.mozilla-central.tinderbox.ui.functional.smoke",
        "flame-kk-319.mozilla-inbound.tinderbox.ui.functional.sanity"
    ]

j = Jenkins(JENKINS_LOCATION, USERNAME, PASSWORD)

for n in JOBS:
    highest_job = j.get_job_info(n).get('builds')[0].get('number')
    for b in range(highest_job, 0, -1):
        path = os.path.join(n, str(b), 'output.html')
        if os.path.exists(path):
            break
        url = urljoin(JENKINS_LOCATION, '/'.join(['job', n, str(b),
                                                  'HTML_Report/index.html']))
        r = requests.get(url)
        if r.status_code == 200:
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(os.path.dirname(path))
            with open(path, 'w') as f:
                print 'Downloading to %s' % path
                f.write(r.text.encode('utf8'))
