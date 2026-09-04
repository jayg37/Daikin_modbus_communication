# Home Assistant configuration

This directory contains the Home Assistant YAML used by the project.

## Baseline automation

`sync_upstairs_mini_split_setpoint.yaml` is the intentionally minimal test automation.

It triggers only on a change to the Honeywell thermostat's exposed `temperature` target and sends the Daikin a target of Honeywell +2°F, clamped to a 70°F minimum.

HVAC mode is intentionally untouched during this test phase.
