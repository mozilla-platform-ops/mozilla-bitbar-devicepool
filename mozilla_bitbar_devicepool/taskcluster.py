# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


def get_taskcluster_pending_tasks(provisioner_id, worker_type, verbose=False):
    # define the retry strategy
    retry_strategy = Retry(
        total=4,  # maximum number of retries
        backoff_factor=2,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],  # the HTTP status codes to retry on
    )

    # create an HTTP adapter with the retry strategy and mount it to the session
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # create a new session object
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    taskcluster_queue_url = (
        "https://firefox-ci-tc.services.mozilla.com/api/queue/v1/pending/%s/%s"
        % (provisioner_id, worker_type)
    )
    if verbose:
        print("taskcluster_queue_url: %s" % taskcluster_queue_url)
    # Adding timeouts: 10 seconds to establish connection, 30 seconds to read response
    r = session.get(taskcluster_queue_url, timeout=(10, 30))
    if verbose:
        print("r.status_code: %s" % r.status_code)
        print("r.text: %s" % r.text if r.text else "r.content: %s" % r.content)
    if r.ok:
        return r.json()["pendingTasks"]
    return 0
