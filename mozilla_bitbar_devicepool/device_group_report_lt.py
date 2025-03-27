import pprint
import os

from mozilla_bitbar_devicepool.lambdatest.api import get_devices


class DeviceGroupReportLt:
    def __init__(self):
        self.lt_username = os.environ["LT_USERNAME"]
        self.lt_api_key = os.environ["LT_ACCESS_KEY"]

    def show_report(self):
        devices = get_devices(self.lt_username, self.lt_api_key)
        result_dict = {}
        # TODO: display a report of the devices including a count of each device type
        for device in devices["data"]["private_cloud_devices"]:
            name = device["name"]
            os_version = device["os_version"]
            udid = device["udid"]
            # if device is not in the result_dict, add it
            if f"{name}-{os_version}" not in result_dict:
                result_dict[f"{name}-{os_version}"] = {
                    "name": name,
                    "os_version": os_version,
                    "udids": [udid],
                    "count": 1,
                }
            else:
                result_dict[f"{name}-{os_version}"]["count"] += 1
                result_dict[f"{name}-{os_version}"]["udids"].append(udid)
            # result_dict[f"{name}-{os_version}"]
            # print(f"{device['name']} - {device['os_version']} - {device['udid']}")
        # pprint.pprint(devices)
        pprint.pprint(result_dict)


def main():
    device_group_report_lt = DeviceGroupReportLt()
    device_group_report_lt.show_report()
