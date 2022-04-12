DATA_FILE=ARG1
GRAPH_FILE=ARG2
GRAPH_TITLE=ARG3
Y_LABEL=ARG4

#set terminal wxt size 800,600 enhanced font 'Verdana,10' persist
set terminal pngcairo size 1200,600 enhanced #font 'Verdana,10'
set output GRAPH_FILE
set title GRAPH_TITLE noenhanced
set autoscale
set logscale y
set key autotitle columnhead
set ylabel sprintf("%s (Log Scale)", Y_LABEL)
set xlabel 'Input Size'
set y2label 'Improvement (number of times)'
set ytics nomirror
set y2tics nomirror

set style data histogram
set style histogram cluster gap 1
set style fill solid border -1
set boxwidth 0.9
set xtic rotate by -45 scale 0
plot DATA_FILE using 3:xtic(2), DATA_FILE using 4:xtic(2), DATA_FILE using 5:xtic(2), DATA_FILE using 6:xtic(2), DATA_FILE using 7:xtic(2) axes x1y2 lw 2 with lines, DATA_FILE using 8:xtic(2) axes x1y2 lw 2 with lines

#pause -1
