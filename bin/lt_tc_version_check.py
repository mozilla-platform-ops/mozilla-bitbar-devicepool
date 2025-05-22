#!/usr/bin/env python3

import argparse
import json
import os
import platform
import subprocess
import sys
import urllib.request


def info(msg):
    print(f"INFO: {msg}")


def error(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def success(msg):
    print(f"SUCCESS: {msg}")


def alert(msg):
    print(f"ALERT: {msg}")


def get_latest_tc_version():
    url = "https://api.github.com/repos/taskcluster/taskcluster/releases/latest"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            tag = data.get("tag_name", "")
            return tag.lstrip("v")
    except Exception as e:
        error(f"Failed to fetch latest TC version: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Checks the latest TC version and compares it with the configured version in the setup script."
    )
    parser.add_argument("--change", action="store_true", help="Update the version in the setup script.")
    args = parser.parse_args()

    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    setup_script = os.path.join(root_path, "mozilla_bitbar_devicepool", "lambdatest", "user_script", "setup_script.sh")
    if not os.path.isfile(setup_script):
        error(f"Setup script not found at {setup_script}")

    # Use gsed on macOS, sed otherwise
    sed_cmd = "gsed" if platform.system() == "Darwin" else "sed"
    if sed_cmd == "gsed" and not shutil.which("gsed"):
        error("gsed could not be found, please install it with brew install gnu-sed")

    # Get latest TC version
    latest_tc_version = get_latest_tc_version()
    print("latest tc version: ")
    print(f"  {latest_tc_version}")

    # Get configured TC version using rg
    try:
        rg_output = subprocess.check_output(["rg", "^TC_VERSION", setup_script], text=True)
        configured_tc_version = rg_output.split("=", 1)[1].strip()
    except subprocess.CalledProcessError:
        error("Unable to find TC_VERSION in setup script.")

    print("configured version in lt setup: ")
    print(f"  {configured_tc_version}")

    if latest_tc_version == configured_tc_version:
        info("Versions are the same, no action needed.")
        sys.exit(0)

    if args.change:
        info("Changing version in setup file...")
        try:
            subprocess.check_call([sed_cmd, "-i", f"s/^TC_VERSION=.*/TC_VERSION={latest_tc_version}/", setup_script])
            success(f"Version changed to: {latest_tc_version}")
        except subprocess.CalledProcessError as e:
            error(f"Failed to update version: {e}")
    else:
        # TODO: show changelog link (https://docs.taskcluster.net/docs/changelog?to=v84.0.2&from=v83.3.0&audience=WORKER-DEPLOYERS)
        # alert("Versions are different!")
        cl_url = f"https://docs.taskcluster.net/docs/changelog?to=v{latest_tc_version}&from=v{configured_tc_version}&audience=WORKER-DEPLOYERS"
        alert("Latest version is greater than configured version!")
        print("")
        print(f"  Changes: {cl_url}")
        print("")
        print("  Please inspect the changes and if they are acceptable, ")
        print("  rerun this script with '--change' to update the version.")


if __name__ == "__main__":
    import shutil

    main()
