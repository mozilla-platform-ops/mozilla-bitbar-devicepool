#!/usr/bin/env python3

import sys
import pprint

import termplotlib as tpl

from mozilla_bitbar_devicepool.bitbar.admin_devices import get_device_statuses


class DockerServerReport:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def do_report(self):
        try:
            results = get_device_statuses()
        except AttributeError as e:
            print(f"  exception: {e}")
            print("Please source bitbar_env.sh (or your equivalent)!")
            sys.exit(1)

        device_to_docker_host_dict = {}
        for result_device in results:
            device_to_docker_host_dict[result_device["deviceName"]] = result_device["clusterName"]
        if self.verbose:
            pprint.pprint(device_to_docker_host_dict)
            print("")

        histogram_dict = {}
        for k, v in device_to_docker_host_dict.items():
            shortened_v = v.replace(".mv.mozilla.hc.bitbar", "")
            try:
                histogram_dict[shortened_v] += 1
            except KeyError:
                histogram_dict[shortened_v] = 1

        sorted_dict = dict(sorted(histogram_dict.items()))

        counts = list(sorted_dict.values())
        labels = list(sorted_dict.keys())

        fig = tpl.figure()
        fig.barh(counts, labels, force_ascii=True)
        fig.show()

    def main(self):
        self.do_report()
