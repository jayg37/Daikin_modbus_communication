#!/home/pi/airzone-env/bin/python

import serial

PORT = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG01PRL4-if00-port0"

ser = serial.Serial(
    port=PORT,
    baudrate=19200,
    bytesize=8,
    parity=serial.PARITY_EVEN,
    stopbits=1,
    timeout=3,
)

print(f"Port {PORT} opened")

# Read Airzone register 2 (room temperature).
request = bytes([0x01, 0x03, 0x00, 0x02, 0x00, 0x01, 0x25, 0xCA])

print("Sending:", request.hex())
ser.write(request)

response = ser.read(100)

if response:
    print("Received:", response.hex())
    print("Length:", len(response))
else:
    print("No response received from the device.")

ser.close()
