# idea: uses api data to build a status/state

import pprint

from mozilla_bitbar_devicepool.lambdatest.api import get_jobs


class Status:
    def __init__(self, lt_username, lt_api_key):
        self.lt_username = lt_username
        self.lt_api_key = lt_api_key

    def get_job_summary(self):
        jobs = get_jobs(self.lt_username, self.lt_api_key)
        job_result_dict = {}
        for job in jobs["data"]:
            job_result_dict[job["job_number"]] = job["status"]
        # TODO: return sorted?
        return job_result_dict


if __name__ == "__main__":
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_API_KEY"]

    status = Status(lt_username, lt_api_key)
    pprint.pprint(status.get_job_summary())
