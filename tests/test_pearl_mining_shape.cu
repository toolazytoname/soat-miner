// Validate complete transcript buffers at the actual Pearl K/rank.
// The upstream dbuf kernel is an independent, synchronous staging oracle.
// The old test accepted a K64 argument but always launched K32. Every selected
// variant below now maps to its actual template and reports that selection.
#include <cuda_runtime.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>
#include "algos/pearl-pow/noisy_gemm.cuh"
#include "algos/pearl-pow/prepare.cuh"
using namespace om::pearl;
#define CK(x) do { const cudaError_t e=(x); if(e!=cudaSuccess) { \
    fprintf(stderr,"CUDA %s at line %d\n",cudaGetErrorString(e),__LINE__);return 1; } } while(0)

template<int WM,int WN,int TM,int TN,int KB,int ST=3,int GM=8,int MIN=1,bool FIX=false,bool SINGLE=false>
cudaError_t launch(const int8_t* a,const int8_t* bn,uint32_t* tr,int m,int n,int k,int rank) {
    constexpr int bm=WM*TM*16,bnSize=WN*TN*16;
    constexpr int shared=ST*(bm+bnSize)*(KB+16);
    cudaError_t e=cudaFuncSetAttribute(noisyGemmPtx<WM,WN,TM,TN,KB,ST,GM,MIN,FIX,SINGLE>,
        cudaFuncAttributeMaxDynamicSharedMemorySize,shared);
    if(e!=cudaSuccess)return e;
    noisyGemmPtx<WM,WN,TM,TN,KB,ST,GM,MIN,FIX,SINGLE><<<dim3(n/bnSize,m/bm),WM*WN*32,shared>>>(
        a,bn,nullptr,tr,m,n,k,rank,false);
    return cudaGetLastError();
}

