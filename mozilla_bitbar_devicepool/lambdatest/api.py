# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import base64
import os
import pprint
from datetime import timedelta

import requests.adapters
import requests_cache
from urllib3.util import Retry

# Create a cached session with 10 second expiry
# Only requests using this session will be cached
cached_session = requests_cache.CachedSession(
    cache_name="lambdatest_cache", backend="memory", expire_after=timedelta(seconds=8)
)

# Configure retry strategy
retry_strategy = Retry(
    total=5,
    backoff_factor=0.1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
cached_session.mount("http://", adapter)
cached_session.mount("https://", adapter)

# https://www.lambdatest.com/support/api-doc/


# WORKS
#   - must use is_cursor_base_pagination=true
#  curl -X GET "https://api.hyperexecute.cloud/v1.0/jobs?show_test_summary=false&is_cursor_base_pagination=true" -H  "accept: application/json" -H  "Authorization: Basic REDACTED" | jsonpp
#
# /v1.0/jobs
# timeout arg: 10 seconds to establish connection, 30 seconds to read response
def get_jobs(
    lt_username,
    lt_api_key,
    label_filter_arr=None,
    jobs=100,
    page_size=100,
    show_test_summary=False,
    timeout=(10, 30),
    status=None,
):
    # check that jobs is greater than page_size
    if jobs < page_size:
        raise ValueError("jobs must be greater than or equal to page_size")

    url_base = (
        "https://api.hyperexecute.cloud/v1.0/jobs"
        f"?show_test_summary={show_test_summary}"
        f"&is_cursor_base_pagination=true"
        f"&limit={page_size}"
    )

    # add status filter if provided
    if status:
        if isinstance(status, str):
            status = [status]
        status_filter = ",".join(status)
        url_base += f"&status={status_filter}"

    headers = {}
    auth_string = f"{lt_username}:{lt_api_key}"
    base64_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    headers["Authorization"] = f"Basic {base64_auth_string}"

    all_jobs = []
    next_cursor = None
    fetched = 0

    while True:
        url = url_base
        if next_cursor:
            url += f"&cursor={next_cursor}"

        response = cached_session.get(url, headers=headers, timeout=timeout)
        print(f"Fetching {url}...")
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(f"  while fetching {url}")
            print(response.text)
            return None
        result = response.json()

        jobs_data = result.get("data", [])
        if label_filter_arr:
            filtered_jobs = []
            for job in jobs_data:
                job_label_data = job.get("job_label")
                if not job_label_data:
                    continue
                job_labels = job["job_label"]
                if all(label in job_labels for label in label_filter_arr):
                    filtered_jobs.append(job)
            jobs_data = filtered_jobs

        # update next_cursor with the last job's job_number
        if jobs_data:
            next_cursor = jobs_data[-1]["job_number"]

        all_jobs.extend(jobs_data)
        fetched += len(jobs_data)

        # Check if we have enough jobs or no more pages
        # next_cursor = result.get("next_cursor") #job['job_number']
        if fetched >= jobs:
            break

    # Trim to the requested number of jobs
    # TODO: needed?
    all_jobs = all_jobs[:jobs]

    # Return in the same format as before
    result["data"] = all_jobs
    return result


# WORKS
# timeout arg: 10 seconds to establish connection, 30 seconds to read response
def get_devices(lt_username, lt_api_key, timeout=(10, 30)):
    # curl --location --request GET 'https://mobile-api.lambdatest.com/mobile-automation/api/v1/privatecloud_devices' -H  "Authorization: Basic REDACTED"

    url = "https://mobile-api.lambdatest.com/mobile-automation/api/v1/privatecloud_devices"

    # do basic auth
    headers = {"accept": "application/json"}
    # craft a header that does basic auth with username and api key
    auth_string = f"{lt_username}:{lt_api_key}"
    base64_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    headers["Authorization"] = f"Basic {base64_auth_string}"

    # Use cached_session instead of requests directly
    response = cached_session.get(url, headers=headers, timeout=timeout)
    # check the response code
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(f"  while fetching {url}")
        print(response.text)
        return None
    return response.json()  # list of jobs


if __name__ == "__main__":  # pragma: no cover
    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_ACCESS_KEY"]

    # output = get_devices(lt_username, lt_api_key)
    # pprint.pprint(output)

    # show get_jobs() output
    output = get_jobs(lt_username, lt_api_key)
    pprint.pprint(output)

    import sys

    sys.exit(0)

    # jobs = get_jobs(lt_username, lt_api_key, ['aje_123', 'fun_fun_456'])
    # jobs = get_jobs(lt_username, lt_api_key, ["123", "456"])
    jobs = get_jobs(lt_username, lt_api_key, ["mbd"])
    pprint.pprint(jobs)

    # this code moved to status.py
    # job_result_dict = {}
    # for job in jobs['data']:
    #     # pprint.pprint(job)
    #     # print(f"{job["job_number"]} {job["status"]}")
    #     job_result_dict[job["job_number"]] = job["status"]
    # pprint.pprint(job_result_dict)
