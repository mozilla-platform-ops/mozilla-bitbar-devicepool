#!/usr/bin/env python3

import sys

import termplotlib as tpl

from mozilla_bitbar_devicepool.bitbar.admin_devices import get_device_statuses


class DockerServerReport:
    def do_report(self):
        try:
            results = get_device_statuses()
        except AttributeError as e:
            print(f"  exception: {e}")
            print("Please source bitbar_env.sh (or your equivalent)!")
            sys.exit(1)
        # print(results)

        device_to_docker_host_dict = {}

        for result_device in results:
            # print(result_device)
            # print("-")

            device_to_docker_host_dict[result_device["deviceName"]] = result_device[
                "clusterName"
            ]

        # import pprint
        # pprint.pprint(device_to_docker_host_dict)

        histogram_dict = {}
        # print("")

        for k, v in device_to_docker_host_dict.items():
            # print(f"{k}: {v}")
            shortened_v = v.replace(".mv.mozilla.hc.bitbar", "")
            try:
                histogram_dict[shortened_v] += 1
            except KeyError:
                histogram_dict[shortened_v] = 1
        # print(histogram_dict)

        # sys.exit()

        # my_dict = {1: 27, 34: 1, 3: 72, 4: 62, 5: 33, 6: 36, 7: 20, 8: 12, 9: 9, 10: 6, 11: 5, 12: 8, 2: 74, 14: 4,
        #            15: 3, 16: 1, 17: 1, 18: 1, 19: 1, 21: 1, 27: 2}
        #
        # my_dict = {"apple": 5, "banana": 3, "orange": 2}
        my_dict = histogram_dict

        sorted_dict = dict(sorted(my_dict.items()))
        # print(sorted_dict)

        data = sorted_dict

        counts = list(data.values())
        labels = list(data.keys())

        fig = tpl.figure()
        fig.barh(counts, labels, force_ascii=True)
        fig.show()

    def main(self):
        self.do_report()
