# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
from string import Template

TEMPLATE_FILENAME = "hyperexecute.yaml.tmpl"


def write_config(
    tc_client_id,
    tc_access_token,
    tc_worker_type,
    lt_app_url,
    udid=None,
    concurrency=1,
    user_script_dir=None,
    path="/tmp/mozilla-lt-devicepool-job-dir/hyperexecute.yaml",
):
    """
    Generate a LambdaTest HyperExecute configuration and write it to a file.

    Args:
        tc_client_id (str): Taskcluster client ID for authentication.
        tc_access_token (str): Taskcluster access token for authentication.
        lt_app_url (str): URL to the application under test on LambdaTest.
        udid (str, optional): The unique device identifier if targeting a specific device. Defaults to None.
        concurrency (int, optional): Number of parallel test executions. Defaults to 1.
        user_script_dir (str): Path to the userscripts version directory containing
                               hyperexecute.yaml.tmpl. Required.
        path (str, optional): Destination path for the config file.
                              Defaults to "/tmp/mozilla-lt-devicepool-job-dir/hyperexecute.yaml".

    Returns:
        str: Path where the configuration file was written.
    """

    # show all options passed in
    logging.debug(f"write_config: tc_client_id: {tc_client_id}")
    logging.debug(f"write_config: tc_access_token: {tc_access_token}")
    logging.debug(f"write_config: tc_worker_type: {tc_worker_type}")
    logging.debug(f"write_config: lt_app_url: {lt_app_url}")
    logging.debug(f"write_config: udid: {udid}")
    logging.debug(f"write_config: user_script_dir: {user_script_dir}")
    logging.debug(f"write_config: path: {path}")
    logging.debug(f"write_config: concurrency: {concurrency}")

    config = return_config(
        tc_client_id,
        tc_access_token,
        tc_worker_type,
        lt_app_url,
        udid,
        concurrency,
        user_script_dir,
    )

    # mkdir -p the path
    dir_to_create = os.path.dirname(path)
    os.makedirs(dir_to_create, exist_ok=True)

    with open(path, "w") as f:
        f.write(config)
    return path


def return_config(
    tc_client_id,
    tc_access_token,
    tc_worker_type,
    lt_app_url,
    udid=None,
    concurrency=1,
    user_script_dir=None,
):
    """
    Generate a LambdaTest HyperExecute configuration YAML as a string.

    The YAML template is loaded from <user_script_dir>/hyperexecute.yaml.tmpl so that
    each userscripts version can ship its own job-config shape alongside its scripts.

    Args:
        tc_client_id (str): Taskcluster client ID for authentication.
        tc_access_token (str): Taskcluster access token for authentication.
        lt_app_url (str): URL to the application under test on LambdaTest.
        udid (str, optional): The unique device identifier if targeting a specific device. Defaults to None.
        concurrency (int, optional): Number of parallel test executions. Defaults to 1.
        user_script_dir (str): Path to the userscripts version directory containing
                               hyperexecute.yaml.tmpl. Required.

    Returns:
        str: Complete HyperExecute YAML configuration as a string.
    """
    # TODO: document decision to inject secrets here vs using lt's built-in secret storage
    #   thinking:
    #   - they already have the secrets in their systems
    #   - why store it in another spot that we have to maintain?
    #
    # template code for using LT secrets:
    # use lt's built-in secret storage
    # TASKCLUSTER_ACCESS_TOKEN: ${{.secrets.TC_ACCESS_TOKEN}}
    # TASKCLUSTER_CLIENT_ID: ${{.secrets.TC_CLIENT_ID}}

    if not user_script_dir:
        raise ValueError("return_config requires user_script_dir")

    test_discover_cmd = ""
    for i in range(concurrency):
        test_discover_cmd += f'echo "taskcluster generic-worker {i}"; '

    fixed_ip_line = "#"
    if udid:
        fixed_ip_line = f'fixedIP: "{udid}"'

    template_path = os.path.join(user_script_dir, TEMPLATE_FILENAME)
    with open(template_path, "r") as f:
        template = Template(f.read())

    return template.substitute(
        tc_client_id=tc_client_id,
        tc_access_token=tc_access_token,
        tc_worker_type=tc_worker_type,
        lt_app_url=lt_app_url,
        concurrency=concurrency,
        test_discover_cmd=test_discover_cmd,
        fixed_ip_line=fixed_ip_line,
    )
