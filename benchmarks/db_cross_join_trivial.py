from UTIL import shared

'''
# HyCC db_cross_join_trivial
size_t cross_join_trivial(DT *OUTPUT_db, DT *a, DT *b) {
    size_t id_a = 0;
    size_t id_b = 0;
    size_t id_out = 0;
    
    for(int i = 0; i < LEN_A*LEN_B*ATT+1; i++) {
        OUTPUT_db[i] = 0;//-1;
        }
    
    for(int i = 0; i < LEN_A; i++) {
        for(int j = 0; j < LEN_B; j++) {
            if(a[i*ATT_A] == b[j*ATT_B]) {
                id_out++;
                OUTPUT_db[(i*LEN_B+j)*ATT] = a[i*ATT_A];
                OUTPUT_db[(i*LEN_B+j)*ATT+1] = a[i*ATT_A+1];
                OUTPUT_db[(i*LEN_B+j)*ATT+2] = b[j*ATT_B+1];
                }
            }
        }
    
    return id_out;
}
'''

#requires len(A) == Len_A*2, len(B) == Len_B*2, len(res) == Len_A*Len_B*3
def db_cross_join_trivial(A: shared[list[int]], Len_A: int, B: shared[list[int]], Len_B: int, res : shared[list[int]]) -> (shared[list[int]],int):
    count = 0;
    for i in range(0, Len_A):
        for j in range(0, Len_B):
            for k in range(0, 3):
                v = 0;
                if A[i * 2] == B[j * 2]:
                    count = count + 1;
                    if k == 0:
                        v = A[i*2]
                    if k == 1:
                        v = A[i*2+1]
                    if k == 2:
                        v = B[j*2+1]
                res[(i*Len_B+j)*3+k] = v 
    return (res,count)

# Ana: DOUNBLE CHECK! I don't quite understand this
A = [1,2,3,4,5,6,7,8,9,10]
B = [1,9,8,4,5,5,4,3,2,1]
Len_A = 5
Len_B = 5
res = [0]*(Len_A*Len_B*3)
print(db_cross_join_trivial(A,Len_A,B,Len_B,res))
