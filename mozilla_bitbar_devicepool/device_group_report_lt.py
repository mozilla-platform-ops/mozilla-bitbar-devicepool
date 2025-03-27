import pprint
import os
import yaml
import argparse

from mozilla_bitbar_devicepool.util import misc

from mozilla_bitbar_devicepool.lambdatest.api import get_devices


class DeviceGroupReportLt:
    def __init__(self, config_path=None, verbose=False):
        self.lt_username = os.environ["LT_USERNAME"]
        self.lt_api_key = os.environ["LT_ACCESS_KEY"]
        self.verbose = verbose
        if not config_path:
            # get the path of this file
            filename_path = os.path.abspath(__file__)
            root_dir = os.path.abspath(os.path.join(filename_path, "..", ".."))
            self.config_path = os.path.join(root_dir, "config", "lambdatest.yml")
            if verbose:
                print("INFO: Using config file at '%s'." % self.config_path)
        else:
            self.config_path = config_path

    def show_report(self, verbose=False):
        config_summary_dict = self.get_config_projects_and_device_types()
        api_device_summary_dict = self.get_lt_device_report()

        if verbose:
            print("config summary")
            pprint.pprint(config_summary_dict)
            print("")
            print("api summary")
            pprint.pprint(api_device_summary_dict)

        output_dict = {}
        for lt_project in config_summary_dict:
            project_lt_device_selector = config_summary_dict[lt_project]
            count_for_device_type = api_device_summary_dict[project_lt_device_selector][
                "count"
            ]
            output_dict[lt_project] = count_for_device_type
            # print(f"{lt_project} - {count_for_device_type}")

        print("")
        print("pool summary")
        pprint.pprint(output_dict, indent=2)

        print("")
        print("device types")

        output_dict_2 = {}
        for project in api_device_summary_dict:
            device_name = api_device_summary_dict[project]["name"]
            os_version = api_device_summary_dict[project]["os_version"]
            count = api_device_summary_dict[project]["count"]
            output_dict_2[f"{device_name}-{os_version}"] = count
            # print(f"{device_name} - {os_version} - {count}")
        pprint.pprint(output_dict_2, indent=2)

        print("")
        print(f"total devices: {sum(output_dict.values())}")

    def get_config_projects_and_device_types(self):
        return_dict = {}

        # open the config file
        with open(self.config_path, "r") as stream:
            try:
                conf_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        for project in conf_yaml["projects"]:
            if project != "defaults":
                project_name = project
                device_selector = conf_yaml["projects"][project]["lt_device_selector"]
                # print(project)
                # print("  " + device_selector)
                return_dict[project_name] = device_selector
        return return_dict

    def get_lt_device_report(self):
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
        return result_dict
        # pprint.pprint(result_dict)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LambdaTest device group report")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show more detailed output"
    )
    # parser.add_argument('--config', '-c', help='Path to config file')
    # parser.add_argument('--quiet', '-q', action='store_true', help='Suppress informational output')
    args = parser.parse_args()

    banner = r"""
 __                __       __       __               __         __
|  .---.-.--------|  |--.--|  .---.-|  |_.-----.-----|  |_   .--|  .-----.----.
|  |  _  |        |  _  |  _  |  _  |   _|  -__|__ --|   _|  |  _  |  _  |   _|
|__|___._|__|__|__|_____|_____|___._|____|_____|_____|____|  |_____|___  |__|
                                                                   |_____|
"""  # noqa: W605
    print(banner.lstrip("\n"))
    print(f"  generated on {misc.get_utc_date_string()} ({misc.get_git_info()})")
    print()

    device_group_report_lt = DeviceGroupReportLt(verbose=args.verbose)
    device_group_report_lt.show_report(verbose=args.verbose)
