// PluginInterface.h
#ifndef PEEL_PLUGININTERFACE_H
#define PEEL_PLUGININTERFACE_H

#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <map>

#ifdef _WIN32
#ifdef PEEL_PLUGIN_EXPORTS
#define PEEL_PLUGIN_API __declspec(dllexport)
#else
#define PEEL_PLUGIN_API __declspec(dllimport)
#endif
#else
#define PEEL_PLUGIN_API
#endif

#pragma once


struct PluginCallbacks
{
    std::function<void(void*, int, int, int, int, float, bool)> timecode;
    std::function<void(void*, const char*, const char*)> state;
    std::function<void(void*, const char**, int)> subject;
    std::function<void(void*, const char**, int)> prop;
    std::function<void(void*, const char*)> log;
};

/* plugins must implement:

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface* createPlugin() {
    return new MyPlugin();
}

extern "C" PEEL_PLUGIN_API void getIdentifier(char *buf, size_t len) {
    snprintf(buf, len, "MyDevice");
}

*/

struct State
{
    std::string state;
    std::string info;
    bool enabled;
};


class PEEL_PLUGIN_API PeelCapDeviceInterface {
public:
    PeelCapDeviceInterface() 
        : cb({ nullptr, nullptr, nullptr }) 
        , states(new State)        
    {
    	states->enabled = true;
    };

    virtual ~PeelCapDeviceInterface() {
        delete states;
    };

    // App modifying device
    virtual bool reconfigure(const char*) = 0;
    virtual void teardown() = 0;
    virtual bool command(const char*, const char*) = 0;
    virtual void setEnabled(bool value) { this->states->enabled = value; }
    virtual bool getEnabled() { return this->states->enabled; }
    virtual const char* getInfo() { return this->states->info.c_str(); }
    virtual const char* getState() { return this->states->state.c_str(); }
    virtual void setState(const char* value) { this->states->state = value;  }
    virtual void setInfo(const char* value) { this->states->info = value;  }
    virtual const char* pluginCommand(const char *) = 0;

    // Device updating app state
    PluginCallbacks cb;
    void setFunctions(PluginCallbacks funcs) {
        cb = funcs;
    }

    // Send up an status update to the app
    void updateState(const char* state, const char* info) {
        this->states->state = state;
        this->states->info = info;
        if (cb.state)
            cb.state(this, state, info);
    }

    // Send a timecode value to the app
    void timecode(int h, int m, int s, int f, float fps, bool isDrop) {
        if (cb.timecode)
            cb.timecode(this, h, m, s, f, fps, isDrop);
    };

    // Send current subjects to the app
    void subjects(const char** subjects, int count) {
        if (cb.subject) {
            cb.subject(this, subjects, count);
        }
    }

    // Send current subjects to the app
    void props(const char** prop, int count) {
        if (cb.prop) {
            cb.prop(this, prop, count);
        }
    }

    // Log a message to the app
    void logMessage(const char* msg) {
        if (cb.log) {
            cb.log(this, msg);
        }
    }

private:
    State* states;

};

#ifdef _WIN32
typedef PeelCapDeviceInterface* (__cdecl* plugin_entry_ptr)();
typedef const char* (__cdecl* plugin_identifier_ptr)();
#else
typedef PeelCapDeviceInterface* (*plugin_entry_ptr)();
typedef const char* (*plugin_identifier_ptr)();

#endif


#endif
