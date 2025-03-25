# LT Notes

## TODO

- user_script/setup_script.sh
  - don't hack up scripts, grab them from a repo
- rename to mozilla-tc-devicepool or
            mozilla-taskcluster-devicepool

## execution loop modes

1. starts a single job, foreground, targets device_type-os_version
  - replica of jmaher's PoC
2. starts multiple jobs, --no-track, foreground, targets device_type-os_version
  - works, current default
  - known issues
    - if 60 jobs come in, will take awhile to have 100% utilization (takes awhile to start jobs)
    - overshoot at the end (not a huge deal... will time out? hmm, tc timeout... or hyperexecute yaml timeout?)
      - not considering lt running (only looking at lt initialized)
3. starts a single job with hyperexecute yaml concurrency, --no-track, foreground, targets device_type-os_version
  - didn't work, needs more investigation

### proposed modes

1. starts multiple jobs, --no-track, background, targets device_type-os_version
  - improve slow start problem
2. starts multiple jobs, --no-track, background, targets single device (device_type-os_version and udid)
  - need to track specific free devices in app
  - enables creation of multiple device pools per device type
