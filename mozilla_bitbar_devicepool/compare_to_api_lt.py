# compares the config to the lt api output

import os
import pprint

from mozilla_bitbar_devicepool import configuration_lt
from mozilla_bitbar_devicepool.lambdatest import status


# main
if __name__ == "__main__":
    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_ACCESS_KEY"]

    status = status.Status(lt_username, lt_api_key)

    # get the config
    clt = configuration_lt.ConfigurationLt()
    clt.configure()
    config = clt.get_config()
    # pprint.pprint(config)

    config_array_of_udids = []
    for project, udid_arr in config["device_groups"].items():
        for udid in udid_arr:
            config_array_of_udids.append(udid)

    # pprint.pprint(config_array_of_udids)
    # pprint.pprint(len(config_array_of_udids))
    # sys.exit(0)

    # get the api output
    api_output = status.get_device_list()
    api_array_of_udids = []
    for _k, v in api_output.items():
        # pprint.pprint(_k)
        # pprint.pprint(v)
        for udid, _state in v.items():
            # pprint.pprint(udid)
            # pprint.pprint(_state)
            api_array_of_udids.append(udid)
        # api_array_of_udids.append(v["udid"])  # Assuming v contains a dictionary with "udid" key

    # TODO: show this if --verbose is set
    # pprint.pprint(api_array_of_udids)
    # sys.exit(0)

    # compare the two
    # if api_array_of_udids != config_array_of_udids:
    # print("Configuration does not match API output")
    # print("Config: ", config_array_of_udids)
    # print("API Output: ", api_array_of_udids)
    # show the differences both ways
    diff1 = set(api_array_of_udids) - set(config_array_of_udids)
    diff2 = set(config_array_of_udids) - set(api_array_of_udids)
    print("Differences (api - config): ", pprint.pformat(diff1))
    print("Differences (config - api): ", pprint.pformat(diff2))
    if not diff1 and not diff2:
        print("SUCCESS: Configuration matches API output.")
    else:
        print("WARNING: Configuration does not match API output.")
