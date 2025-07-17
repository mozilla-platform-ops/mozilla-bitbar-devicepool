# Devices in Multiple Projects: Feature Summary

## Overview
This feature allows a single device to be assigned to more than one project/device group. When a device is eligible for multiple projects, a priority mechanism determines which project gets to use the device first.

## Key Details
- Each project can specify a `priority_group` (device type) and a `priority` value in the config.
- Higher `priority` values mean higher priority for device assignment.
- When multiple projects claim the same device, the project with the highest priority (largest number) gets first access.
- If the higher-priority project has no pending jobs, the device can be used by a lower-priority project.

## To Do
- Update device selection logic to respect project priorities.
- Ensure the config (`lambdatest.yml`) includes `priority_group` and `priority` for each project.
- Document any changes to the job starter or device allocation logic.

---

_Use this file to track design decisions, implementation notes, and any open questions about device sharing and prioritization across projects._
