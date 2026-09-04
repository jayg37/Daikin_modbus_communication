#!/home/pi/airzone-env/bin/python

import json
import struct
import time
from datetime import datetime

import paho.mqtt.client as mqtt
import serial

MQTT_BROKER = "YOUR_HOME_ASSISTANT_IP"
MQTT_PORT = 1883
MQTT_USER = "airzone"
MQTT_PASS = "YOUR_MQTT_PASSWORD"

PORT = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG01PRL4-if00-port0"
SLAVE_ID = 1

DEVICE_NAME = "Daikin Mini Split"
DEVICE_ID = "daikin_mini_split"

ser = serial.Serial(
    port=PORT,
    baudrate=19200,
    bytesize=8,
    parity=serial.PARITY_EVEN,
    stopbits=1,
    timeout=2,
)

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)
client.username_pw_set(MQTT_USER, MQTT_PASS)


def modbus_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return struct.pack("<H", crc)


def read_register(register):
    request = bytes([
        SLAVE_ID,
        0x03,
        (register >> 8) & 0xFF,
        register & 0xFF,
        0x00,
        0x01,
    ])
    request += modbus_crc(request)
    ser.write(request)
    time.sleep(0.2)
    response = ser.read(100)
    if len(response) >= 5:
        return response[3] << 8 | response[4]
    return None


def write_register(register, value):
    request = bytes([
        SLAVE_ID,
        0x06,
        (register >> 8) & 0xFF,
        register & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ])
    request += modbus_crc(request)

    print(f"{datetime.now()} WRITE -> Register {register} Value {value}")
    with open("/home/pi/modbus_writes.log", "a") as f:
        f.write(f"{datetime.now()} Register={register} Value={value}\n")

    ser.write(request)
    time.sleep(0.2)
    response = ser.read(100)
    if response:
        print(f"Write response: {response.hex()}")
        return True
    print("No write response")
    return False


def publish_discovery():
    discovery_topic = f"homeassistant/climate/{DEVICE_ID}/config"
    payload = {
        "name": DEVICE_NAME,
        "unique_id": DEVICE_ID,
        "mode_state_topic": "airzone/mode/state",
        "mode_command_topic": "airzone/mode/set",
        "modes": ["off", "auto", "cool", "heat", "fan_only", "dry"],
        "temperature_state_topic": "airzone/setpoint/state",
        "temperature_command_topic": "airzone/setpoint/set",
        "current_temperature_topic": "airzone/roomtemp/state",
        "temp_step": 1,
        "min_temp": 60,
        "max_temp": 86,
        "precision": 1.0,
        "fan_mode_state_topic": "airzone/fan/state",
        "fan_mode_command_topic": "airzone/fan/set",
        "fan_modes": ["auto", "1", "2", "3"],
        "device": {
            "identifiers": [DEVICE_ID],
            "name": DEVICE_NAME,
            "manufacturer": "Daikin/Airzone",
            "model": "Airzone Aidoo",
            "sw_version": "1.0",
        },
    }
    client.publish(discovery_topic, json.dumps(payload), retain=True)
    print("Published MQTT discovery")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    print(f"MQTT COMMAND: {topic} -> {payload}")
    with open("/home/pi/mqtt_commands.log", "a") as f:
        f.write(f"{datetime.now()} {topic} {payload}\n")

    try:
        if topic == "airzone/setpoint/set":
            temp = int(float(payload) * 10)
            success = write_register(1, temp)
            print(f"Setpoint write success: {success}")

        elif topic == "airzone/mode/set":
            if payload == "off":
                success = write_register(0, 0)
                print(f"Power OFF success: {success}")
            else:
                write_register(0, 1)
                modes = {
                    "auto": 1,
                    "cool": 2,
                    "heat": 3,
                    "fan_only": 4,
                    "dry": 5,
                }
                if payload in modes:
                    success = write_register(3, modes[payload])
                    print(f"Mode write success: {success}")

        elif topic == "airzone/fan/set":
            fan_modes = {"auto": 0, "1": 1, "2": 2, "3": 3}
            if payload in fan_modes:
                success = write_register(54, fan_modes[payload])
                print(f"Fan write success: {success}")

    except Exception as e:
        print(f"MQTT write error: {e}")


print("Connecting to MQTT broker...")
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
print("Connected to MQTT broker")
client.subscribe("airzone/setpoint/set")
client.subscribe("airzone/mode/set")
client.subscribe("airzone/fan/set")
print("MQTT subscriptions active")
client.loop_start()
publish_discovery()

last_setpoint = None

while True:
    try:
        power = read_register(0)
        setpoint = read_register(1)
        room_temp = read_register(2)
        mode = read_register(3)
        fan = read_register(54)

        if setpoint is not None:
            client.publish("airzone/setpoint/state", setpoint / 10, retain=True)

        if room_temp is not None:
            client.publish("airzone/roomtemp/state", room_temp / 10, retain=True)

        if power is not None:
            client.publish("airzone/power/state", power, retain=True)

        if power == 0:
            client.publish("airzone/mode/state", "off", retain=True)
        elif mode is not None:
            mode_map = {
                1: "auto",
                2: "cool",
                3: "heat",
                4: "fan_only",
                5: "dry",
            }
            client.publish("airzone/mode/state", mode_map.get(mode, "unknown"), retain=True)

        if fan is not None:
            fan_map = {0: "auto", 1: "1", 2: "2", 3: "3"}
            client.publish("airzone/fan/state", fan_map.get(fan, "auto"), retain=True)

        if setpoint is not None and setpoint != last_setpoint:
            print(f"SETPOINT CHANGED: {last_setpoint} -> {setpoint}")
            with open("/home/pi/setpoint_changes.log", "a") as f:
                f.write(f"{datetime.now()} {last_setpoint} -> {setpoint}\n")
            last_setpoint = setpoint

        time.sleep(5)

    except Exception as e:
        print(f"Main loop error: {e}")
        time.sleep(5)
