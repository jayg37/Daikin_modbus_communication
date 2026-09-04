# Daikin Modbus Communication

Local Modbus RTU integration for a Daikin mini-split through an Airzone DKN/Aidoo interface, using a Raspberry Pi and USB RS485 adapter, with Home Assistant integration over MQTT.

## Project overview

This project documents a working local-control architecture:

```text
Daikin Mini Split
       │
       │ Daikin proprietary interface
       ▼
Airzone DKN / Aidoo
       │
       │ RS-485 / Modbus RTU
       ▼
FTDI USB → RS485 Adapter
       │
       │ USB
       ▼
Raspberry Pi Zero 2 W
       │
       │ MQTT
       ▼
Home Assistant
```

The Raspberry Pi acts as the **Modbus master**. The Airzone device is the **Modbus slave**, using slave address 1 in this installation. The Pi polls the Airzone registers and publishes the resulting HVAC state to MQTT. Home Assistant can send commands back over MQTT; the Pi translates those commands into Modbus writes.

The implementation is local and does not depend on a vendor cloud API for HVAC control.

## Hardware

### Raspberry Pi

- Raspberry Pi Zero 2 W
- Raspberry Pi OS
- Python 3 virtual environment

### RS-485 interface

The production-tested interface is a USB RS485 converter using an FTDI USB serial interface. The tested device enumerated on Linux as an FTDI FT232R serial converter.

The earlier GPIO/TTL RS485 interface was not used in the final implementation.

### RS-485 cable

Use a twisted pair for A/B. CAT5e is suitable for short installations; shielded 22/2 or similar RS485 cable may be preferred in electrically noisy environments.

## Airzone Modbus configuration

The Airzone documentation specifies Modbus RTU with:

- Half duplex RS-485
- 8 data bits
- 1 stop bit
- Even parity
- Default baud rate: 19200 bps
- Slave addresses: 1–247
- Default slave address: 1
- Function 03: Read Holding Registers
- Function 04: Read Input Registers
- Function 06: Write Single Holding Register
- Function 16: Write Multiple Holding Registers

The Airzone documentation identifies the DKN as a Modbus slave and provides the register table used by this project.

## RS-485 wiring

The Airzone documentation identifies the RS-485 communication conductors by color. In this installation:

| Airzone | USB RS485 |
|---|---|
| Blue / BMS+ / A+ | A+ / D+ |
| Green / BMS- / B- | B- / D- |

## Raspberry Pi USB setup

The final system uses the USB RS485 interface rather than the Pi GPIO UART for Modbus. Connect the USB RS485 adapter to the Pi USB data/OTG port.

Verify the adapter is detected:

```bash
lsusb
ls /dev/ttyUSB*
ls -l /dev/serial/by-id/
```

Prefer the persistent `/dev/serial/by-id/...` path in the Python configuration.

Example:

```text
/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG01PRL4-if00-port0
```

## Python environment

Create the virtual environment:

```bash
sudo apt update
sudo apt install python3-venv -y
python3 -m venv ~/airzone-env
```

Activate it:

```bash
source ~/airzone-env/bin/activate
```

Install the required packages:

```bash
pip install pyserial paho-mqtt
```

## Modbus register map

| Register | Function | Values / scaling | Access |
|---:|---|---|---|
| 0 | Power | `0 = Off`, `1 = On` | Read/Write |
| 1 | Setpoint | Temperature × 10 | Read/Write |
| 2 | Room temperature | Temperature × 10 | Read only |
| 3 | HVAC mode | `1 = Auto`, `2 = Cooling`, `3 = Heating`, `4 = Fan`, `5 = Dry` | Read/Write |
| 4 | Fan speed | `0–100%`, `0 = Automatic` | Read only |
| 5 | Vertical louver | `0–7`, `8 = Auto`, `9 = Swing`, `10 = Swirl` | Read/Write |
| 14 | Available modes | Bit 0 Auto, 1 Cool, 2 Heat, 3 Vent, 4 Dry | Read only |
| 15 | Available speeds | Bitmask of available fan speeds | Read only |
| 54 | Numeric fan speed | `0 = Auto`, `1,2,3...` | Read/Write |
| 56 | Modbus slave address | Default `1` | Read/Write |
| 57 | Port baud configuration | `8 = 19200` | Read/Write |
| 58 | Port parity configuration | `2 = Even` | Read/Write |

Temperature values use a ×10 representation. The numeric fan-speed register 54 is documented as `0,1,2,3...`, with `0` meaning automatic.

