# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import requests


def get_taskcluster_pending_tasks(provisioner_id, worker_type, verbose=False):
    taskcluster_queue_url = (
        "https://firefox-ci-tc.services.mozilla.com/api/queue/v1/pending/%s/%s"
        % (provisioner_id, worker_type)
    )
    if verbose:
        print("taskcluster_queue_url: %s" % taskcluster_queue_url)
    r = requests.get(taskcluster_queue_url)
    if verbose:
        print("r.status_code: %s" % r.status_code)
        print("r.text: %s" % r.text if r.text else "r.content: %s" % r.content)
    if r.ok:
        return r.json()["pendingTasks"]
    return 0
