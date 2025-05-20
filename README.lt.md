# LT Notes

## TODO

- user_script/setup_script.sh
  - don't hack up scripts, grab them from a repo
- rename to mozilla-tc-devicepool or
            mozilla-taskcluster-devicepool

## getting the hyperexecute binary

See https://www.lambdatest.com/support/docs/hyperexecute-cli-run-tests-on-hyperexecute-grid/.

## testing

```bash
# activate venv
. ./.venv/bin/activate

# pytest-watch with coverage and double verbose
pytest-watch -- -vv --cov
```

## installation / deployment

```
sudo cp service/lambdatest.service /etc/systemd/system/lambdatest.service
sudo systemctl daemon-reload
```

## execution loop overview

```bash
# overview:
#   1. do configuration / load config data
#   2. in loop:
#     a. update tc queue counts
#     b. update lt job status (how many running per group)
#     c. update lt device status (how many devices in each state per group)
#     d. calculate number of jobs to start
#     e. start jobs for the appropriate tc queue with selected devices
```

## execution loop modes

1. starts a single job, foreground, targets device_type-os_version
  - replica of jmaher's PoC
2. starts multiple jobs, --no-track, foreground, targets device_type-os_version
  - works, current default
  - known issues
    - slwo start problem: if 60 jobs come in, will take awhile to have 100% utilization (takes awhile to start jobs)
3. starts a single job with hyperexecute yaml concurrency, --no-track, foreground, targets device_type-os_version
  - didn't work (theoretically should, check with LT about my understanding of field), needs more investigation.

### proposed modes

1. starts multiple jobs, --no-track, background, targets device_type-os_version
  - improve slow start problem
  - decision: implement
2. starts multiple jobs, --no-track, background, targets single device (device_type-os_version and udid)
  - need to track specific free devices in app
  - enables creation of multiple device pools per device type
  - discussed with jmaher... wait on this
    - don't expect need for device_type partitions at LT yet
