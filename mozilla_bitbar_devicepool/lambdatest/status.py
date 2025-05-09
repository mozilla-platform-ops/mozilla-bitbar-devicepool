# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import pprint

from mozilla_bitbar_devicepool.lambdatest.api import get_devices, get_jobs

# idea: uses api data to build a status/state
#   - a presentation layer for data from api.py


# TODO: make these constants and use them everywhere
# list of possible lt states:
# 'aborted': 0,
# 'cancelled': 0,
# 'completed': 0,
# 'created': 0,
# 'error': 0,
# 'failed': 0,
# 'ignored': 0,
# 'in_progress': 1,
# 'lambda_error': 0,
# 'log_available': 0,
# 'muted': 0,
# 'passed': 0,
# 'skipped': 0,
# 'stopped': 0,
# 'timeout': 0},


class Status:
    def __init__(self, lt_username, lt_api_key):
        self.lt_username = lt_username
        self.lt_api_key = lt_api_key

    # jobs

    def get_jobs(self, jobs=100):
        jobs = get_jobs(self.lt_username, self.lt_api_key, jobs=jobs)
        return jobs

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

    # includes concurrent shards
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
                concurrency = int(job["Tasks"])
                if concurrency > 1:
                    # TODO: running calculates this based on the sub-tasks... should we also do here?
                    initiated_job_count += concurrency
                else:
                    initiated_job_count += 1
        return initiated_job_count

    # TODO: write this so we don't need get_initiated_job_count and get_running_job_count
    # def get_job_count(self, state_filter=None, label_filter=None, jobs=100):
    #     pass

    # includes concurrent shards
    def get_running_job_count(self, label_filter_arr=None, jobs=100):
        # TODO: make label_filter work
        gj_output = get_jobs(
            self.lt_username,
            self.lt_api_key,
            label_filter_arr=label_filter_arr,
            jobs=jobs,
        )
        running_job_count = 0
        for job in gj_output["data"]:
            # TODO: we need to check if the concurrent tasks are running, outer job could be runing but 4/5 jobs done!
            if job["status"] == "running":
                # print(job['id'])
                # print(job['job_label'])
                concurrency = int(job["Tasks"])
                # print(concurrency)
                if concurrency > 1:
                    # print("c")
                    # issue with this is that the tasks could have finished
                    # running_job_count += int(concurrency.split("=")[1])
                    running_job_count += int(
                        job["job_summary"]["scenario_stage_summary"]["status_counts_excluding_retries"]["in_progress"]
                    )
                else:
                    running_job_count += 1
        return running_job_count

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

    # Check if there are busy devices and no running jobs
    device_summary = status.get_device_state_summary()
    busy_device_count = device_summary.get("busy", 0)
    running_job_count = status.get_running_job_count()

    if busy_device_count > 0 and running_job_count == 0:
        # Collect UDIDs of busy devices
        device_list = status.get_device_list()
        busy_udids = []
        for dev_type in device_list:
            for udid, state in device_list[dev_type].items():
                if state == "busy":
                    busy_udids.append(f"{udid} ({dev_type})")

        print(
            "\n⚠️ WARNING: There are {0} busy devices but no running jobs. Devices may be stuck.".format(
                busy_device_count
            )
        )
        print("  Busy device UDIDs:")
        for udid in busy_udids:
            print(f"    - {udid}")


if __name__ == "__main__":  # pragma: no cover
    import os
    import pprint
    import sys

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_ACCESS_KEY"]

    status = Status(lt_username, lt_api_key)

    # pprint.pprint(status.get_running_job_count())
    # sys.exit()

    # pprint.pprint(status.get_jobs())
    for job in status.get_jobs()["data"]:
        print("job number: %s" % job["job_number"])
        print("status: %s" % job["status"])
        print("job label: %s" % job["job_label"])
        # print("device udid: %s" % job["device_udid"])
        # print("device name: %s" % job["device_name"])
        # print("device os: %s" % job["device_os"])
        # print("device status: %s" % job["device_status"])
        if job["status"] == "running":
            # pprint.pprint(job)
            # where number of currently running is for concurrent jobs
            # TODO: incorporate into functions above
            # print(job["job_summary"]["scenario_stage_summary"]["status_counts_excluding_retries"]["in_progress"])
            print(job["Tasks"])
        print("")
    print("")
    sys.exit()

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
