// SPDX-License-Identifier: MIT
// Bounded launch metadata only. No CUDA parameters, memory or machine code.
#include <windows.h>
#include <cupti.h>
#include <cupti_activity.h>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <fcntl.h>
#include <io.h>
#include <malloc.h>
#include <mutex>
#include <string>
#include <thread>

namespace {
struct State {
    FILE* file = nullptr;
    std::mutex lock;
    std::atomic<unsigned long long> kernels{0}, dropped{0}, errors{0};
    unsigned seconds = 60;
    ULONGLONG beginTick = 0;
};
State* state = nullptr; // Deliberately lives until process exit; no CUDA calls in DllMain.
std::atomic<bool> initialized{false};
std::string quoted(const char* text) {
    std::string out = "\"";
    if (text) for (const unsigned char* p = (const unsigned char*)text; *p; ++p) {
        unsigned char c = *p;
        if (c == '"' || c == '\\') { out += '\\'; out += (char)c; }
        else if (c < 32) { char b[7]; sprintf_s(b, "\\u%04x", (unsigned)c); out += b; }
        else out += (char)c;
    }
    return out + '"';
}
void error(const char* where, CUptiResult result) {
    if (!state || result == CUPTI_SUCCESS) return;
    state->errors++;
    const char* message = nullptr;
    cuptiGetResultString(result, &message);
    std::lock_guard<std::mutex> hold(state->lock);
    fprintf(state->file, "{\"event\":\"error\",\"where\":%s,\"result\":%u,\"message\":%s}\n",
            quoted(where).c_str(), (unsigned)result, quoted(message).c_str());
    fflush(state->file);
}
void CUPTIAPI requested(uint8_t** buffer, size_t* size, size_t* maxRecords) {
    *size = 4 * 1024 * 1024;
    *buffer = (uint8_t*)_aligned_malloc(*size, 8);
    *maxRecords = 0;
    if (!*buffer) { *size = 0; if (state) state->errors++; }
}
void CUPTIAPI completed(CUcontext context, uint32_t stream,
                       uint8_t* buffer, size_t, size_t valid) {
    if (!state) { _aligned_free(buffer); return; }
    CUpti_Activity* record = nullptr;
    CUptiResult rc = CUPTI_SUCCESS;
    {
        std::lock_guard<std::mutex> hold(state->lock);
        while ((rc = cuptiActivityGetNextRecord(buffer, valid, &record)) == CUPTI_SUCCESS) {
            if (record->kind != CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL &&
                record->kind != CUPTI_ACTIVITY_KIND_KERNEL) continue;
            const auto* k = (const CUpti_ActivityKernel11*)record;
            auto count = ++state->kernels;
            if (count > 200000) { state->errors++; continue; }
            fprintf(state->file,
                "{\"event\":\"kernel\",\"name\":%s,\"start_ns\":%llu,\"end_ns\":%llu,"
                "\"device\":%u,\"context\":%u,\"stream\":%u,\"correlation\":%u,"
                "\"grid\":[%d,%d,%d],\"block\":[%d,%d,%d]}\n",
                quoted(k->name).c_str(), (unsigned long long)k->start,
                (unsigned long long)k->end, k->deviceId, k->contextId,
                k->streamId, k->correlationId, k->gridX, k->gridY, k->gridZ,
                k->blockX, k->blockY, k->blockZ);
        }
        fflush(state->file);
    }
    if (rc != CUPTI_ERROR_MAX_LIMIT_REACHED) error("get_record", rc);
    size_t lost = 0;
    rc = cuptiActivityGetNumDroppedRecords(context, stream, &lost);
    if (rc != CUPTI_SUCCESS) error("dropped_records", rc);
    if (lost) {
        state->dropped += lost;
        std::lock_guard<std::mutex> hold(state->lock);
        fprintf(state->file, "{\"event\":\"dropped\",\"count\":%zu}\n", lost);
        fflush(state->file);
    }
    _aligned_free(buffer);
}
void worker() {
    for (;;) {
        Sleep(2000);
        auto elapsed = GetTickCount64() - state->beginTick;
        if (elapsed >= (ULONGLONG)state->seconds * 1000 || state->kernels > 200000) break;
        error("periodic_flush", cuptiActivityFlushAll(0));
        uint64_t stamp = 0;
        error("timestamp", cuptiGetTimestamp(&stamp));
        std::lock_guard<std::mutex> hold(state->lock);
        fprintf(state->file, "{\"event\":\"heartbeat\",\"cupti_ns\":%llu,"
                "\"kernels\":%llu,\"dropped\":%llu}\n",
                (unsigned long long)stamp, state->kernels.load(), state->dropped.load());
        fflush(state->file);
    }
    error("disable", cuptiActivityDisable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL));
    error("final_flush", cuptiActivityFlushAll(CUPTI_ACTIVITY_FLAG_FLUSH_FORCED));
    uint64_t stamp = 0;
    error("end_timestamp", cuptiGetTimestamp(&stamp));
    std::lock_guard<std::mutex> hold(state->lock);
    fprintf(state->file, "{\"event\":\"trace_end\",\"cupti_ns\":%llu,"
            "\"kernels\":%llu,\"dropped\":%llu,\"errors\":%llu}\n",
            (unsigned long long)stamp, state->kernels.load(),
            state->dropped.load(), state->errors.load());
    fflush(state->file);
    // Do not use atexit or CUDA calls during Windows DLL teardown.
    // Keep FILE/state allocated: CUPTI may still release a final empty buffer.
}
}
extern "C" __declspec(dllexport) int InitializeInjection(void) {
    if (initialized.exchange(true)) return 1;
    wchar_t file[32768], seconds[16];
    DWORD n = GetEnvironmentVariableW(L"SOAT_CUDA_TRACE_FILE", file, 32768);
    if (!n || n >= 32768) return 0;
    DWORD length = GetEnvironmentVariableW(L"SOAT_CUDA_TRACE_SECONDS", seconds, 16);
    if (!length || length >= 16) return 0;
    wchar_t* end = nullptr;
    unsigned long duration = wcstoul(seconds, &end, 10);
    if (!end || *end || duration < 10 || duration > 180) return 0;
    HANDLE handle = CreateFileW(file, GENERIC_WRITE, FILE_SHARE_READ,
                                nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (handle == INVALID_HANDLE_VALUE) return 0;
    int fd = _open_osfhandle((intptr_t)handle, _O_WRONLY | _O_BINARY);
    if (fd < 0) { CloseHandle(handle); return 0; }
    FILE* output = _fdopen(fd, "wb");
    if (!output) { _close(fd); return 0; }
    state = new State;
    state->file = output;
    state->seconds = (unsigned)duration;
    state->beginTick = GetTickCount64();
    uint64_t timestamp = 0;
    CUptiResult rc = cuptiGetTimestamp(&timestamp);
    if (rc != CUPTI_SUCCESS) { error("initial_timestamp", rc); return 0; }
    FILETIME ft;
    GetSystemTimePreciseAsFileTime(&ft);
    ULARGE_INTEGER ticks; ticks.LowPart = ft.dwLowDateTime; ticks.HighPart = ft.dwHighDateTime;
    unsigned long long unixNs = (ticks.QuadPart - 116444736000000000ULL) * 100;
    fprintf(output, "{\"event\":\"trace_start\",\"schema\":\"soat-cupti-launch-v1\","
            "\"cupti_ns\":%llu,\"unix_ns\":%llu,\"pid\":%lu,\"seconds\":%u,"
            "\"scope\":\"kernel launch metadata; no parameters or code\"}\n",
            (unsigned long long)timestamp, unixNs, GetCurrentProcessId(), state->seconds);
    fflush(output);
    rc = cuptiActivityRegisterCallbacks(requested, completed);
    if (rc != CUPTI_SUCCESS) { error("register", rc); return 0; }
    rc = cuptiActivityEnable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL);
    if (rc != CUPTI_SUCCESS) { error("enable", rc); return 0; }
    try { std::thread(worker).detach(); }
    catch (...) {
        state->errors++;
        error("disable_after_thread_failure", cuptiActivityDisable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL));
        return 0;
    }
    return 1;
}
