# idea: uses api data to build a status/state

import pprint

from mozilla_bitbar_devicepool.lambdatest.api import get_jobs


class Status:
    def __init__(self, lt_username, lt_api_key):
        self.lt_username = lt_username
        self.lt_api_key = lt_api_key

    def get_job_dict(self, jobs=100):
        jobs = get_jobs(self.lt_username, self.lt_api_key, jobs=jobs)
        # pprint.pprint(jobs)
        job_result_dict = {}
        for job in jobs["data"]:
            job_result_dict[job["job_number"]] = job["status"]
        # TODO: return sorted?
        return job_result_dict

    def get_initiated_job_count(self, jobs=100):
        jobs = get_jobs(self.lt_username, self.lt_api_key, jobs=jobs)
        initiated_job_count = 0
        for job in jobs["data"]:
            if job["status"] == "initiated":
                initiated_job_count += 1
        return initiated_job_count


if __name__ == "__main__":
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_API_KEY"]

    status = Status(lt_username, lt_api_key)
    pprint.pprint(status.get_job_dict())
    print(f"initiated job count: {status.get_initiated_job_count()}")
