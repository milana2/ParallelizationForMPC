from UTIL import shared

'''
void max_pooling(DT *vals, DT *OUTPUT_res, unsigned cols, unsigned rows) {
    unsigned rows_res = rows / 2;
    unsigned cols_res = cols / 2;
    for(unsigned i = 0; i < rows_res; i++) {
        for(unsigned j = 0; j < cols_res; j++) {
            unsigned x = j * 2;
            unsigned y = i * 2;
            DT max = vals[y*cols + x];
            if(vals[y*cols + x + 1] > max) {
                max = vals[y*cols + x + 1];
                }
            if(vals[(y + 1) *cols + x] > max) {
                max = vals[(y + 1) * cols + x];
                } 
            if(vals[(y + 1) *cols + x + 1] > max) {
                max = vals[(y + 1) * cols + x + 1];
                } 
            OUTPUT_res[i * cols_res + j] = max;
            }
        }
}
'''

# requires: len(vals) == cols*rows
# len(OUTPUT_res) = cols*rows/4
# cols%2 == 0, rows%2 == 0
def cryptonets_max_pooling(vals: shared[list[int]], cols: int, rows: int, OUTPUT_res: shared[list[int]]) -> shared[list[int]]:
    rows_res = int(rows/2);
    cols_res = int(cols/2);
    for i in range(rows_res):
        for j in range(cols_res):
            max = vals[i*2*cols+j*2];
            if vals[i*2*cols+j*2+1] > max:
                max = vals[i*2*cols+j*2+1]
            if vals[(i*2 + 1)*cols + j*2] > max:
                max = vals[(i*2 + 1) * cols + j*2]    
            if vals[(i*2 + 1)*cols + j*2 + 1] > max:                                                                                       
                max = vals[(i*2 + 1) * cols + j*2 + 1];
            OUTPUT_res[i * cols_res + j] = max;                                                                      
    return OUTPUT_res

cols = 10
rows = 8
vals = [i+2 for i in range(rows*cols)]
output_size = int(cols*rows/4)
OUTPUT_res = [0]*output_size
print(cryptonets_max_pooling(vals, cols, rows, OUTPUT_res))





