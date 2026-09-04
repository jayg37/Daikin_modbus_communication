# Daikin Modbus Communication

Home Assistant project for integrating and automating a Daikin mini-split system using the Daikin/Airzone Aidoo MQTT interface, with the downstairs Honeywell T6 Pro thermostat serving as the temperature reference.

## Project status

**Current phase: setpoint synchronization only — testing baseline**

The current automation intentionally does one thing:

> When the downstairs Honeywell thermostat target temperature changes, set the upstairs Daikin mini-split target to the Honeywell target +2°F, with a 70°F minimum.

No HVAC mode control or temperature-trend logic is currently enabled. This is deliberate so the setpoint synchronization can be observed for several days before adding mode logic.

## Home Assistant entities

- Downstairs Honeywell: `climate.tstat_24d76e_t6_pro_thermostat`
- Upstairs Daikin: `climate.daikin_mini_split`

Saved Home Assistant state data shows the Daikin entity is MQTT-based and associated with a Daikin/Airzone Aidoo device. The entity supports `off`, `auto`, `cool`, `heat`, `fan_only`, and `dry`, with a single `temperature` target exposed in the captured state data.

## Current automation

File: `ha/sync_upstairs_mini_split_setpoint.yaml`

Behavior:

1. Trigger only when the Honeywell `temperature` attribute changes.
2. Read the Honeywell target temperature.
3. Calculate the Daikin target as Honeywell +2°F.
4. Clamp the result to a minimum of 70°F.
5. Send only `climate.set_temperature` to the Daikin.

The automation does **not**:

- change Daikin HVAC mode
- monitor Honeywell HVAC mode
- monitor room-temperature changes
- infer heating versus cooling
- use temperature trend logic
- intentionally send repeated HVAC-mode commands

## Why the project is being developed incrementally

Earlier iterations attempted to synchronize HVAC mode and infer heat/cool behavior from the Honeywell thermostat. Those versions produced undesirable behavior, including the Daikin being turned off or becoming inconsistent when its climate entity reported an idle operating state.

The project was therefore simplified to establish a clean, observable baseline. After the setpoint-only behavior is confirmed, the next phase will add low-level mode checking carefully and only when required.

## Observed Daikin entity details

From saved Home Assistant state data:

- Entity: `climate.daikin_mini_split`
- Platform: MQTT
- Device: Daikin/Airzone Aidoo
- Supported HVAC modes: `off`, `auto`, `cool`, `heat`, `fan_only`, `dry`
- Minimum target temperature reported: 60°F
- Maximum target temperature reported: 86°F
- Target temperature step: 1°F
- Fan modes: `auto`, `1`, `2`, `3`

## Future work

The planned next stage is to add controlled HVAC-mode synchronization without unnecessary commands. For Honeywell `cool` and `heat`, the desired mode can eventually be mapped directly. Honeywell `auto` will require separate logic because the current Home Assistant representation exposes only the active target temperature rather than both heating and cooling setpoints. Any future mode logic should be introduced only after the setpoint-only baseline has been validated.

## Safety / deployment notes

This project contains Home Assistant automation intended for a specific installation. Review entity IDs and behavior before deploying to another system. HVAC behavior should be validated in the actual installation before relying on automation for unattended operation.
