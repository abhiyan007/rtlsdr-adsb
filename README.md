# rtlsdr-adsb

Picks up ADS-B signals from aircraft using a cheap RTL-SDR dongle. Every commercial plane broadcasts its position, altitude, speed, and callsign unencrypted on 1090 MHz. You just listen.

## hardware

- RTL-SDR Blog v3 dongle (~$25)
- Included telescoping antenna, pointed up

## how it works

`dump1090` does the actual radio decoding and runs a local server. `logger.py` connects to that server, parses the aircraft messages, and logs everything it sees.

## setup

Install dump1090:
```bash
sudo apt install dump1090-mutability
dump1090 --interactive --net
```

Then run the logger:
```bash
python logger.py
```

Pass `--host` and `--port` if dump1090 is on a different machine.

## output

```
listening on localhost:30003

14:22:01  NEW   A3B1C2   UAL2183    35000ft   (41.88, -87.63)
14:22:04  NEW   C0D4E5   DAL445     28500ft   (42.01, -87.90)
14:22:09  UPD   A3B1C2   UAL2183    35000ft   (41.92, -87.51)
```
