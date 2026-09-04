# Airzone RS485 Wiring

The tested production connection is:

```text
USB RS485 adapter                    Airzone DKN
-----------------                    -----------
A+ / D+  --------------------------> Blue / BMS+
B- / D-  --------------------------> Green / BMS-
```

Use a twisted pair for A/B. For the Raspberry Pi Zero 2 W, connect the USB RS485 adapter to the USB data/OTG port, not the power-only connector.

The Airzone manual identifies the communication conductors as green/blue and specifies RS-485 half duplex, 8-bit framing, one stop bit, no flow control, and even parity. The manual also specifies a default baud rate of 19200 bps. 
