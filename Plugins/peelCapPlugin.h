// PluginInterface.h
#ifndef PEEL_PLUGININTERFACE_H
#define PEEL_PLUGININTERFACE_H

#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <map>

#ifdef PEEL_PLUGIN_EXPORTS
#define PEEL_PLUGIN_API __declspec(dllexport)
#else
#define PEEL_PLUGIN_API __declspec(dllimport)
#endif

#pragma once

typedef void (*TimecodeFunc)(void*, int, int, int, int, float, bool);
typedef void (*StateFunc)(void*, const char*, const char*);
typedef void (*SubjectFunc)(void*, const char**);
typedef void (*LogFunc)(void*, const char*);

struct PluginCallbacks
{
    StateFunc state;
    TimecodeFunc timecode;
    SubjectFunc subject;
    LogFunc log;
};

/* plugins must implement:

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface* createPlugin() {
    return new MyPlugin();
}

extern "C" PEEL_PLUGIN_API void getIdentifier(char *buf, size_t len) {
    snprintf(buf, len, "MyDevice");
}

}

*/

class PEEL_PLUGIN_API PeelCapDeviceInterface {
public:
    PeelCapDeviceInterface() : cb({ nullptr, nullptr, nullptr }) {};
    virtual ~PeelCapDeviceInterface() {};

    // App modifying device
    virtual bool reconfigure(const char*) = 0;
    virtual void teardown() = 0;
    virtual bool command(const char*, const char*) = 0;
    virtual void setEnabled(bool) = 0;
    virtual bool getEnabled() = 0;
    virtual const char* getInfo() = 0;
    virtual const char* getState() = 0;
    virtual const char* pluginCommand(const char *) = 0;

    // Device updating app state
    PluginCallbacks cb;
    void setFunctions(PluginCallbacks funcs) {
        cb = funcs;
    }

    // Send up an status update to the app
    void updateState(const char* state, const char* info) {
        if (cb.state)
            cb.state(this, state, info);
    }

    // Send a timecode value to the app
    void timecode(int h, int m, int s, int f, float fps, bool isDrop) {
        if (cb.timecode)
            cb.timecode(this, h, m, s, f, fps, isDrop);
    };

    // Send current subjects to the app
    void subjects(const char** subjects) {
        if (cb.subject) {
            cb.subject(this, subjects);
        }
    }

    // Log a message to the app
    void logMessage(const char* msg) {
        if (cb.log) {
            cb.log(this, msg);
        }
    }
};

typedef PeelCapDeviceInterface* (__cdecl* plugin_entry_ptr)();
typedef const char* (__cdecl* plugin_identifier_ptr)();

#endif