import socket
import argparse
import json
import os
from datetime import datetime

LOG_FILE = 'flights.json'

def connect(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s.makefile('r')

def parse(line):
    parts = line.strip().split(',')
    if len(parts) < 22 or parts[0] != 'MSG':
        return None
    return {
        'icao':     parts[4],
        'callsign': parts[10].strip() or None,
        'alt':      int(parts[11])    if parts[11]  else None,
        'speed':    int(parts[12])    if parts[12]  else None,
        'lat':      float(parts[14]) if parts[14]  else None,
        'lon':      float(parts[15]) if parts[15]  else None,
    }

def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_log(data):
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def fmt(msg):
    cs  = (msg.get('callsign') or 'unknown').ljust(10)
    alt = f"{msg['alt']}ft" if msg.get('alt') else '?ft'
    pos = f"({msg['lat']:.2f}, {msg['lon']:.2f})" if msg.get('lat') else ''
    return f"{msg['icao']}   {cs}  {alt}   {pos}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=30003)
    args = parser.parse_args()

    print(f'listening on {args.host}:{args.port}\n')

    aircraft = {}
    log = load_log()

    try:
        stream = connect(args.host, args.port)
        for line in stream:
            msg = parse(line)
            if not msg or not msg['icao']:
                continue

            icao = msg['icao']
            now  = datetime.now().strftime('%H:%M:%S')
            prev = aircraft.get(icao)

            if not prev:
                aircraft[icao] = msg
                print(f'{now}  NEW   {fmt(msg)}')
            else:
                updated = {k: v for k, v in msg.items() if v is not None}
                aircraft[icao].update(updated)
                if msg.get('lat'):
                    print(f'{now}  UPD   {fmt(aircraft[icao])}')

    except KeyboardInterrupt:
        print(f'\n{len(aircraft)} unique aircraft seen\n')
        seen = datetime.now().isoformat()
        for icao, data in aircraft.items():
            entry = {'seen': seen, **data}
            log.append(entry)
        save_log(log)
        print(f'saved to {LOG_FILE}')

if __name__ == '__main__':
    main()
