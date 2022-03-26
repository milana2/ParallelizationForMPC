from UTIL import shared

'''
void convolution_naive(DT *image, DT* kernel, DT* OUTPUT_layer, unsigned image_width, unsigned window_size, unsigned stride, unsigned conv_width)
{
    unsigned window_unrolled = window_size * window_size;
    // Need to assign each input pixel to the convolution matrix
    unsigned x, y, wx=0, wy;
    for(y = 0; y < conv_width; y++) { // Inner position in the image
                                         for(x = 0; x < conv_width; x++) {
            unsigned oPos = x+y*conv_width;
            DT tmp = 0;
            for(wy = 0; wy < window_size; wy++) {
                #if WINDOW_WIDTH==5
                unsigned convPos = wx+wy*window_size;
                tmp += kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + 0)] + kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + 1)] + kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + 2)] + kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + 3)] + kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + 4)];
                #else 
                for(wx = 0; wx < window_size; wx++) {
                    unsigned convPos = wx+wy*window_size;
                    tmp += kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + wx)];
                    }
                #endif
                /*for(wx = 0; wx < window_size; wx++) {
                    unsigned convPos = wx+wy*window_size;
                    tmp += kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + wx)];
                    }*/
                }
            OUTPUT_layer[oPos] = tmp;
            }
                                         }
}
'''

def cryptonets_convolution_naive(
    image: shared[list[int]], kernel: shared[list[int]], OUTPUT_layer: shared[list[int]], image_width: int, window_size: int, stride: int, conv_width: int
) -> shared[list[int]]:
    # Need to assign each input pixel to the convolution matrix
    # unsigned x, y, wx=0, wy;
    for y in range(conv_width):  # Inner position in the image
       for x in range(conv_width):
            oPos = x+y*conv_width;
            tmp = 0;
            for wy in range(window_size):
                for wx in range(window_size):
                    convPos = wx+wy*window_size;
                    tmp += kernel[convPos] * image[(y*stride + wy) * image_width + (x*stride + wx)];
            OUTPUT_layer[oPos] = tmp;
    return OUTPUT_layer

#Parameters taken from the paper
#define IMAGE_WIDTH 28 // 28
#define WINDOW_WIDTH 5
#define STRIDE 2
#define OUTPUT_CHANNELS 5 // 5

#define IMAGE_CROP 13 // 13 with padding
#define SIZE_CONVOLUTION (IMAGE_CROP * IMAGE_CROP) // 169

#define FULLY_CONNECTED_WIDTH 100 // (7, 9)
#define FINAL_OUTPUT_CHANNELS 10

#convolution_naive(image, kernel, res, image_width, window_size, stride, conv_width);
#void convolution_naive_outputs(DT *image, DT* kernels, DT* OUTPUT_layer, unsigned image_width, unsigned window_size, unsigned output_size, unsigned stride, unsigned conv_width)
#DT convolution_layer[OUTPUT_CHANNELS * SIZE_CONVOLUTION];
#convolution_naive_outputs(convolution_input, INPUT_B.kernelsL1, convolution_layer, padded_width, WINDOW_WIDTH, OUTPUT_CHANNELS, STRIDE, IMAGE_CROP);
IMAGE_WIDTH = 28
padded_width = IMAGE_WIDTH + 2
WINDOW_WIDTH = 5
OUTPUT_CHANNELS = 5
STRIDE = 2
IMAGE_CROP = 13
SIZE_CONVOLUTION = IMAGE_CROP * IMAGE_CROP
convolution_layer = [0 for i in range(OUTPUT_CHANNELS * SIZE_CONVOLUTION)]
image = [i+2 for i in range(padded_width*padded_width)]
kernel = [1 for i in range(WINDOW_WIDTH*WINDOW_WIDTH)] 
print(cryptonets_convolution_naive(image,kernel,convolution_layer,padded_width,WINDOW_WIDTH,STRIDE,IMAGE_CROP))
