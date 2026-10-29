function epoch_seconds(ts,    y, mo, d, h, mi, s, offset, sign, oh, om, t) {
    y  = substr(ts, 1, 4)
    mo = substr(ts, 6, 2)
    d  = substr(ts, 9, 2)
    h  = substr(ts, 12, 2)
    mi = substr(ts, 15, 2)
    s  = substr(ts, 18, 2)

    t = mktime(y " " mo " " d " " h " " mi " " s)

    offset = substr(ts, 24, 5)
    sign = substr(offset, 1, 1)
    oh = substr(offset, 2, 2)
    om = substr(offset, 4, 2)

    if (sign == "+")
        t -= oh * 3600 + om * 60
    else if (sign == "-")
        t += oh * 3600 + om * 60

    return t
}

function reset_trip() {
    rows = 0
    distance_start = 0
    distance = 0
    moving_seconds = 0
    max_speed = 0
    max_rpm = 0
    min_voltage = 0
    max_voltage = 0
    first_epoch = 0
    last_epoch = 0
    previous_epoch = 0
    previous_speed = 0
    avg_kml = 0
    fuel_level = 0
    start_time = ""
    end_time = ""
}

function print_duration(label, seconds,    h, m, s) {
    h = int(seconds / 3600)
    m = int(seconds % 3600 / 60)
    s = int(seconds % 60)
    printf "%s: %02d:%02d:%02d\n", label, h, m, s
}

function accumulate_trip(    duration) {
    trip_distance = distance - distance_start
    duration = last_epoch - first_epoch

    if (rows < 2 || duration <= 0)
        return

    if (multi_file && trip_distance <= 1)
        return

    trips++
    total_distance += trip_distance
    total_duration += duration
    total_moving += moving_seconds

    if (avg_kml > 0 && trip_distance > 0) {
        fuel_distance += trip_distance
        fuel_used_estimate += trip_distance / avg_kml
    }

    if (max_speed > overall_max_speed)
        overall_max_speed = max_speed

    if (max_rpm > overall_max_rpm)
        overall_max_rpm = max_rpm

    if (min_voltage > 0 &&
        (overall_min_voltage == 0 || min_voltage < overall_min_voltage))
        overall_min_voltage = min_voltage

    if (max_voltage > overall_max_voltage)
        overall_max_voltage = max_voltage

    if (!multi_file) {
        print "Trip: " FILENAME
        printf "Start: %s\nEnd:   %s\n", start_time, end_time
        printf "Distance: %.3f km\n", trip_distance
        print_duration("Duration", duration)

        if (duration > 0)
            printf "Average speed: %.1f km/h\n", \
                trip_distance / (duration / 3600)

        print_duration("Moving time", moving_seconds)
        print_duration("Stationary time", duration - moving_seconds)

        if (moving_seconds > 0)
            printf "Moving average speed: %.1f km/h\n", \
                trip_distance / (moving_seconds / 3600)
        else
            print "Moving average speed: unavailable"

        if (avg_kml > 0)
            printf "Average fuel consumption: %.2f L/100 km\n", \
                100 / avg_kml
        else
            print "Average fuel consumption: unavailable"

        printf "Final fuel tank level: %.0f\n", fuel_level
        printf "Maximum speed: %.1f km/h\n", max_speed
        printf "Maximum RPM: %.0f\n", max_rpm

        if (min_voltage > 0)
            printf "Minimum battery voltage: %.2f V\n", min_voltage
        else
            print "Minimum battery voltage: unavailable"

        if (max_voltage > 0)
            printf "Maximum battery voltage: %.2f V\n", max_voltage
        else
            print "Maximum battery voltage: unavailable"
    }
}

BEGIN {
    FS = ","
    multi_file = (ARGC > 2)
    reset_trip()
}

FNR == 1 {
    if (NR > 1)
        accumulate_trip()

    reset_trip()
    delete col

    for (i = 1; i <= NF; i++)
        col[$i] = i

    next
}

{
    if (!("timestamp_local" in col))
        next

    timestamp = $(col["timestamp_local"])
    current_epoch = epoch_seconds(timestamp)
    speed = $(col["speed"])
    rpm = $(col["rpm"])
    voltage = $(col["batteryVoltage"])

    if (rows == 0) {
        start_time = timestamp
        first_epoch = current_epoch
        distance_start = $(col["distance"])
    } else {
        interval = current_epoch - previous_epoch

        if (interval > 0 && previous_speed > 0)
            moving_seconds += interval
    }

    previous_epoch = current_epoch
    previous_speed = speed

    end_time = timestamp
    last_epoch = current_epoch
    distance = $(col["distance"])
    avg_kml = $(col["avg_consumption"])
    fuel_level = $(col["fuelLevel"])

    if (speed > max_speed)
        max_speed = speed

    if (rpm > max_rpm)
        max_rpm = rpm

    if (voltage > 0) {
        if (min_voltage == 0 || voltage < min_voltage)
            min_voltage = voltage
        if (voltage > max_voltage)
            max_voltage = voltage
    }

    rows++
}

END {
    accumulate_trip()

    if (!multi_file)
        exit

    if (trips == 0) {
        print "No trips longer than 1 km found."
        exit
    }

    print "Combined trip statistics (trips > 1 km)"
    print "----------------------------------------"
    printf "Qualifying trips: %d\n", trips
    printf "Total distance: %.3f km\n", total_distance
    print_duration("Total duration", total_duration)
    printf "Overall average speed: %.1f km/h\n", \
        total_distance / (total_duration / 3600)

    print_duration("Moving time", total_moving)
    print_duration("Stationary time", total_duration - total_moving)

    if (total_moving > 0)
        printf "Moving average speed: %.1f km/h\n", \
            total_distance / (total_moving / 3600)
    else
        print "Moving average speed: unavailable"

    if (fuel_distance > 0)
        printf "Average fuel consumption: %.2f L/100 km\n", \
            100 * fuel_used_estimate / fuel_distance
    else
        print "Average fuel consumption: unavailable"

    printf "Maximum speed: %.1f km/h\n", overall_max_speed
    printf "Maximum RPM: %.0f\n", overall_max_rpm

    if (overall_min_voltage > 0)
        printf "Minimum battery voltage: %.2f V\n", overall_min_voltage
    else
        print "Minimum battery voltage: unavailable"

    if (overall_max_voltage > 0)
        printf "Maximum battery voltage: %.2f V\n", overall_max_voltage
    else
        print "Maximum battery voltage: unavailable"
}
