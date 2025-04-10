# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import pprint

from mozilla_bitbar_devicepool.lambdatest.api import get_jobs, get_devices
from mozilla_bitbar_devicepool.lambdatest.util import array_key_search

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
        # TODO?: return sorted?
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
    def get_job_summary(self, label_filter_arr=None, jobs=100):
        # TODO: make label_filter work
        gj_output = get_jobs(
            self.lt_username,
            self.lt_api_key,
            label_filter_arr=label_filter_arr,
            jobs=jobs,
        )
        result_dict = {}
        for job in gj_output["data"]:
            status = job["status"]
            if status in result_dict:
                result_dict[status] += 1
            else:
                result_dict[status] = 1
        return result_dict

    def get_initiated_job_count(self, label_filter_arr=None, jobs=100):
        # TODO: make label_filter work
        gj_output = get_jobs(
            self.lt_username,
            self.lt_api_key,
            label_filter_arr=label_filter_arr,
            jobs=jobs,
        )
        initiated_job_count = 0
        for job in gj_output["data"]:
            if job["status"] == "initiated":
                initiated_job_count += 1
        return initiated_job_count

    # TODO: write this so we don't need get_initiated_job_count and get_running_job_count
    def get_job_count(self, state_filter=None, label_filter=None, jobs=100):
        pass

    # TODO: make this generic get_job_count and pass in an array of states to include
    def get_running_job_count(self, label_filter_arr=None, jobs=100):
        # TODO: make label_filter work
        gj_output = get_jobs(
            self.lt_username,
            self.lt_api_key,
            label_filter_arr=label_filter_arr,
            jobs=jobs,
        )
        initiated_job_count = 0
        for job in gj_output["data"]:
            # pprint.pprint(job)
            if job["status"] == "running":
                # TODO: inspect label for 'c=X'
                # print(job['job_label'])
                concurrency = array_key_search("c=", job["job_label"])
                if concurrency:
                    initiated_job_count = int(concurrency.split("=")[1])
                else:
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
    def get_device_list(self, device_type_and_os_filter=None, verbose=False):
        result_dict = {}
        output = get_devices(self.lt_username, self.lt_api_key)
        if not output:
            return result_dict
        # if verbose:
        #     pprint.pprint(output)

        device_type = None
        device_os = None
        # TODO: sanity check this arg
        if device_type_and_os_filter:
            device_type = device_type_and_os_filter.split("-")[0]
            device_os = device_type_and_os_filter.split("-")[1]

        for device in output["data"]["private_cloud_devices"]:
            if verbose:
                pprint.pprint(device)
            # TODO: make the key include OS? 'fullOsVersion'
            # get the current value in result_dict['name'] or create a new dict
            device_type_entry = result_dict.get(device["name"], {})
            device_type_entry[device["udid"]] = device["status"]
            if device_type_and_os_filter:
                # pprint.pprint(device)
                # result_dict[device["name"]] = device_type_entry
                if device_type == device["name"] and device_os == device["fullOsVersion"]:
                    result_dict[device["name"]] = device_type_entry
            else:
                result_dict[device["name"]] = device_type_entry
        return result_dict

    def get_device_state_summary(self, device_type_and_os_filter=None):
        results = self.get_device_list(device_type_and_os_filter=device_type_and_os_filter)
        # results dict format: {state: count, ...}
        result_dict = {}
        for dev_type in results:
            for udid in results[dev_type]:
                # get or set the state
                state = results[dev_type][udid]
                if state in result_dict:
                    result_dict[state] += 1
                else:
                    result_dict[state] = 1
        return result_dict

    def get_device_state_summary_by_device(self):
        results = self.get_device_list()
        result_dict = {}
        for dev_type in results:
            for udid in results[dev_type]:
                # get or set the state
                state = results[dev_type][udid]
                if dev_type in result_dict and state in result_dict[dev_type]:
                    result_dict[dev_type][state] += 1
                elif dev_type in result_dict:
                    result_dict[dev_type][state] = 1
                else:
                    result_dict[dev_type] = {state: 1}
        return result_dict

    def get_device_state_count(self, device_type_and_os_filter, state):
        results = self.get_device_list(device_type_and_os_filter=device_type_and_os_filter)
        result_int = 0
        for dev_type in results:
            for udid in results[dev_type]:
                # get or set the state
                device_state = results[dev_type][udid]
                if device_state == state:
                    result_int += 1
        return result_int


def lt_status_main():
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_ACCESS_KEY"]

    status = Status(lt_username, lt_api_key)

    print("device list: ")
    pprint.pprint(status.get_device_list())
    print("")

    print("device summary by device:")
    pprint.pprint(status.get_device_state_summary_by_device())
    print("")

    print("device summary:")
    r = status.get_device_state_summary()
    pprint.pprint(r)

    print("")

    print("job summary:")
    pprint.pprint(status.get_job_summary())


if __name__ == "__main__":
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_ACCESS_KEY"]

    status = Status(lt_username, lt_api_key)

    pprint.pprint(status.get_running_job_count())

    # print("device list: ")
    # pprint.pprint(status.get_device_list())
    # print("")

    # print("device summary by device:")
    # pprint.pprint(status.get_device_state_summary_by_device())
    # print("")

    # # r = status.get_device_list("Galaxy A55 5G-14")
    # print("device summary:")
    # # pprint.pprint(r)
    # r = status.get_device_state_summary()
    # # # r = status.get_device_state_summary("Galaxy A55 5G-14")
    # # r = status.get_device_state_summary("Galaxy A55 5G-14")
    # pprint.pprint(r)
    # # r = status.get_device_state_count("Galaxy A55 5G-14", "active")
    # # pprint.pprint(r)

    # # r = status.get_job_summary(["mbd"])
    # # pprint.pprint(r)

    # print("")

    # # pprint.pprint(status.get_job_dict())
    # # # print("")
    # # # sys.exit(0)
    # # print(f"initiated job count: {status.get_initiated_job_count()}")
    # print("job summary:")
    # pprint.pprint(status.get_job_summary())

    # # print("")

    # # print("device list:")
    # # pprint.pprint(status.get_device_list())

    # # sys.exit(0)
