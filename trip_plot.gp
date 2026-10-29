set datafile separator ","
set datafile columnheaders
set terminal pngcairo size 1600,1000 enhanced font "sans,10"
set output "trip_plot.png"

set xdata time
set timefmt "%Y-%m-%dT%H:%M:%S"
set format x "%H:%M"
set xlabel "Time"
set grid
set key outside
set multiplot layout 5,1 title "Aprilia Trip Telemetry"

set ylabel "Speed (km/h)"
plot ARG1 using (timecolumn(1,"%Y-%m-%dT%H:%M:%S")):3 \
    with lines lw 1.5 title "Speed"

set ylabel "RPM"
plot ARG1 using (timecolumn(1,"%Y-%m-%dT%H:%M:%S")):4 \
    with lines lw 1.2 title "Engine RPM"

set ylabel "Speed (km/h)"
set y2label "Engine RPM"
set y2tics
set ytics nomirror

plot ARG1 using (timecolumn(1,"%Y-%m-%dT%H:%M:%S")):3 \
    with lines lw 1.5 title "Speed (km/h)", \
    ARG1 using (timecolumn(1,"%Y-%m-%dT%H:%M:%S")):4 axes x1y2 \
    with lines lw 1.2 title "RPM"

unset y2tics
unset y2label

set ylabel "Battery (V)"
plot ARG1 using (timecolumn(1,"%Y-%m-%dT%H:%M:%S")):11 \
    with lines lw 1.5 title "Battery voltage", \
    12 with lines dt 2 title "12 V reference"

set ylabel "Distance (km)"
plot ARG1 using (timecolumn(1,"%Y-%m-%dT%H:%M:%S")):2 \
    with lines lw 1.5 title "Distance"

unset multiplot
unset output
