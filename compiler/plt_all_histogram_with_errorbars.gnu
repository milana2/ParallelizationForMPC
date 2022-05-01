DATA_FILE=ARG1
GRAPH_FILE=ARG2
GRAPH_TITLE=ARG3
Y_LABEL=ARG4

set terminal epslatex size 7in,3.5in color colortext
#set terminal pngcairo size 1200,600 enhanced #font 'Verdana,10'
set output GRAPH_FILE
#set title GRAPH_TITLE noenhanced
set autoscale
set autoscale y
set key autotitle columnhead
set ylabel sprintf("%s", Y_LABEL)
set bmargin 7
# set xlabel 'Benchmark'
set y2label 'Improvement (number of times)'
set ytics nomirror
set y2tics nomirror
set key tmargin horizontal center

set style data histogram
set style histogram errorbars gap 1 lw 1
set style fill solid border -1
set boxwidth 0.9
set xtic rotate by -45 scale 0
plot DATA_FILE using 3:4:xtic(2), \
     DATA_FILE using 5:6:xtic(2), \
     DATA_FILE using 7:8:xtic(2), \
     DATA_FILE using 9:10:xtic(2), \
     DATA_FILE using 11:xtic(2) axes x1y2 lw 2 with lines, \
     DATA_FILE using 12:xtic(2) axes x1y2 lw 2 with lines

#pause -1
