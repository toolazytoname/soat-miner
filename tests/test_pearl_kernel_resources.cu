// Read compiled resources and theoretical occupancy; no performance claim.
#include <cuda_runtime.h>
#include <stdio.h>
#include "algos/pearl-pow/noisy_gemm.cuh"
using namespace om::pearl;
#define CK(x) do {cudaError_t e=(x);if(e!=cudaSuccess){fprintf(stderr,"CUDA %s at %d\n",cudaGetErrorString(e),__LINE__);return 1;}}while(0)
template<int WM,int WN,int TM,int TN,int KB,int ST=3,int GM=8,int MIN=1,bool FIX=false,bool SINGLE=false,bool EARLY=false,bool STREAM=false,bool SCRATCH=false,bool FOLD=false,bool CACHEA=false,bool DEFER=false,bool UNROLL=false>
int report(const char* name,int maxThreads) {
    constexpr int threads=WM*WN*32,shared=ST*(WM*TM*16+WN*TN*16)*(KB+16);
    auto kernel=noisyGemmPtx<WM,WN,TM,TN,KB,ST,GM,MIN,FIX,SINGLE,EARLY,STREAM,SCRATCH,FOLD,CACHEA,DEFER,UNROLL>;
    CK(cudaFuncSetAttribute(kernel,cudaFuncAttributeMaxDynamicSharedMemorySize,shared));
    cudaFuncAttributes a{};CK(cudaFuncGetAttributes(&a,kernel));
    int blocks=0;CK(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&blocks,kernel,threads,shared));
    printf("{\"configuration\":\"%s\",\"threads\":%d,\"registers_per_thread\":%d,\"local_bytes_per_thread\":%zu,\"dynamic_shared_bytes\":%d,\"static_shared_bytes\":%zu,\"theoretical_blocks_per_sm\":%d,\"theoretical_occupancy_percent\":%.2f}\n",name,threads,a.numRegs,a.localSizeBytes,shared,a.sharedSizeBytes,blocks,100.0*blocks*threads/maxThreads);
    return 0;
}
int main() {
    CK(cudaSetDevice(0));cudaDeviceProp p{};CK(cudaGetDeviceProperties(&p,0));
    printf("{\"gpu\":\"%s\",\"sm_count\":%d,\"max_threads_per_sm\":%d,\"registers_per_sm\":%d,\"shared_bytes_per_sm\":%zu,\"l2_bytes\":%d}\n",p.name,p.multiProcessorCount,p.maxThreadsPerMultiProcessor,p.regsPerMultiprocessor,p.sharedMemPerMultiprocessor,p.l2CacheSize);
    if((report<4,4,4,2,32>("original-k32",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,4,4,2,64>("original-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,4,2,64,2,8>("sm86-s2-g8",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,4,2,64,2,4>("sm86-s2-g4",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,4,2,64,3,4>("sm86-s3-g4",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,64,2,8>("sm86-m64n128-s2-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,64,3,8>("sm86-m64n128-s3-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,2,2,64,2,8>("sm86-m128n64-s2-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,32,2,8>("sm86-m64n128-s2-k32",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,64,2,8,3>("sm86-m64n128-s2-k64-b3",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,32,2,8,3>("sm86-m64n128-s2-k32-b3",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,4,2,64,2,8,1,true>("sm86-fixed-s2-g8-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,64,2,8,3,true>("sm86-fixed-m64n128-b3-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,4,2,64,2,8,1,true,true>("sm86-singlefold-s2-g8-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,2,2,64,2,8,3,true,true>("sm86-singlefold-m64n128-b3-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,4,4,2,64,2,8,1,true,false>("sm86-large-s2-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,4,4,2,64,2,8,1,true,true>("sm86-large-s2-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,4,4,2,64,3,8,1,true,true>("sm86-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,4,4,2,64,2,8,1,true,true,true>("sm86-early-large-s2-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,4,4,2,64,3,8,1,true,true,true>("sm86-early-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,2,4,4,64,2,8,1,true,true>("sm86-warpwide-compact-s2-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true>("sm86-warpwide-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,false,false,true>("sm86-warpwide-scratch-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<2,4,4,4,64,3,8,1,true,true>("sm86-warpwide-n256-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,false,false,false,true>("sm86-warpwide-foldissue-large-s3-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,false,false,false,false,true>("sm86-warpwide-cachea-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,false,false,false,false,false,true>("sm86-warpwide-deferred-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,false,false,false,false,false,false,true>("sm86-warpwide-unrollcopy-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,false,true>("sm86-warpwide-streamb-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    if((report<4,2,4,4,64,3,8,1,true,true,true,false>("sm86-warpwide-early-large-s3-fold-k64",p.maxThreadsPerMultiProcessor)))return 1;
    return 0;
}
