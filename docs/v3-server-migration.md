# Bitbar v3-server migration

**Deadline: 2026-05-18**

## Status

- [x] Phase 0 — v3 systemd service deployed and running
- [x] Phase 1 — a55-perf — **done** (migrated 2026-05-06)
- [ ] Phase 2 — pixel6-perf — **on hold** (most devices not rooted; see work log 2026-05-11)
- [x] Phase 3 — s24-perf — **done** (migrated 2026-05-11; s24-07 not rooted, see Phase 4)
- [ ] Phase 4 — device count reconciliation (pixel6: 10, s24: 4, a55: 6)
- [x] Phase 4 — root s24-07 (resolved 2026-05-12; Magisk adb shell authorization was never granted)

## Known issues / blockers

| Phase | Status | Issue |
|-------|--------|-------|
| 2 | **Resolved 2026-05-05** | New pixel6 devices missing from vendor's `DOCKER_POWER_METER_MAP`, `DOCKER_DEVICE_SERIAL_IP_MAP`, and `DOCKER_DEVICE_SERIAL_NAME_MAP` Jenkins config. Serial `1A011FDF600AMA` (pixel6-137) confirmed missing; likely all new pixel6 devices affected. |
| 2 | **Resolved 2026-05-06** | v3 pixel6 devices not rooted — `su` binary absent (`su: inaccessible or not found`). Confirmed via task logs 2026-05-05; distinguishable from the benign `setenforce` permission denied which appears on both clusters. |
| 2 | **Blocking** | v3 pixel6 devices have two issues: (1) Magisk root authorization not finalized — same exitcode 13 pattern as s24-07 (see 2026-05-12 work log); `_have_su: False` on these devices suggests su detection also failing, possibly OS-version-related. (2) Mixed Android OS versions: pixel6-137 (Android 13, working), pixel6-166 (12), pixel6-147 (15), pixel6-138/158/165/169/170/173 (16), pixel6-181 (non-functional). Vendor must finalize Magisk authorization on all devices and ideally standardize OS version to Android 13. |

## Background

The legacy Bitbar server (`https://mozilla.bitbar.com`) is being replaced by
a new server at the new datacenter (`https://mozilla-v3.bitbar.com`).

The v3 server already has its own physical device fleet, registered and online
today under *test pool* labels in `config/config-v3-server.yml`. Migration
moves production work pool-by-pool by:

1. Promoting v3 devices from their current test groups into production groups
   in `config/config-v3-server.yml`.
2. Retiring the matching pool from the legacy `config/config.yml` so the
   legacy fleet stops receiving that workload.

During migration both devicepool services run in parallel — one per server —
and each pool lives in exactly one config at any given time.

Test pools (`test-1/2/3`, `test-p5/p6/s24`, `test-999`) carry no production
workload and are out of scope except as the source of devices for v3 production
groups.

## Key files

| File | Role |
|------|------|
| `config/config.yml` | Legacy server config (active) |
| `config/config-v3-server.yml` | v3 server config (test pools only at start) |
| `bitbar_env.sh` | Sets `TESTDROID_URL=https://mozilla.bitbar.com` for legacy service |
| `bitbar_env-v3-server.sh` | Sets `TESTDROID_URL=https://mozilla-v3.bitbar.com` for v3 service |
| `service/bitbar.service` | systemd unit for legacy service (`RuntimeMaxSec=1h`, `Restart=always`) |
| `bin/start_android_hardware_testing.sh` | Legacy entrypoint (uses `config/config.yml`) |
| `bin/start_mbd_new_server.sh` | v3 manual launch wrapper; basis for v3 systemd unit |
| `bin/v3_config_mover.sh` | Moves devices between pools on the v3 server via `configuration_device_tool` |

## Pool migration order

Ordered by v3 device availability — pools with enough devices on the new server
go first; pools that need the vendor to bring more devices online go later.
Vendor is actively working to bring remaining devices online.