## Verified installation behavior

During bring-up, the installed Airzone/Daikin system returned:

- Register 0 = `1` when the HVAC was on
- Register 1 = `720` when the target was 72°F
- Register 2 = `690` when room temperature was 69°F
- Register 3 = `2` in cooling mode
- Register 3 = `3` in heating mode
- Writing register 1 with `740` changed the HVAC setpoint to 74°F
- The Modbus response was a valid RTU frame with slave address 1 and function 03

These observations matched the Airzone register definitions used for the installed system.

## Modbus bridge

The production bridge is `rpi/airzone_bridge.py`.

Its responsibilities are:

1. Open the FTDI USB RS485 serial interface at 19200/8/E/1.
2. Poll the Airzone registers.
3. Publish HVAC state to MQTT.
4. Subscribe to MQTT command topics.
5. Translate Home Assistant commands into Modbus writes.
6. Publish MQTT Discovery configuration so Home Assistant creates the device and climate entity automatically.
7. Remain running continuously under systemd.

### MQTT state topics

| Topic | Payload |
|---|---|
| `airzone/power/state` | `0` or `1` |
| `airzone/setpoint/state` | target temperature |
| `airzone/roomtemp/state` | current temperature |
| `airzone/mode/state` | `off`, `auto`, `cool`, `heat`, `fan_only`, `dry` |
| `airzone/fan/state` | `auto`, `1`, `2`, `3` |

### MQTT command topics

| Topic | Payload |
|---|---|
| `airzone/setpoint/set` | temperature, e.g. `74` |
| `airzone/mode/set` | `off`, `auto`, `cool`, `heat`, `fan_only`, `dry` |
| `airzone/fan/set` | `auto`, `1`, `2`, `3` |

## Home Assistant MQTT Discovery

The bridge publishes an MQTT Discovery payload under:

```text
homeassistant/climate/daikin_mini_split/config
```

The climate entity is associated with a device identified as Daikin/Airzone Aidoo. The resulting entity in this installation is:

```text
climate.daikin_mini_split
```

Supported HVAC modes:

- Off
- Auto
- Cool
- Heat
- Fan Only
- Dry

Supported fan modes:

- Auto
- 1
- 2
- 3

## systemd service

The bridge runs from the Python virtual environment and is configured as a persistent service.

Create:

```text
/etc/systemd/system/airzone-bridge.service
```

with:

```ini
[Unit]
Description=Airzone MQTT Modbus Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi
ExecStart=/home/pi/airzone-env/bin/python /home/pi/airzone_bridge.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable airzone-bridge
sudo systemctl start airzone-bridge
```

Check status:

```bash
sudo systemctl status airzone-bridge
```

Follow logs:

```bash
journalctl -u airzone-bridge -f
```

## Home Assistant automation preserved from the original project

The repository retains the existing upstairs setpoint synchronization automation:

```text
ha/sync_upstairs_mini_split_setpoint.yaml
```

This automation is separate from the Modbus transport layer. It watches the downstairs Honeywell T6 Pro target temperature and sets the upstairs Daikin target to the downstairs target +2°F, with a 70°F minimum. It changes only the Daikin temperature setpoint and does not synchronize HVAC mode.

Downstairs entities:

```text
sensor.tstat_24d76e_current_temperature
climate.tstat_24d76e_t6_pro_thermostat
```

Upstairs entity:

```text
climate.daikin_mini_split
```

## Repository layout

```text
.
├── README.md
├── LICENSE
├── docs/
│   ├── airzone_dkn_modbus_manual.pdf
│   └── wiring/
│       ├── usb-rs485-to-airzone.png
│       └── system-block-diagram.png
├── rpi/
│   ├── airzone_bridge.py
│   ├── airzone_test.py
│   ├── systemd/
│   │   └── airzone-bridge.service
│   └── requirements.txt
└── ha/
    └── sync_upstairs_mini_split_setpoint.yaml
```

## Reference documentation

`docs/airzone_dkn_modbus_manual.pdf` is the Airzone DKN Modbus integration manual used as the source for serial parameters, function codes, and register definitions.

## Safety / deployment notes

This project contains Home Assistant automation and HVAC control code intended for a specific installation. Review entity IDs, wiring, register definitions, HVAC behavior, and electrical safety requirements before deploying it elsewhere.

## Development status

The basic Modbus transport and Home Assistant MQTT control path are working. Future development can add diagnostics, availability reporting, additional Airzone registers, louver control, and additional devices/zones.