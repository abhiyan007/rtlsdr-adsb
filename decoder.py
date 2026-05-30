import math

NZ = 15

CALLSIGN_CHARS = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ#####_###############0123456789######'

TYPECODES = {
    range(1,  5):  'aircraft_id',
    range(5,  9):  'surface_pos',
    range(9,  19): 'airborne_pos_baro',
    range(19, 20): 'airborne_vel',
    range(20, 23): 'airborne_pos_gnss',
    range(28, 29): 'aircraft_status',
    range(29, 31): 'target_state',
    range(31, 32): 'op_status',
}

EMERGENCY_SQUAWKS = {
    '7500': 'HIJACK',
    '7600': 'COMMS FAILURE',
    '7700': 'EMERGENCY',
}

def msg_type(tc):
    for r, t in TYPECODES.items():
        if tc in r:
            return t
    return 'unknown'

def decode_callsign(data):
    cs = ''
    for i in range(8):
        idx = (data >> (42 - 6 * i)) & 0x3F
        cs += CALLSIGN_CHARS[idx]
    return cs.strip()

def _cpr_mod(a, b):
    return a - b * math.floor(a / b)

def _nl(lat):
    if abs(lat) >= 87.0:
        return 1
    if abs(lat) >= 86.5354:
        return 2
    return max(1, math.floor(
        2 * math.pi / math.acos(
            1 - (1 - math.cos(math.pi / (2 * NZ))) /
            (math.cos(math.radians(abs(lat))) ** 2)
        )
    ))

def decode_cpr(lat0_raw, lon0_raw, lat1_raw, lon1_raw, odd):
    lat0 = lat0_raw / 131072.0
    lat1 = lat1_raw / 131072.0
    lon0 = lon0_raw / 131072.0
    lon1 = lon1_raw / 131072.0

    dlat0 = 360.0 / (4 * NZ)
    dlat1 = 360.0 / (4 * NZ - 1)

    j = math.floor(59 * lat0 - 60 * lat1 + 0.5)

    lat0 = dlat0 * (_cpr_mod(j, 60) + lat0)
    lat1 = dlat1 * (_cpr_mod(j, 59) + lat1)

    if lat0 >= 270: lat0 -= 360
    if lat1 >= 270: lat1 -= 360

    if _nl(lat0) != _nl(lat1):
        return None, None

    lat = lat1 if odd else lat0

    nl  = _nl(lat)
    ni  = max(nl - (1 if odd else 0), 1)
    m   = math.floor(lon0 * (nl - 1) - lon1 * nl + 0.5)
    dlon = 360.0 / ni

    lon_raw = lon1 if odd else lon0
    lon = dlon * (_cpr_mod(m, ni) + lon_raw)
    if lon >= 180:
        lon -= 360

    return round(lat, 5), round(lon, 5)

def decode_altitude(msg, gnss=False):
    if gnss:
        return ((msg >> 36) & 0xFFF) * 25 - 1000

    q = (msg >> 40) & 1
    if q:
        n = ((msg >> 41) & 0x7FF) | ((msg >> 40) & 0xF)
        return n * 25 - 1000

    gray = ((msg >> 41) & 0x7FF) | ((msg >> 40) & 0xF)
    n = 0
    while gray:
        n ^= gray
        gray >>= 1
    return n * 100 - 1200

def decode_velocity(data):
    sub = (data >> 48) & 0x7

    if sub in (1, 2):
        vew_sign = (data >> 43) & 1
        vew = ((data >> 32) & 0x7FF) - 1
        vns_sign = (data >> 30) & 1
        vns = ((data >> 19) & 0x7FF) - 1

        if vew < 0 or vns < 0:
            return None, None, None

        vew = -vew if vew_sign else vew
        vns = -vns if vns_sign else vns

        spd = round(math.sqrt(vew**2 + vns**2))
        hdg = round(math.degrees(math.atan2(vew, vns))) % 360

        vr_sign = (data >> 10) & 1
        vr = ((data >> 0) & 0x1FF) - 1
        if vr >= 0:
            vr = (-64 if vr_sign else 64) * vr

        return spd, hdg, vr

    if sub in (3, 4):
        hdg_ok = (data >> 47) & 1
        hdg = round(((data >> 36) & 0x3FF) / 1024 * 360) if hdg_ok else None
        spd = ((data >> 21) & 0x3FF) - 1
        spd = round(spd * 0.514444) if spd >= 0 else None
        return spd, hdg, None

    return None, None, None