Note: `pixel5-unit` is not being migrated — those tasks are moving to `pixel6-perf`.

| Phase | Legacy project / device_group | v3 target | v3 online now | Vendor needed? |
|-------|-------------------------------|-----------|---------------|----------------|
| 1 | `mozilla-gw-perftest-a55` / `a55-perf` | 6 | 35 (29 disabled by Bitbar) | No |
| 2 | `mozilla-gw-perftest-p6` / `pixel6-perf` | 10 | 11 | No — at target |
| 3 | `mozilla-gw-perftest-s24` / `s24-perf` | 4 | 4 | No — at target |

Unit pools (`s24-unit`, `pixel6-unit`, `a55-unit`) are empty in legacy config.
Handle them in the matching perf phase: uncomment and populate on v3 if needed,
otherwise leave commented.

---

## Phase 0 — Prerequisites (one-time setup)

Complete before moving any production pool.

1. **Stand up the v3 systemd service** alongside the existing legacy unit.
   - Create `service/bitbar-v3.service` modeled on `service/bitbar.service`.
   - `ExecStart` should invoke `bin/start_mbd_new_server.sh` (which already
     sources `bitbar_env-v3-server.sh` and passes `-b config/config-v3-server.yml`).
   - Use a distinct `SyslogIdentifier` / log target so both services are
     independently observable.
   - Enable and start the unit. Confirm it manages the existing v3 test pools
     (jobs flow, devices reach ready state) before touching production.

2. **Snapshot state for rollback.**
   ```
   git tag pre-v3-migration
   cp config/config.yml config/config.yml.pre-migration.bak
   cp config/config-v3-server.yml config/config-v3-server.yml.pre-migration.bak
   ```

3. **Verification gate.** Both services are running without errors.
   - Legacy service owns all production pools.
   - v3 service runs cleanly against test pools only.
   - `journalctl -u bitbar.service` and `journalctl -u bitbar-v3.service` are
     both clean.

---

## Phases 1–4 — Per-pool migration

Repeat these steps for each pool in the order above.

### Step 1 — Pre-flight

- Confirm the legacy pool P has no stuck or in-flight jobs.
- Confirm the v3 source test group has enough ready devices to cover P's
  required device count. Top up from the wider v3 fleet if short.

### Step 2 — Edit `config/config-v3-server.yml`

- Uncomment or add the production project block for P under `projects:`.
  - **Do not copy legacy `additional_parameters` verbatim.** Inherit v3
    defaults: `bitbar_cloud_url: https://mozilla-v3.bitbar.com`,
    `application_file: v3-testdroid-sample-app.apk`,
    `test_file: v3-empty-test.zip`.
- Add a `device_groups:` entry for P populated with the device labels
  currently in the corresponding `test-*` group.
- Remove those labels from the `test-*` group in the same edit (a device
  should be in exactly one group at a time).

### Step 3 — Edit `config/config.yml`

- Comment out the matching project block for P with a note:
  `# disabled: migrated to v3 server`

### Step 4 — Commit

```
git add config/config.yml config/config-v3-server.yml
git commit -m "migrate <pool> from legacy bitbar to v3 server"
```

### Step 5 — Deploy and restart both services

Pull the updated configs on the host, then restart both services:

```
systemctl restart bitbar.service
systemctl restart bitbar-v3.service
```

### Step 6 — Verify and soak

- `journalctl -u bitbar-v3.service` — production project P picked up, no errors.
- Bitbar v3 UI — project P present, devices online.
- Taskcluster — a real job lands on a v3-managed worker for P and completes
  successfully.
- Legacy fleet for P is idle (expected; those devices are decommissioned
  separately, out of scope here).

**Soak period:** hold 24 hours after migrating Phase 1 (`s24-perf`) before
proceeding to Phase 2. Once the pattern is proven, later phases can move faster.

---

