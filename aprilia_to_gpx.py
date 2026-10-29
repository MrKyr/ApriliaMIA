#!/usr/bin/env python3

# (ↄ) Copyleft 2026 Kyriakos Bellios
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License version 2 for more details.
#
# You should have received a copy of the GNU General Public License
# version 2 along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import base64
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
from cryptography.hazmat.primitives.ciphers import Cipher, modes

SOURCE = None
OUTPUT = Path("Aprilia-GPX")
GPX_NS = "http://www.topografix.com/GPX/1/1"

ET.register_namespace("", GPX_NS)


def decrypt_record(line, key):
    encrypted = base64.b64decode(line, validate=True)
    decryptor = Cipher(Blowfish(key), modes.ECB()).decryptor()
    plain = decryptor.update(encrypted) + decryptor.finalize()

    padding = plain[-1]
    if not 1 <= padding <= 8 or plain[-padding:] != bytes([padding]) * padding:
        raise ValueError("Invalid encrypted-record padding")

    return json.loads(plain[:-padding].decode("utf-8"))


def gpx_tag(name):
    return f"{{{GPX_NS}}}{name}"


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {Path(sys.argv[0]).name} <export.json>")

    source = Path(sys.argv[1])
    if not source.is_file():
        sys.exit(f"Error: {source} not found or is not a file.")

    lines = source.read_bytes().splitlines()
    if len(lines) < 3 or not lines[1].startswith(b"{"):
        sys.exit("Unrecognized Aprilia export format")

    metadata = json.loads(lines[1])
    if metadata.get("encrypted") is not True:
        sys.exit("Export does not declare encrypted data")

    user_id = metadata.get("header", {}).get("userId")
    if not user_id:
        sys.exit("Could not find the encryption key in export metadata")

    key = user_id.encode("utf-8")
    trips = []
    malformed = 0

    trip_index = 0
    for line in lines[2:]:
        if not line:
            continue
        try:
            record = decrypt_record(line, key)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            malformed += 1
            continue

        if record.get("t") != "trip":
            continue

        trip_index += 1

        data = record.get("d", {})
        gps = data.get("tripGPS", "")
        rows = gps.splitlines()
        if not rows:
            continue

        header = rows[0].strip().split(";")
        if header != ["ts", "lat", "lng", "alt"]:
            continue

        points = []
        for row in rows[1:]:
            fields = row.strip().split(";")
            if len(fields) != 4:
                continue
            try:
                ts, lat, lon, ele = map(float, fields)
                if not all(math.isfinite(v) for v in (ts, lat, lon, ele)):
                    continue
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                timestamp = datetime.fromtimestamp(
                    ts / 1000, timezone.utc
                ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            except (ValueError, OverflowError, OSError):
                continue

            points.append((timestamp, lat, lon, ele))

        if len(points) >= 2:
            date = points[0][0][:10]
            raw_data = data.get("tripData", "")
            if isinstance(raw_data, str) and raw_data.strip():
                telemetry_rows = raw_data.splitlines()
                if len(telemetry_rows) > 1:
                    fields = telemetry_rows[1].split(";")
                    if fields and fields[0]:
                        try:
                            date = datetime.fromtimestamp(
                                float(fields[0]) / 1000, timezone.utc
                            ).astimezone().date().isoformat()
                        except (ValueError, TypeError, OverflowError, OSError):
                            pass

            trips.append((trip_index, str(data.get("id", "")), date, points))

    OUTPUT.mkdir(exist_ok=True)
    written = 0

    for number, trip_id, date, points in trips:
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "", trip_id)[:24] or "trip"
        filename = OUTPUT / f"{number:03d}_{date}_{safe_id}.gpx"

        root = ET.Element(gpx_tag("gpx"), {
            "version": "1.1",
            "creator": "Aprilia MIA GPX converter",
        })
        metadata_el = ET.SubElement(root, gpx_tag("metadata"))
        ET.SubElement(metadata_el, gpx_tag("name")).text = (
            f"Aprilia trip {number} — {date}"
        )

        track = ET.SubElement(root, gpx_tag("trk"))
        ET.SubElement(track, gpx_tag("name")).text = (
            f"Aprilia trip {number} — {date}"
        )
        segment = ET.SubElement(track, gpx_tag("trkseg"))

        for timestamp, lat, lon, ele in points:
            point = ET.SubElement(segment, gpx_tag("trkpt"), {
                "lat": format(lat, ".8f"),
                "lon": format(lon, ".8f"),
            })
            ET.SubElement(point, gpx_tag("ele")).text = format(ele, ".2f")
            ET.SubElement(point, gpx_tag("time")).text = timestamp

        ET.indent(root, space="  ")
        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        written += 1

    print(f"Trips exported: {written}")
    print(f"Output directory: {OUTPUT.resolve()}")
    if malformed:
        print(f"Records that could not be decrypted or parsed: {malformed}")
    if not written:
        print("No trips with at least two valid GPS points were found.")


if __name__ == "__main__":
    main()
