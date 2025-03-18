# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import requests
import base64

# https://www.lambdatest.com/support/api-doc/


# WORKS
#   - must use is_cursor_base_pagination=true
#  curl -X GET "https://api.hyperexecute.cloud/v1.0/jobs?show_test_summary=false&is_cursor_base_pagination=true" -H  "accept: application/json" -H  "Authorization: Basic REDACTED" | jsonpp
#
# /v1.0/jobs
def get_jobs(lt_username, lt_api_key, show_test_summary=False):
    url = (
        "https://api.hyperexecute.cloud/v1.0/jobs"
        f"?show_test_summary={show_test_summary}"
        f"&is_cursor_base_pagination=true"
    )

    # do basic auth
    headers = {}
    # craft a header that does basic auth with username and api key
    auth_string = f"{lt_username}:{lt_api_key}"
    base64_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    headers["Authorization"] = f"Basic {base64_auth_string}"

    response = requests.get(url, headers=headers)
    print(response)
    return response.json()  # list of jobs


if __name__ == "__main__":
    import os

    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_API_KEY"]
    jobs = get_jobs(lt_username, lt_api_key)
    print(jobs)
