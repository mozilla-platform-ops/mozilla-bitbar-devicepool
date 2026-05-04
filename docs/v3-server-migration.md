# Bitbar v3-server migration

**Deadline: 2026-05-18**

## Status

- [x] Phase 0 — v3 systemd service deployed and running
- [ ] Phase 1 — pixel6-perf — **can proceed** (10 on v3 vs 4 on legacy; at target)
- [ ] Phase 2 — s24-perf — **blocked** (1 on v3 vs 4 on legacy; need 3 more s24 from vendor before migrating)
- [ ] Phase 3 — a55-perf — **can proceed** once earlier phases done; trim test-1 from 43 to 6 devices before enabling production pool
- [ ] Phase 4 — device count reconciliation (pixel6: 10, s24: 4, a55: 6)

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
| 1 | `mozilla-gw-perftest-p6` / `pixel6-perf` | 10 | 10 | No — at target |
| 2 | `mozilla-gw-perftest-s24` / `s24-perf` | 4 | 1 | Yes — 3 more s24 |
| 3 | `mozilla-gw-perftest-a55` / `a55-perf` | 6 | 43 (trimming to 6) | No |

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
| pre-migration | — | `67ae46a` |
| 1 | pixel6-perf | TBD |
| 2 | s24-perf | TBD |
| 3 | a55-perf | TBD |

### Per-pool rollback (during or shortly after a phase)

1. `git revert` the migration commit for pool P from the table above (restores both YAML files).
2. Deploy the reverted configs to the host manually.
3. Restart both services:
   ```
   systemctl restart bitbar-v3.service
   systemctl restart bitbar.service
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

| Pool | Target | Action if short |
|------|--------|-----------------|
| `pixel6-perf` | 10 | Follow up with vendor to bring remaining pixel6 devices online |
| `s24-perf` | 4 | Follow up with vendor to bring remaining s24 devices online |
| `a55-perf` | 6 | Follow up with vendor to bring remaining a55 devices online |

Run `dgrv3` and `v3_compare_to_api` to check current state. For any pool short
of its target, file a vendor request and track until resolved. Update
`config/config-v3-server.yml` to add newly online devices to the appropriate
production group as they come online.
