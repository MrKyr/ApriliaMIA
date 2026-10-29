#!/usr/bin/gawk -f

BEGIN {
    FS = ","
    if (sort == "")
        sort = "date"
}

NR == 1 {
    for (i = 1; i <= NF; i++)
        col[$i] = i
    next
}

{
    if ($(col["telemetry_status"]) != "available")
        next

    file = $(col["telemetry_file"])
    if (file == "")
        next

    distance = $(col["distance"]) + 0
    duration = $(col["duration"]) + 0
    liters = $(col["tripLitersConsumed"]) + 0
    path = "Aprilia-Telemetry/" file

    date_col = speed_col = rpm_col = voltage_col = 0
    max_speed = max_rpm = 0
    min_voltage = 1e9
    max_voltage = 0

    if ((getline line < path) <= 0) {
        close(path)
        next
    }

    n = split(line, fields, ",")
    for (i = 1; i <= n; i++) {
        if (fields[i] == "timestamp_local") date_col = i
        if (fields[i] == "speed") speed_col = i
        if (fields[i] == "rpm") rpm_col = i
        if (fields[i] == "batteryVoltage") voltage_col = i
    }

    if (!speed_col || !rpm_col || !voltage_col) {
        close(path)
        next
    }

    date = ""

    while ((getline line < path) > 0) {
        split(line, fields, ",")

        if (date == "" && date_col)
            date = substr(fields[date_col], 1, 10)

        speed = fields[speed_col] + 0
        rpm = fields[rpm_col] + 0
        voltage = fields[voltage_col] + 0

        if (speed > max_speed) max_speed = speed
        if (rpm > max_rpm) max_rpm = rpm

        if (voltage > 0) {
            if (voltage < min_voltage) min_voltage = voltage
            if (voltage > max_voltage) max_voltage = voltage
        }
    }
    close(path)

    if (min_voltage == 1e9)
        min_voltage = 0

    count++
    trip[count] = $(col["id"])
    trip_date[count] = date
    dist[count] = distance
    dur[count] = duration
    avg_speed[count] = duration > 0 ? distance * 3600 / duration : 0
    fuel[count] = distance > 0 ? liters * 100 / distance : 0
    top_speed[count] = max_speed
    top_rpm[count] = max_rpm
    low_voltage[count] = min_voltage
    high_voltage[count] = max_voltage
}

function by_sort(a, va, b, vb) {
    if (sort == "date" || sort == "date_asc") {
        if (trip_date[a] != trip_date[b])
            return sort == "date" \
                ? (trip_date[a] > trip_date[b] ? -1 : 1) \
                : (trip_date[a] < trip_date[b] ? -1 : 1)
    } else if (sort == "distance" || sort == "distance_asc") {
        if (dist[a] != dist[b])
            return sort == "distance" \
                ? (dist[a] > dist[b] ? -1 : 1) \
                : (dist[a] < dist[b] ? -1 : 1)
    } else if (sort == "duration" || sort == "duration_asc") {
        if (dur[a] != dur[b])
            return sort == "duration" \
                ? (dur[a] > dur[b] ? -1 : 1) \
                : (dur[a] < dur[b] ? -1 : 1)
    } else if (sort == "fuel" || sort == "fuel_asc") {
        if (fuel[a] != fuel[b])
            return sort == "fuel" \
                ? (fuel[a] > fuel[b] ? -1 : 1) \
                : (fuel[a] < fuel[b] ? -1 : 1)
    } else {
        if (top_speed[a] != top_speed[b])
            return top_speed[a] > top_speed[b] ? -1 : 1
    }

    return a < b ? -1 : (a > b ? 1 : 0)
}

END {
    n = asorti(trip, order, "by_sort")

    printf "%-10s %-23s %10s %9s %10s %12s %10s %10s %10s\n", \
           "Date", "Trip ID", "Distance", "Duration", "Avg km/h", \
           "Fuel L/100km", "Max km/h", "Max RPM", "Battery V min/max"

    for (i = 1; i <= n; i++) {
        j = order[i]
        seconds = dur[j]
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        secs = int(seconds % 60)
        duration_text = sprintf("%02d:%02d:%02d", hours, minutes, secs)

        printf "%-10s %-23s %10.3f %9s %10.1f %12.2f %10.1f %10.0f %5.1f / %5.1f\n", \
                  trip_date[j], trip[j], dist[j], duration_text, avg_speed[j], fuel[j], \
                  top_speed[j], top_rpm[j], low_voltage[j], high_voltage[j]
    }
}
