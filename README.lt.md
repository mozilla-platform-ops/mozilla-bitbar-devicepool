# mld: mozilla-lambdatest-devicepool

Detects pending Taskcluster jobs and starts tasks at Lambdatest to handle them.

Lambdatest job launching is done via their Hyperexecute CLI tool (that handles the API requests).

## Configuration

Configuring `mld` requires creating environment variables and a yaml configuration file for Bitbar. See `config/lambdatest.yml`.

## Usage

```bash
mld --help

# run locally in debug mode (no LT API jobs started)
mld --debug
```

## Deployment

### getting the hyperexecute binary

See https://www.lambdatest.com/support/docs/hyperexecute-cli-run-tests-on-hyperexecute-grid/.


### Systemd Unit Installation

```
sudo cp service/lambdatest.service /etc/systemd/system/lambdatest.service
sudo systemctl daemon-reload
```

## Job Tracing

Linking Taskcluster jobs to Lambdatest jobs bidrectionally.

### LT->TC

Go to the 'Post Steps' tab of the selected job in the LambdaTest Hyperexecute UI (https://hyperexecute.lambdatest.com/hyperexecute/jobs). Reveal the 'Post' step's output. You should see text similar to:

```
generic-worker-metadata.json contents:
{
  "lastTaskUrl": "https://firefox-ci-tc.services.mozilla.com/tasks/Ym_uHmb0TmC_f45Wv8uw3w/runs/0"
}
```

### TC->LT

Search for `lambdatest` in the Taskcluster job's log. You should find content similar to:

```
[task 2025-06-02T22:27:14.576Z] LambdaTest Job Number: 21724
[task 2025-06-02T22:27:14.576Z] LambdaTest Job URL: https://hyperexecute.lambdatest.com/hyperexecute/task?jobId=0e05dbf5-7cec-44a2-a63c-1d8c01525009&link=&logType=&order=&scenario_search_text=&taskId=HYPL-1611945-1748903159145866048AYB&taskStatus=
```

## Development Notes

### Differences between MBD and MLD

#### Device Pools: Server-side vs Client-side

MBD submits Bitbar tasks to several projects. The projects represent our Taskcluster worker pools.

In MLD, no such ability to group devices exists. Only MLD knows about these groups, not LT.

### Execution Loop Overview

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

### Execution Loop Implementation Details

1. starts a single job, foreground, targets device_type-os_version
  - replica of jmaher's PoC
2. starts multiple jobs, --no-track, foreground, targets device_type-os_version
  - works, current default
  - known issues
    - slwo start problem: if 60 jobs come in, will take awhile to have 100% utilization (takes awhile to start jobs)
3. starts a single job with hyperexecute yaml concurrency, --no-track, foreground, targets device_type-os_version
  - didn't work (theoretically should, check with LT about my understanding of field), needs more investigation.
4. (CURRENTLY IMPLEMENTED) starts multiple jobs, --no-track, background, targets single device (device_type-os_version and udid)
  - need to track specific free devices in app
  - enables creation of multiple device pools per device type
  - discussed with jmaher... wait on this
    - don't expect need for device_type partitions at LT yet
