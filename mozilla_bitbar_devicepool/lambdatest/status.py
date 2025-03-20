# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import pprint

from mozilla_bitbar_devicepool.lambdatest.api import get_jobs, get_devices

# idea: uses api data to build a status/state
#   - a presentation layer for data from api.py


class Status:
    def __init__(self, lt_username, lt_api_key):
        self.lt_username = lt_username
        self.lt_api_key = lt_api_key

    # jobs

    def get_job_dict(self, jobs=100):
        jobs = get_jobs(self.lt_username, self.lt_api_key, jobs=jobs)
        pprint.pprint(jobs)
        job_result_dict = {}
        for job in jobs["data"]:
            job_result_dict[job["job_number"]] = job["status"]
        # TODO: return sorted?
        return job_result_dict

    # format:
    # {
    #   'running': 12,
    #   'aborted': 5,
    #   ...
    # }
    #
    # possible states:
    #  - initiated
    #  - running
    #  - completed
    #  - aborted
    #  - failed
    #  - timeout
    #
    def get_job_summary(self, jobs=100):
        gj_output = get_jobs(self.lt_username, self.lt_api_key, jobs=jobs)
        result_dict = {}
        for job in gj_output["data"]:
            status = job["status"]
            if status in result_dict:
                result_dict[status] += 1
            else:
                result_dict[status] = 1
        return result_dict

    def get_initiated_job_count(self, label_filter=None, jobs=100):
        # TODO: make label_filter work
        gj_output = get_jobs(self.lt_username, self.lt_api_key, jobs=jobs)
        initiated_job_count = 0
        for job in gj_output["data"]:
            if job["status"] == "initiated":
                initiated_job_count += 1
        return initiated_job_count

    # TODO: find out which job is for which 'workerType' otherwise we can only run one workerType...
    #   - use job label? `--labels` arg to hyperexecute

    # devices

    # format:
    # {
    #   {'a55': {'RXYA1821': 'online',
    #            'RXYA1823': 'busy'
    #            'RXYA1824': 'online'},
    #   {'a51': {'DB123212': 'online'}
    # }
    def get_device_list(self, verbose=False):
        result_dict = {}
        output = get_devices(self.lt_username, self.lt_api_key)
        for device in output["data"]["private_cloud_devices"]:
            if verbose:
                pprint.pprint(device)
            # TODO: make the key include OS? 'fullOsVersion'
            # get the current value in result_dict['name'] or create a new dict
            device_type_entry = result_dict.get(device["name"], {})
            device_type_entry[device["udid"]] = device["status"]
            result_dict[device["name"]] = device_type_entry
        return result_dict


if __name__ == "__main__":
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_API_KEY"]

    status = Status(lt_username, lt_api_key)

    pprint.pprint(status.get_job_dict())
    # print("")
    # sys.exit(0)
    print(f"initiated job count: {status.get_initiated_job_count()}")
    print("job summary:")
    pprint.pprint(status.get_job_summary())

    print("")

    print("device list:")
    pprint.pprint(status.get_device_list())

    sys.exit(0)
