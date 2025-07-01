import argparse
import pprint

from mozilla_bitbar_devicepool.configuration_lt import ConfigurationLt

# from mozilla_bitbar_devicepool.lambdatest import status
from mozilla_bitbar_devicepool.util import misc


class DeviceGroupReportLt:
    def __init__(self, config_path=None, verbose=False):
        self.verbose = verbose
        self.config_path = config_path
        # Using ConfigurationLt to handle config loading
        self.config_object = ConfigurationLt(ci_mode=True, quiet=True)  # ci_mode=True to avoid credentials check
        self.config_object.configure(config_path=self.config_path)

    def show_report(self, verbose=False):
        config_summary_dict = self.get_config_projects_and_device_types()

        if verbose:
            print("config summary")
            pprint.pprint(config_summary_dict)

        output_dict = {}
        for project_name, device_groups in self.config_object.config.get("device_groups", {}).items():
            if device_groups is not None:
                # Count devices in each project
                device_count = len(device_groups)
                output_dict[project_name] = device_count

        print("")
        print("pool summary")
        pprint.pprint(output_dict, indent=2)

        print("")
        print("device types")
        pprint.pprint(self.get_device_types(), indent=2)

        print("")
        print(f"total devices: {sum(output_dict.values())}")

        # Add device types information if needed
        if verbose and hasattr(self, "status_object") and self.status_object:
            print("\nDevice types from LambdaTest API:")
            device_list = self.status_object.get_device_list()
            pprint.pprint(device_list)

    def get_config_projects_and_device_types(self):
        """Extract project names and their device selectors from config"""
        return_dict = {}

        for project_name, _project_config in self.config_object.config.get("projects", {}).items():
            if project_name != "defaults":
                # TODO: elimiate this if we don't need to do anything now
                pass

        return return_dict

    def get_device_types(self):
        """
        Count the number of devices of each type based on lt_device_selector in device_groups.

        Returns:
            dict: Dictionary with device types as keys and their counts as values
        """
        # Create a ConfigurationLt instance to access the config
        config_object = self.config_object

        device_types = {}

        # iterate through the 'projects' in the config
        for project_name, project_config in config_object.config.get("projects", {}).items():
            devices_for_project = config_object.config.get("device_groups", {})[project_name]
            # no need to worry about the 'defaults' project, already handled in configure()
            lt_device_selector = project_config.get("lt_device_selector")
            if lt_device_selector:
                # project is ready for use
                device_types[lt_device_selector] = len(devices_for_project)
        # Sort the device types by their counts in descending order
        device_types = dict(sorted(device_types.items(), key=lambda item: item[1], reverse=True))

        return device_types


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LambdaTest device group report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show more detailed output")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    args = parser.parse_args()

    banner = """
 __                __       __       __               __         __
|  .---.-.--------|  |--.--|  .---.-|  |_.-----.-----|  |_   .--|  .-----.----.
|  |  _  |        |  _  |  _  |  _  |   _|  -__|__ --|   _|  |  _  |  _  |   _|
|__|___._|__|__|__|_____|_____|___._|____|_____|_____|____|  |_____|___  |__|
                                                                   |_____|
"""  # noqa: W605
    print(banner.lstrip("\n"))
    print(f"  generated on {misc.get_utc_date_string()} ({misc.get_git_info()})")
    print()

    device_group_report_lt = DeviceGroupReportLt(config_path=args.config, verbose=args.verbose)
    device_group_report_lt.show_report(verbose=args.verbose)


if __name__ == "__main__":  # pragma: no cover
    main()