## Rollback

### Rollback commits

| Phase | Pool | Commit |
|-------|------|--------|
| pre-migration | — | `f26e673` |
| 1 | a55-perf | `6987040` |
| 2 | pixel6-perf | TBD (on hold) |
| 3 | s24-perf | `b082b7b` |

### Per-pool rollback (during or shortly after a phase)

1. `git revert` the migration commit for pool P from the table above (restores both YAML files).
2. Deploy the reverted configs to the host manually.
3. Restart both services:
   ```
   systemctl restart bitbar.service
   systemctl restart bitbar-v3.service
   ```
4. Confirm legacy P resumes and v3 devices return to the `test-*` group.

### Full rollback (abort migration entirely)

1. Restore both configs from the tag:
   ```
   git checkout pre-v3-migration -- config/config.yml config/config-v3-server.yml
   ```
2. Deploy the reverted configs to the host manually.
3. Restart both services.
4. Optionally disable the v3 unit to return to single-service operation:
   ```
   systemctl disable --now bitbar-v3.service
   ```

The `RuntimeMaxSec=1h` auto-restart means worst-case config staleness without a
manual restart is 1 hour.

---

## Risk notes

- **v3 config defaults differ from legacy.** Key differences in
  `config-v3-server.yml`: `bitbar_cloud_url` points to `mozilla-v3.bitbar.com`;
  `application_file` and `test_file` use v3 filenames. Always inherit v3
  defaults when adding production projects; do not paste from `config.yml`.
- **`jobs_to_start_algorithm: v3`** is set in `devicepool_config` of the v3
  config. If job scheduling behavior differs materially from the legacy
  algorithm, pause and investigate after Phase 1 before continuing.
- **`test-999`** (`a55-46`, labeled SLOW) must never be promoted into a
  production device group.
- **Parallel API key usage.** Both `bitbar_env.sh` and `bitbar_env-v3-server.sh`
  need valid `TESTDROID_APIKEY` values for their respective servers. Confirm
  both are active before Phase 0.

---

## Final cutover (after all pools migrated)

Once `a55-perf` (Phase 3) is stable on v3:

- `config/config.yml` should have no active production projects.
- Stop and disable the legacy systemd unit:
  ```
  systemctl disable --now bitbar.service
  ```
- Open a follow-up ticket to decommission the legacy device fleet and remove
  the legacy config/env files from the repo.

---

## Phase 4 — Device count reconciliation

Verify final device counts on v3 match the agreed targets:

| Pool | Target | Online (2026-05-06) | Notes |
|------|--------|---------------------|-------|
| `pixel6-perf` | 10 | 11 | At target; 1 spare |
| `s24-perf` | 4 | 4 | At target |
| `a55-perf` | 6 | 35 registered, 29 disabled by Bitbar = 6 active | At target; follow up with Bitbar on disabled devices |

Run `dgrv3` and `v3_compare_to_api` to check current state. For any pool short
of its target, file a vendor request and track until resolved. Update
`config/config-v3-server.yml` to add newly online devices to the appropriate
production group as they come online.

---

## Work log

### 2026-05-05
- Attempted p6-perf migration (try 2, commit `70e31127`); reverted (`c0df0a6`) — v3 p6 devices not rooted (`su` binary absent). Vendor rooting; expected done 2026-05-06.
- s24s being overnighted to FL datacenter; 3 devices needed to reach target of 4.
- Started a55 try push against test-1 pool on v3: https://treeherder.mozilla.org/jobs?repo=try&landoInstance=lando-prod-2025&landoCommitID=43062

