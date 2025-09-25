# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import pprint

# import datetime
from datetime import datetime

import requests
import taskcluster
from natsort import natsorted
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

ROOT_URL = "https://firefox-ci-tc.services.mozilla.com"


class TaskclusterClient:
    def __init__(self, verbose=False):
        self.verbose = verbose
        # self.queue = taskcluster.Queue()
        cfg = {"rootUrl": ROOT_URL}

        with open(os.path.expanduser("~/.tc_token")) as json_file:
            data = json.load(json_file)
        creds = {"clientId": data["clientId"], "accessToken": data["accessToken"]}

        self.tc_wm = taskcluster.WorkerManager({"rootUrl": ROOT_URL, "credentials": creds})

    def get_quarantined_worker_names(self, provisioner, worker_type, results=None):
        if results is None:
            results = self.get_quarantined_workers(provisioner, worker_type)
        return_arr = []
        for result in results:
            return_arr.append(result["workerId"])
        # pprint.pprint(natsorted(return_arr))
        return natsorted(return_arr)

    def get_quarantined_workers(self, provisioner, worker_type, results=None):
        if results is None:
            results = self.tc_wm.listWorkers(provisioner, worker_type)
        # do filtering
        quarantined_workers = []
        for item in results["workers"]:
            if self.verbose:
                pprint.pprint(item)
            # check if quarantineUntil is set and in the future
            if "quarantineUntil" in item:
                if item["quarantineUntil"] is None:
                    # if self.verbose:
                    #     print("Not quarantined: %s" % item["workerId"])
                    item["quarantined"] = False
                else:
                    # if self.verbose:
                    #     print("Quarantined: %s" % item["workerId"])

                    # cast date string to datetime object
                    # item["quarantineUntil"] = taskcluster.utils.fromNow(item["quarantineUntil"])
                    dt = datetime.fromisoformat(item["quarantineUntil"].replace("Z", "+00:00"))

                    # check if date is in the future
                    if dt > taskcluster.utils.fromNow("0 hour"):
                        # print("Quarantined (date in future): %s" % item["workerId"])
                        item["quarantined"] = True
                        quarantined_workers.append(item)
                    else:
                        # print("Not quarantined (date in past): %s" % item["workerId"])
                        pass
            else:
                # if self.verbose:
                #     print("Not quarantined: %s" % item["workerId"])
                item["quarantined"] = False

        return quarantined_workers


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

    taskcluster_queue_url = "https://firefox-ci-tc.services.mozilla.com/api/queue/v1/pending/%s/%s" % (
        provisioner_id,
        worker_type,
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


# main
if __name__ == "__main__":  # pragma: no cover
    tci = TaskclusterClient(verbose=True)
    provisioner_id = "proj-autophone"
    # worker_type = "t-lambda-a55-perf"
    worker_type = "gecko-t-lambda-perf-a55"

    # pending tasks
    pending_tasks = get_taskcluster_pending_tasks(provisioner_id, worker_type, verbose=True)
    print("Pending tasks: %s" % pending_tasks)

    # quarantined workers
    quarantined_workers = tci.get_quarantined_worker_names(provisioner_id, worker_type)
    print("Quarantined workers: %s" % quarantined_workers)
    print("Number of quarantined workers: %s" % len(quarantined_workers))
