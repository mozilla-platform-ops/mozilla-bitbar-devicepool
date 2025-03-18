# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import requests

# https://www.lambdatest.com/support/api-doc/


# curl -X GET "https://api.hyperexecute.cloud/v1.0/jobs?show_test_summary=true&limit=2000&is_cursor_base_pagination=false" -H  "accept: application/json"

# curl -X GET "https://api.hyperexecute.cloud/v1.0/jobs?show_test_summary=true&is_cursor_base_pagination=false" -H  "accept: application/json" -H  "Authorization: Basic BASE64_STRING"

# curl from https://www.lambdatest.com/support/api-doc/?key=hyperexecute
#
# (mozilla-bitbar-devicepool-py3.12) powderdry  mozilla-bitbar-devicepool git:(lt_work) ✗  ➜  curl -X GET "https://api.hyperexecute.cloud/v1.0/jobs?show_test_summary=false&is_cursor_base_pagination=false" -H  "accept: application/json" -H  "Authorization: Basic REDACTED"
# {"error":{"Number":1054,"Message":"Unknown column 'tj.team_id' in 'field list'"},"status":"failed"}%
# (mozilla-bitbar-devicepool-py3.12) powderdry  mozilla-bitbar-devicepool git:(lt_work) ✗  ➜


#
# /v1.0/jobs
def get_jobs(lt_username, lt_api_key):
    url = "https://api.hyperexecute.cloud/v1.0/jobs"
    # do basic auth
    headers = {
        "accept": "application/json",
    }

    response = requests.get(url, headers=headers)
    print(response)
    return response.json()  # list of jobs


if __name__ == "__main__":
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_API_KEY"]
    jobs = get_jobs(lt_username, lt_api_key)
    print(jobs)
