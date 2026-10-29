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
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.decrepit.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.padding import PKCS7

SOURCE = None
OUTPUT = Path("Aprilia-Telemetry")

def decrypt_record(line, key):
    ciphertext = base64.b64decode(line, validate=True)
    decryptor = Cipher(algorithms.Blowfish(key), modes.ECB()).decryptor()
    raw = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = PKCS7(64).unpadder()
    return json.loads(unpadder.update(raw) + unpadder.finalize())

def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))
    return value.strip("._") or "unknown"

def timestamp_date(value):
    try:
        return datetime.fromtimestamp(
            float(value) / 1000, timezone.utc
        ).astimezone().strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError, OSError):
        return "unknown-date"

def readable_timestamp(value):
    try:
        return datetime.fromtimestamp(
            float(value) / 1000, timezone.utc
        ).astimezone().isoformat(timespec="milliseconds")
    except (ValueError, TypeError, OverflowError, OSError):
        return value

def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {Path(sys.argv[0]).name} <export.json>")

    source = Path(sys.argv[1])
    if not source.is_file():
        sys.exit(f"Error: {source} not found or is not a file.")

    lines = source.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or not lines[0].startswith("#POC-BACKUP-STREAM"):
        sys.exit("Error: unrecognized Aprilia backup format.")

    metadata = json.loads(lines[1])
    key = metadata["header"]["userId"].encode("utf-8")

    OUTPUT.mkdir(exist_ok=True)
    trips = []
    activities = []
    trip_ids = set()
    gps_status_by_id = {}
    errors = 0

    for line in lines[2:]:
        if not line.strip():
            continue
        try:
            record = decrypt_record(line, key)
        except Exception as exc:
            errors += 1
            print(f"Warning: skipped unreadable record ({exc})", file=sys.stderr)
            continue

        kind = record.get("t")
        data = record.get("d", {})

        if kind == "trip":
            trips.append(data)
            trip_id = data.get("id")
            if trip_id is not None:
                trip_ids.add(trip_id)
                gps = data.get("tripGPS", "")
                gps_rows = gps.splitlines() if isinstance(gps, str) else []
                gps_status_by_id[trip_id] = (
                    "available"
                    if len(gps_rows) > 2
                    and gps_rows[0].strip() == "ts;lat;lng;alt"
                    else "missing_gps"
                )
        elif kind == "activity":
            activities.append(data)

    telemetry_count = 0
    trip_rows = []

    for index, trip in enumerate(trips, 1):
        raw_data = trip.get("tripData", "")
        if not isinstance(raw_data, str) or not raw_data.strip():
            continue

        rows = list(csv.reader(raw_data.splitlines(), delimiter=";"))
        if not rows:
            continue

        header = rows[0]
        if not header or header[0] != "ts":
            print(f"Warning: trip {index}: unexpected telemetry header", file=sys.stderr)
            continue

        valid_rows = []
        for row in rows[1:]:
            if len(row) != len(header):
                continue
            row[0] = readable_timestamp(row[0])
            valid_rows.append(row)

        if not valid_rows:
            continue

        trip_id = trip.get("id", index)
        date = valid_rows[0][0][:10] if valid_rows else "unknown-date"
        filename = f"{index:03d}_{date}_{safe_name(trip_id)}.csv"

        with (OUTPUT / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp_local" if name == "ts" else name for name in header])
            writer.writerows(valid_rows)

        telemetry_count += len(valid_rows)
        trip_rows.append({
            "trip_index": index,
            "trip_id": trip_id,
            "date": date,
            "telemetry_file": filename,
            "telemetry_rows": len(valid_rows),
        })

    summary_path = OUTPUT / "trips-summary.csv"
    if activities:
        telemetry_files = {row["trip_id"]: row["telemetry_file"] for row in trip_rows}
        fields = sorted({field for item in activities for field in item})
        fields.append("telemetry_file")
        fields.append("duration_hms")
        fields.append("telemetry_status")
        fields.append("gps_status")

        for item in activities:
            try:
                seconds = int(float(item["duration"]))
                item["duration_hms"] = (
                    f"{seconds // 3600:02d}:"
                    f"{(seconds % 3600) // 60:02d}:"
                    f"{seconds % 60:02d}"
                )
            except (KeyError, ValueError, TypeError, OverflowError):
                item["duration_hms"] = ""

            trip_id = item.get("id")
            item["telemetry_file"] = telemetry_files.get(trip_id, "")

            if item.get("type") != "trip":
                item["telemetry_status"] = "not_applicable"
                item["gps_status"] = "not_applicable"
            elif trip_id not in trip_ids:
                item["telemetry_status"] = "missing_trip_record"
                item["gps_status"] = "missing_trip_record"
            else:
                item["telemetry_status"] = (
                    "available" if item["telemetry_file"] else "missing_telemetry"
                )
                item["gps_status"] = gps_status_by_id.get(trip_id, "missing_gps")

        with summary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(activities)

            index_path = OUTPUT / "telemetry-index.csv"
            with index_path.open("w", newline="", encoding="utf-8") as handle:
                fields = ["trip_index", "trip_id", "date", "telemetry_file", "telemetry_rows"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(trip_rows)

    print(f"Trips found: {len(trips)}")
    print(f"Activity summaries: {len(activities)}")
    print(f"Telemetry CSV files written: {len(trip_rows)}")
    print(f"Telemetry rows written: {telemetry_count}")
    print(f"Unreadable records skipped: {errors}")
    print(f"Output directory: {OUTPUT.resolve()}")

if __name__ == "__main__":
    main()
