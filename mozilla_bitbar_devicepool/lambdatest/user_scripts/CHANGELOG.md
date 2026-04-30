# user_scripts changelog

| Version | Directory | Status | Notes |
|---------|-----------|--------|-------|
| v1 | `v1/` | Deployed | Initial version. |
| v2 | `v2-py312_and_hg702/` | Deployed | Python 3.12 and Mercurial 7.0.2 support. |
| v3 | `v3-disable-adb-killserver/` | Deployed | Disable adb kill-server. |
| v4 | `v4-python_fix/` | Deployed | Python fix. |
| v5 | `v5-python_runtime/` | Deployed | Python runtime update. |
| v6 | `v6-setup_sets_portrait/` | Not deployed | Superseded; perf team delivered a fix in-tree. |
| v7 | `v7-cdc_acm_detach_for_power_meters/` | Not deployed | Does not fully solve the problem — tests still fail because the race condition occurs during the tests, not just at setup. |
