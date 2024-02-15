#!/usr/bin/env python3

import os
import sys

import yaml


def get_len(an_object):
    if an_object:
        return len(an_object)
    else:
        return 0


class DeviceGroupReport:
    def __init__(self, config_path=None, quiet=False):
        self.gw_result_dict = {}
        self.tcw_result_dict = {}
        self.test_result_dict = {}
        self.device_dict = {}  # device types to count
        if not config_path:
            pathname = os.path.dirname(sys.argv[0])
            root_dir = os.path.abspath(os.path.join(pathname, ".."))
            self.config_path = os.path.join(root_dir, "config", "config.yml")
            if not quiet:
                print("Using config file at '%s'." % self.config_path)
        else:
            self.config_path = config_path

    def get_config_devices(self):
        # TODO: store this data in the instance and only read once

        with open(self.config_path, "r") as stream:
            try:
                conf_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        device_names = {}

        for group in conf_yaml["device_groups"]:
            the_item = conf_yaml["device_groups"][group]
            if the_item:
                for device in the_item:
                    if device == "Docker Builder":
                        continue
                    device_names[device] = True
        return sorted(device_names.keys())

    def get_report_dict_v2(self, injected_data=None):
        total_devices = 0

        if injected_data:
            parsed_data = yaml.safe_load(injected_data)
            device_groups = parsed_data.get("device_groups", {})
        else:
            with open(self.config_path, "r") as stream:
                try:
                    parsed_data = yaml.safe_load(stream)
                    device_groups = parsed_data.get("device_groups", {})
                except yaml.YAMLError as exc:
                    print(exc)

        pool_counts = {}
        for group, devices in device_groups.items():
            if isinstance(devices, dict):
                if "-builder" not in group:
                    pool_counts[group] = len(devices)

        device_counts = {}
        for group, devices in device_groups.items():
            if isinstance(devices, dict):
                if "-builder" not in group:
                    modified_group = group.replace("-perf", "").replace("-unit", "")
                    if modified_group not in device_counts:
                        device_counts[modified_group] = 0
                    device_counts[modified_group] += len(devices)
                    total_devices += len(devices)

        # import pprint
        # pprint.pprint(pool_counts)
        # pprint.pprint(device_counts)
        return {
            "pool_counts": pool_counts,
            "device_counts": device_counts,
            "total_devices": total_devices,
        }

    def get_report_dict(self):
        with open(self.config_path, "r") as stream:
            try:
                conf_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        for group in conf_yaml["device_groups"]:
            the_item = conf_yaml["device_groups"][group]
            # filter out the test queue and the builder job
            if "-builder" not in group:
                if "test" in group:
                    self.test_result_dict[group] = get_len(the_item)
                elif (
                    group.endswith("2")
                    or group.startswith("s7")
                    or group.startswith("a51")
                    or group.startswith("pixel5")
                    or group.startswith("pixel6")
                ):
                    self.gw_result_dict[group] = get_len(the_item)
                else:
                    self.tcw_result_dict[group] = get_len(the_item)

        for group in conf_yaml["device_groups"]:
            the_item = conf_yaml["device_groups"][group]
            # print(the_item)
            if the_item:
                for device in the_item:
                    if "a51" in device:
                        self.device_dict["a51"] = self.device_dict.get("a51", 0) + 1
                    if "pixel5" in device:
                        self.device_dict["p5"] = self.device_dict.get("p5", 0) + 1
                    if "pixel6" in device:
                        self.device_dict["p6"] = self.device_dict.get("p6", 0) + 1
                    if "s7" in device:
                        self.device_dict["s7"] = self.device_dict.get("s7", 0) + 1
                    if "pixel2" in device:
                        self.device_dict["p2"] = self.device_dict.get("p2", 0) + 1
                    if "motog5" in device:
                        self.device_dict["g5"] = self.device_dict.get("g5", 0) + 1

    def main(self):
        self.get_report_dict()

        v1_enabled = False
        if v1_enabled:

            print("/// tc-w  workers ///")
            for key in sorted(self.tcw_result_dict.keys()):
                print("%s: %s" % (key, self.tcw_result_dict[key]))
            print("/// g-w workers ///")
            for key in sorted(self.gw_result_dict.keys()):
                print("%s: %s" % (key, self.gw_result_dict[key]))
            print("/// test workers ///")
            for key in sorted(self.test_result_dict.keys()):
                print("%s: %s" % (key, self.test_result_dict[key]))
            print("/// device summary ///")
            total_count = 0
            for item in self.device_dict:
                total_count += int(self.device_dict[item])
                print("%s: %s" % (item, self.device_dict[item]))
            print("total: %s" % total_count)

            print("")
            print("v2:")

        result = self.get_report_dict_v2()
        import pprint

        print("/// pool summary ///")
        pprint.pprint(result["pool_counts"])

        print("/// device summary ///")
        pprint.pprint(result["device_counts"])

        print("total devices: %s" % result["total_devices"])
