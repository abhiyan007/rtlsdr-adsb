import socket
import argparse
import time
import json
import os
import threading
from datetime import datetime
from decoder import (
    decode_callsign, decode_cpr, decode_altitude,
    decode_velocity, msg_type, EMERGENCY_SQUAWKS
)

STALE_SECS = 120
LOG_FILE = 'flights.json'

class Aircraft:
    def __init__(self, icao):
        self.icao     = icao
        self.callsign = None
        self.alt      = None
        self.speed    = None
        self.heading  = None
        self.vrate    = None
        self.lat      = None
        self.lon      = None
        self.squawk   = None
        self.on_ground = False
        self.last_seen = time.time()
        self.first_seen = time.time()
        self._cpr     = {}

    def feed_cpr(self, lat_raw, lon_raw, odd):
        self._cpr[odd] = (lat_raw, lon_raw, time.time())
        if 0 in self._cpr and 1 in self._cpr:
            if abs(self._cpr[0][2] - self._cpr[1][2]) < 10:
                lat, lon = decode_cpr(
                    self._cpr[0][0], self._cpr[0][1],
                    self._cpr[1][0], self._cpr[1][1],
                    odd
                )
                if lat is not None:
                    self.lat, self.lon = lat, lon

    def to_dict(self):
        return {
            'icao':       self.icao,
            'callsign':   self.callsign,
            'alt':        self.alt,
            'speed':      self.speed,
            'heading':    self.heading,
            'lat':        self.lat,
            'lon':        self.lon,
            'squawk':     self.squawk,
            'first_seen': datetime.fromtimestamp(self.first_seen).isoformat(),
            'last_seen':  datetime.fromtimestamp(self.last_seen).isoformat(),
        }

    def fmt(self):
        cs  = (self.callsign or 'unknown').ljust(10)
        alt = f'{self.alt}ft'.ljust(9) if self.alt is not None else '?ft'.ljust(9)
        spd = f'{self.speed}kts'.ljust(8) if self.speed is not None else ''
        pos = f'({self.lat:.4f}, {self.lon:.4f})' if self.lat is not None else ''
        return f'{self.icao}  {cs}  {alt}  {spd}  {pos}'


def parse_bs(line):
    parts = line.strip().split(',')
    if len(parts) < 22 or parts[0] != 'MSG':
        return None
    def f(i):
        return parts[i] if i < len(parts) and parts[i] else None
    return {
        'type':     f(1),
        'icao':     f(4),
        'callsign': f(10).strip() if f(10) else None,
        'alt':      int(f(11)) if f(11) and f(11).lstrip('-').isdigit() else None,
        'speed':    int(f(12)) if f(12) and f(12).isdigit() else None,
        'heading':  float(f(13)) if f(13) else None,
        'lat':      float(f(14)) if f(14) else None,
        'lon':      float(f(15)) if f(15) else None,
        'vrate':    int(f(16)) if f(16) and f(16).lstrip('-').isdigit() else None,
        'squawk':   f(17),
        'ground':   f(21) == '-1',
    }

def prune(aircraft):
    now = time.time()
    gone = [k for k, v in aircraft.items() if now - v.last_seen > STALE_SECS]
    for k in gone:
        del aircraft[k]

def save(aircraft):
    data = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                data = json.load(f)
    except:
        pass
    data.extend(v.to_dict() for v in aircraft.values())
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='localhost')
    p.add_argument('--port', type=int, default=30003)
    p.add_argument('--no-log', action='store_true')
    args = p.parse_args()

    print(f'connecting to {args.host}:{args.port}')

    s = socket.create_connection((args.host, args.port))
    stream = s.makefile('r')

    print(f'listening...\n')

    aircraft = {}
    lock = threading.Lock()

    def pruner():
        while True:
            time.sleep(30)
            with lock:
                before = len(aircraft)
                prune(aircraft)
                gone = before - len(aircraft)
                if gone:
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] pruned {gone} stale')

    t = threading.Thread(target=pruner, daemon=True)
    t.start()

    try:
        for line in stream:
            msg = parse_bs(line)
            if not msg or not msg['icao']:
                continue

            icao = msg['icao'].upper()
            now_str = datetime.now().strftime('%H:%M:%S')

            with lock:
                new = icao not in aircraft
                if new:
                    aircraft[icao] = Aircraft(icao)
                ac = aircraft[icao]
                ac.last_seen = time.time()

                if msg['callsign']:
                    ac.callsign = msg['callsign']
                if msg['alt'] is not None:
                    ac.alt = msg['alt']
                if msg['speed'] is not None:
                    ac.speed = msg['speed']
                if msg['heading'] is not None:
                    ac.heading = round(msg['heading'])
                if msg['vrate'] is not None:
                    ac.vrate = msg['vrate']
                if msg['lat'] and msg['lon']:
                    ac.lat = msg['lat']
                    ac.lon = msg['lon']
                if msg['squawk']:
                    prev_squawk = ac.squawk
                    ac.squawk = msg['squawk']
                    if msg['squawk'] in EMERGENCY_SQUAWKS and msg['squawk'] != prev_squawk:
                        label = EMERGENCY_SQUAWKS[msg['squawk']]
                        print(f'{now_str}  !!!   {ac.fmt()}  ** {label} **')

                tag = 'NEW' if new else 'UPD'
                if new or msg['lat']:
                    print(f'{now_str}  {tag}   {ac.fmt()}')

    except KeyboardInterrupt:
        print(f'\n{len(aircraft)} aircraft tracked')
        if not args.no_log:
            with lock:
                save(aircraft)
            print(f'saved to {LOG_FILE}')

if __name__ == '__main__':
    main()
