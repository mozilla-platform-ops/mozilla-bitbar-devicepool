# compares the config to the lt api output

import os
import pprint

from mozilla_bitbar_devicepool import configuration_lt
from mozilla_bitbar_devicepool.lambdatest import status


def main():
    lt_username = os.environ["LT_USERNAME"]
    lt_api_key = os.environ["LT_ACCESS_KEY"]

    status_client = status.Status(lt_username, lt_api_key)

    # get the config
    clt = configuration_lt.ConfigurationLt()
    clt.configure()
    config = clt.get_config()
    # pprint.pprint(config)

    config_array_of_udids = []
    for project, udid_arr in config["device_groups"].items():
        if udid_arr is not None:
            for udid in udid_arr:
                config_array_of_udids.append(udid)

    # pprint.pprint(config_array_of_udids)
    # pprint.pprint(len(config_array_of_udids))
    # sys.exit(0)

    # get the api output
    api_output = status_client.get_device_list()
    api_array_of_udids = []
    for _k, v in api_output.items():
        # pprint.pprint(_k)
        # pprint.pprint(v)
        for udid, _state in v.items():
            # pprint.pprint(udid)
            # pprint.pprint(_state)
            api_array_of_udids.append(udid)
        # api_array_of_udids.append(v["udid"])  # Assuming v contains a dictionary with "udid" key

    # Find any duplicates in the arrays before sorting
    api_duplicates = [item for item in api_array_of_udids if api_array_of_udids.count(item) > 1]
    config_duplicates = [item for item in config_array_of_udids if config_array_of_udids.count(item) > 1]

    # display the sets, sorted
    config_array_of_udids.sort()
    api_array_of_udids.sort()

    print("Config: ", pprint.pformat(config_array_of_udids))
    print("API Output: ", pprint.pformat(api_array_of_udids))
    print("")

    # Print any duplicates found
    if api_duplicates:
        print("WARNING: Duplicates in API array: ", pprint.pformat(sorted(set(api_duplicates))))
    if config_duplicates:
        print("WARNING: Duplicates in Config array: ", pprint.pformat(sorted(set(config_duplicates))))
    if api_duplicates or config_duplicates:
        print("")

    # show the differences both ways (after removing duplicates)
    api_set = set(api_array_of_udids)
    config_set = set(config_array_of_udids)

    print("Count of api_array_of_udids (with duplicates): ", len(api_array_of_udids))
    print("Count of config_array_of_udids (with duplicates): ", len(config_array_of_udids))
    print("Count of unique api items: ", len(api_set))
    print("Count of unique config items: ", len(config_set))

    diff1 = list(api_set - config_set)
    diff2 = list(config_set - api_set)

    print("Count of differences (api - config): ", len(diff1))
    print("Count of differences (config - api): ", len(diff2))

    print("")

    print("Differences (api - config): ", pprint.pformat(sorted(diff1)))
    print("Differences (config - api): ", pprint.pformat(sorted(diff2)))
    if not diff1 and not diff2:
        print("SUCCESS: Configuration matches API output.")
    else:
        print("WARNING: Configuration does not match API output.")


# main
if __name__ == "__main__":
    main()
