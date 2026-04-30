# compares bitbar api devices to devices in the v3 config

import argparse
import os

from testdroid import Testdroid

from mozilla_bitbar_devicepool.bitbar.devices import get_devices
from mozilla_bitbar_devicepool.device_group_report import DeviceGroupReport

TESTDROID_URL = os.environ.get("TESTDROID_URL")
TESTDROID_APIKEY = os.environ.get("TESTDROID_APIKEY")
if TESTDROID_URL and TESTDROID_APIKEY:
    TESTDROID = Testdroid(apikey=TESTDROID_APIKEY, url=TESTDROID_URL)
else:
    TESTDROID = None

_DEFAULT_V3_CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "config-v3-server.yml")


def get_device_names():
    display_names = {}
    for device in get_devices():
        dn = device["displayName"]
        # skip docker builder, not a real device
        if dn == "Docker Builder":
            continue
        display_names[dn] = True

    return sorted(display_names.keys())


def main():
    parser = argparse.ArgumentParser(description="Compare Bitbar API devices to v3 config devices")
    parser.add_argument(
        "--config-file",
        "-c",
        dest="config_file",
        default=_DEFAULT_V3_CONFIG,
        help="Path to device config file (default: config/config-v3-server.yml)",
    )
    args = parser.parse_args()

    try:
        api_devices = get_device_names()
    except AttributeError as e:
        print("Please ensure the bitbar env vars have been set!")
        print("  - TESTDROID_URL and TESTDROID_APIKEY")
        print("full exception follows")
        print("")
        raise e
    dgri = DeviceGroupReport(quiet=True, config_path=args.config_file)

    api_devices_set = set(api_devices)
    print("api devices: ")
    print(f"  {api_devices}")
    print(f"  count: {len(api_devices)}")

    print("")

    config_devices = dgri.get_config_devices()
    config_devices_set = set(config_devices)
    print(f"config ({dgri.config_path}) devices: ")
    print(f"  {config_devices}")
    print(f"  count: {len(config_devices)}")

    print("")
    print("api - config: ")
    print(f"  {sorted(api_devices_set.difference(config_devices_set))}")
    print("config - api: ")
    print(f"  {sorted(config_devices_set.difference(api_devices_set))}")


if __name__ == "__main__":  # pragma: no cover
    main()
