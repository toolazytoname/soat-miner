// Small, bounded live-yield stimulus: one 8 MiB memset, then idle context.
#include <cuda_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <thread>
#ifdef _WIN32
#include <process.h>
#define PID _getpid()
#else
#include <unistd.h>
#define PID getpid()
#endif
int main(int argc,char** argv) {
 const int seconds=argc>1?std::atoi(argv[1]):20;
 if(seconds<5||seconds>30){std::fprintf(stderr,"Context hold must be 5..30 seconds\n");return 2;}
 void* buffer=nullptr;
 if(cudaSetDevice(0)!=cudaSuccess||cudaMalloc(&buffer,8*1024*1024)!=cudaSuccess)return 1;
 if(cudaMemset(buffer,0,8*1024*1024)!=cudaSuccess||cudaDeviceSynchronize()!=cudaSuccess){cudaFree(buffer);return 1;}
 std::printf("{\"pid\":%d,\"context_active\":true,\"allocated_bytes\":8388608,\"idle_seconds\":%d}\n",(int)PID,seconds);std::fflush(stdout);
 std::this_thread::sleep_for(std::chrono::seconds(seconds));
 const auto error=cudaFree(buffer);
 std::printf("{\"pid\":%d,\"context_released\":true}\n",(int)PID);std::fflush(stdout);
 return error==cudaSuccess?0:1;
}