### 2026-05-06
- a55 try push results (revision `5d01ab1da31bc556385ed93300a441908c8d194f`): 174 total jobs — 153 green, 11 testfailed (all `sp3`, all autoclassified intermittent), 6 retry, 4 exception. Try push considered clean; proceeding with a55 production migration.
- Vendor confirmed p6 devices on v3 are now rooted.
- s24 devices arrived at FL datacenter and are online.
- Sparky landing https://phabricator.services.mozilla.com/D298883 to remove all P5 references and redirect pixel5 load to A55s (already running there in LT). No migration action needed.
- Renumbered phases: a55-perf is now Phase 1 (migrated first due to highest confidence in those workers), pixel6-perf Phase 2, s24-perf Phase 3.

### 2026-05-11
- pixel6-perf migration completed successfully (commit `98f28fe`). Jobs confirmed flowing on v3.
- Verification: retriggered ~10 sp3 jobs from mozilla-central push `5d85334c95eda979785d121004aa4a8ee310deb4` (previously run on old workers). Monitoring worker uptake at https://firefox-ci-tc.services.mozilla.com/provisioners/proj-autophone/worker-types/gecko-t-bitbar-gw-perf-p6?sortBy=Last%20Active&sortDirection=desc.
- Migration reverted — most v3 pixel6 devices not rooted. Only pixel6-137 confirmed rooted (Android 13). All others unrooted: pixel6-165 (Android 16), pixel6-169 (Android 16), pixel6-166 (Android 12), pixel6-170 (Android 16), pixel6-173 (Android 16), pixel6-138 (Android 16), pixel6-147 (Android 15), pixel6-158 (Android 16). pixel6-181 non-functional. Vendor needs to root all devices — issue appears to be Android version, not just missing su binary.
- s24-perf migration completed (commit `b082b7b`). s24-01, s24-02, s24-03 (shipped from old DC) working well. s24-07 (vendor-provisioned) not rooted — flagged as Phase 4 follow-up.

### 2026-05-12
- s24-07 rooting resolved. Bitbar had unlocked the bootloader and flashed a rooted image (Magisk) but never granted the initial adb shell su authorization. Magisk requires an interactive grant on first `su` request — the popup must be accepted on-device to store the policy for `com.android.shell`. Without this step, subsequent `su -c` calls fail with exitcode 13 (Permission denied). Bitbar completed the authorization flow; s24-07 now working.

  **Diagnostic: working device (s24-02)**
  ```
  adb Setting SELinux Permissive
  '_have_su': True
  ```

  **Diagnostic: broken device (s24-07, before fix)**
  ```
  su -c setenforce 0 exitcode 13, stdout: None
  Unable to set SELinux Permissive due to args: adb wait-for-device shell setenforce Permissive, exitcode: 1, stdout: setenforce: Couldn't set enforcing status to 'Permissive': Permission denied.
  ```
  The `exitcode 13` on `su -c` specifically indicates Magisk denied the request (vs `exitcode: 127` / `su: inaccessible or not found` which means `su` is absent entirely).

### 2026-05-13
- Diagnostic jobs confirmed all 9 tested v3 pixel6 devices are now rooted (vendor completed work), across mixed Android versions (12, 15, 16). pixel6-137 (Android 13) already known good.
- Updated migration plan with vendor: they are shipping pixel6-01 and pixel6-04 from old DC to new DC, and flashing "several" more p6s to Android 13 and rooting them. Communicated to vendor that we only need 4 pixel6s on Android 13 (rooted, with OS auto-upgrades disabled) to proceed with migration — don't need all 10 perfect before starting.
- Vendor downgraded and rooted pixel6-138, pixel6-165, pixel6-173 to Android 13 (pixel6-137 was already on Android 13 and working). Moved all 4 into pixel6-perf in v3 config; remaining 6 left in test-1.
- Verified via diagnostic jobs: all 4 pixel6-perf devices confirmed Android 13 + rooted. test-1 devices also all rooted (mixed OS): pixel6-147 (15), pixel6-158 (16), pixel6-169 (16), pixel6-170 (16), pixel6-181 (12). pixel6-166 not working well — stuck/not completing diagnostic job; left in test-1, not blocking migration.
