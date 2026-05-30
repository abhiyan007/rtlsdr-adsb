# rtlsdr-adsb

ADS-B aircraft tracking with an RTL-SDR dongle. Decodes position using CPR (Compact Position Reporting), tracks squawk codes, detects emergency transponder codes.

## setup

```bash
sudo apt install dump1090-mutability
dump1090 --net --quiet
```

```bash
pip install pyModeS
python tracker.py
python tracker.py --host 192.168.1.x --port 30003
```

`decoder.py` has the raw message parsing and CPR math if you want to use it standalone.

## what it does

connects to dump1090's BaseStation output (port 30003), decodes each message type, resolves CPR position pairs into lat/lon, flags emergency squawks.

```
listening on localhost:30003

14:23:01  NEW   A1B2C3  UAL2183     35000ft  412kts  (41.8781, -87.6298)
14:23:04  NEW   D4E5F6  DAL0091     28500ft  380kts  (42.0121, -87.9034)
14:23:07  UPD   A1B2C3  UAL2183     35000ft  412kts  (41.8820, -87.6101)
14:24:11  !!!   B0C1D2  unknown     12000ft           SQUAWK 7700 (EMERGENCY)
```

## hardware

RTL-SDR Blog v3, stock telescoping antenna aimed up. Getting 150-200nm range on clear days.