int main(int argc,char** argv) {
    const int m=argc>1?atoi(argv[1]):1024,n=argc>2?atoi(argv[2]):1024;
    const int k=argc>3?atoi(argv[3]):2048,rank=argc>4?atoi(argv[4]):128;
    const char* which=argc>5?argv[5]:"ptx";
    const int kb=argc>6?atoi(argv[6]):64;
    const bool ptx=!strcmp(which,"ptx"),async=!strcmp(which,"async");
    const bool s2g8=!strcmp(which,"ampere-s2-g8"),s2g4=!strcmp(which,"ampere-s2-g4");
    const bool s3g4=!strcmp(which,"ampere-s3-g4");
    const bool sm64s2=!strcmp(which,"sm86-m64n128-s2-k64"),sm64s3=!strcmp(which,"sm86-m64n128-s3-k64");
    const bool sm128s2=!strcmp(which,"sm86-m128n64-s2-k64"),sm64k32=!strcmp(which,"sm86-m64n128-s2-k32");
    const bool b3k64=!strcmp(which,"sm86-m64n128-s2-k64-b3"),b3k32=!strcmp(which,"sm86-m64n128-s2-k32-b3");
    const bool fixed=!strcmp(which,"sm86-fixed-s2-g8-k64"),fixedB3=!strcmp(which,"sm86-fixed-m64n128-b3-k64");
    const bool single=!strcmp(which,"sm86-singlefold-s2-g8-k64"),singleB3=!strcmp(which,"sm86-singlefold-m64n128-b3-k64");
    const bool large2=!strcmp(which,"sm86-large-s2-k64"),large2fold=!strcmp(which,"sm86-large-s2-fold-k64"),large3fold=!strcmp(which,"sm86-large-s3-fold-k64");
    if(m<=0||n<=0||m>8192||n>65536||m%256||n%256||k!=2048||rank!=128||
       !(ptx||async||s2g8||s2g4||s3g4||sm64s2||sm64s3||sm128s2||sm64k32||b3k64||b3k32||fixed||fixedB3||single||singleB3||large2||large2fold||large3fold)||(ptx&&kb!=32&&kb!=64)) {
        fprintf(stderr,"Expected M,N positive multiples of 256 (M<=8192,N<=65536), K=2048 rank=128; variant ptx [32|64], async, ampere-s[2|3]-g[4|8] or sm86-m{64n128|128n64}-s{2|3}-k{32|64}.\n");
        return 2;
    }
    const size_t aBytes=(size_t)m*k,bBytes=(size_t)k*n,tiles=(size_t)(m/16)*(n/16);
    int8_t *a=nullptr,*bk=nullptr,*bn=nullptr;uint32_t *reference=nullptr,*actual=nullptr;
    CK(cudaMalloc(&a,aBytes));CK(cudaMalloc(&bk,bBytes));CK(cudaMalloc(&bn,bBytes));
    CK(cudaMalloc(&reference,tiles*16*4));CK(cudaMalloc(&actual,tiles*16*4));
    genMatrix<<<(aBytes/8+255)/256,256>>>(a,aBytes,11);
    genMatrix<<<(bBytes/8+255)/256,256>>>(bk,bBytes,22);
    CK(cudaGetLastError());CK(cudaDeviceSynchronize());
    std::vector<int8_t> hostBk(bBytes),hostBn(bBytes);
    CK(cudaMemcpy(hostBk.data(),bk,bBytes,cudaMemcpyDeviceToHost));
    for(int j=0;j<n;j++)for(int q=0;q<k;q++)hostBn[(size_t)j*k+q]=hostBk[(size_t)q*n+j];
    CK(cudaMemcpy(bn,hostBn.data(),bBytes,cudaMemcpyHostToDevice));
    CK(cudaMemset(reference,0,tiles*16*4));CK(cudaMemset(actual,0,tiles*16*4));
    noisyGemmMmaTiledDB<2,4,4,2><<<dim3(n/128,m/128),256>>>(a,bk,nullptr,reference,m,n,k,rank,false);
    CK(cudaGetLastError());CK(cudaDeviceSynchronize());
    if(async) {
        noisyGemmMmaTiledAsync<2,4,4,4><<<dim3(n/256,m/128),256>>>(a,bk,nullptr,actual,m,n,k,rank,false);
        CK(cudaGetLastError());
    } else if(s2g8) { CK((launch<2,4,4,2,64,2,8>(a,bn,actual,m,n,k,rank)));
    } else if(s2g4) { CK((launch<2,4,4,2,64,2,4>(a,bn,actual,m,n,k,rank)));
    } else if(s3g4) { CK((launch<2,4,4,2,64,3,4>(a,bn,actual,m,n,k,rank)));
    } else if(sm64s2) { CK((launch<2,4,2,2,64,2,8>(a,bn,actual,m,n,k,rank)));
    } else if(sm64s3) { CK((launch<2,4,2,2,64,3,8>(a,bn,actual,m,n,k,rank)));
    } else if(sm128s2) { CK((launch<4,2,2,2,64,2,8>(a,bn,actual,m,n,k,rank)));
    } else if(sm64k32) { CK((launch<2,4,2,2,32,2,8>(a,bn,actual,m,n,k,rank)));
    } else if(b3k64) { CK((launch<2,4,2,2,64,2,8,3>(a,bn,actual,m,n,k,rank)));
    } else if(b3k32) { CK((launch<2,4,2,2,32,2,8,3>(a,bn,actual,m,n,k,rank)));
    } else if(fixed) { CK((launch<2,4,4,2,64,2,8,1,true>(a,bn,actual,m,n,k,rank)));
    } else if(fixedB3) { CK((launch<2,4,2,2,64,2,8,3,true>(a,bn,actual,m,n,k,rank)));
    } else if(single) { CK((launch<2,4,4,2,64,2,8,1,true,true>(a,bn,actual,m,n,k,rank)));
    } else if(singleB3) { CK((launch<2,4,2,2,64,2,8,3,true,true>(a,bn,actual,m,n,k,rank)));
    } else if(large2) { CK((launch<4,4,4,2,64,2,8,1,true,false>(a,bn,actual,m,n,k,rank)));
    } else if(large2fold) { CK((launch<4,4,4,2,64,2,8,1,true,true>(a,bn,actual,m,n,k,rank)));
    } else if(large3fold) { CK((launch<4,4,4,2,64,3,8,1,true,true>(a,bn,actual,m,n,k,rank)));
    } else if(kb==64) { CK((launch<4,4,4,2,64>(a,bn,actual,m,n,k,rank)));
    } else { CK((launch<4,4,4,2,32>(a,bn,actual,m,n,k,rank))); }
    CK(cudaDeviceSynchronize());
    std::vector<uint32_t> want(tiles*16),got(tiles*16);
    CK(cudaMemcpy(want.data(),reference,tiles*16*4,cudaMemcpyDeviceToHost));
    CK(cudaMemcpy(got.data(),actual,tiles*16*4,cudaMemcpyDeviceToHost));
    size_t badTiles=0,badWords=0;int histogram[16]={};
    for(size_t t=0;t<tiles;t++) {
        bool bad=false;
        for(int w=0;w<16;w++)if(want[t*16+w]!=got[t*16+w]) {bad=true;badWords++;histogram[w]++;}
        if(bad)badTiles++;
    }
    printf("%s%s%s %dx%d k=%d rank=%d: %s (%zu/%zu tiles, %zu words differ)\n",
           which,ptx?" k":"",ptx?(kb==64?"64":"32"):"",m,n,k,rank,
           badTiles?"FAIL":"ok",badTiles,tiles,badWords);
    if(badTiles) {printf("per-word mismatches:");for(int w=0;w<16;w++)printf(" %d",histogram[w]);printf("\n");}
    CK(cudaFree(a));CK(cudaFree(bk));CK(cudaFree(bn));CK(cudaFree(reference));CK(cudaFree(actual));
    return badTiles?1:0;
}
