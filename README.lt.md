# LT Notes

## TODO

- user_script/setup_script.sh
  - don't hack up scripts, grab them from a repo
- rename to mozilla-tc-devicepool or
            mozilla-taskcluster-devicepool

## execution loop modes

1. starts a single job, foreground, targets device type
  - replica of jmaher's PoC
2. starts multiple jobs, --no-track, foreground, targets device type
  - works, current default
  - known issues
    - if 60 jobs come in, will take awhile to have 100% utilization (takes awhile to start jobs)
3. starts a single job with hyperexecute yaml concurrency, --no-track, foreground, targets device type
  - didn't work, needs more investigation
4. proposed modes
  - starts multiple jobs, --no-track, background, targets device type
    - improve slow start problem
  - starts multiple jobs, --no-track, background, targets single device (track specific free devices)
    - enables creation of multiple device pools per device type
