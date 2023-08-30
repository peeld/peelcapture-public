#include "peelCapPlugin.h"
#include "RemoteCaptury.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <sstream>
#include <iomanip>



class CapturyPlugin : public PeelCapDeviceInterface {
public:

    CapturyPlugin() : running(true) {
        frame = 0;
        host = "127.0.0.1";
        value = 0;
        enabled = false;
        recording = false;
        info[0] = 0;
    };

    ~CapturyPlugin() {
        running = false;
    }

    const char* device() { return "Captury"; };

    bool reconfigure(const char* value) override {
        if (value != nullptr)
        {
            this->host = value;
            strcpy_s(info, 255, value);
        }

        return true;
    }

    void teardown() override
    {
        running = false;
    };

    bool command(const char* name, const char* arg)
    {
        if (!enabled)
        {
            updateState("OFFLINE", info);
            return true;
        }

        if (strcmp(name, "record") == 0)
        {
            std::string sn = currentShotName + "_" + std::string(arg);
            int ress = Captury_setShotName(sn.c_str());
            if (ress != 0)
            {
                updateState("ONLINE", info);
                return true;
            }
            int res = Captury_startRecording();
            if (res > 0)
            {
                updateState("RECORDING", info);
                recording = true;
                return true;
            }
            
        }
        if (strcmp(name, "stop") == 0)
        {
            int res = Captury_stopRecording();
            if (res == 1)
            {
                updateState("ONLINE", info);
                recording = false;
                return true;
            }
        }
        if (strcmp(name, "shotName") == 0)
        {
            currentShotName = arg;
            return true;
        }

        return true;
    }

    void setEnabled(bool b) override {
        enabled = b;
        if (!enabled) {
            updateState("OFFLINE", info);
            Captury_disconnect();
        }
        else {
            int res = Captury_connect(host.c_str(), 2101);
            if (res != 0)
            {
                updateState("OFFLINE", info);
                return;
            }
            updateState("ONLINE", info);
        }
    }

    bool getEnabled() override {
        return enabled;
    }

    const char* getInfo() override
    {
        return info;
    }

    const char* getState() override
    {
        if (enabled)
            return "ONLINE";
        else
            return "OFFLINE";
    }

    const char* pluginCommand(const char* msg) override
    {
        std::ostringstream oss;
        oss << "Reply to " << msg;
        commandReply = oss.str();
        return commandReply.c_str();
    }


    char info[255];
    bool enabled;
    bool running;
    bool recording;
    size_t frame;
    std::string host;
    int value;
    std::string currentShotName;
    std::string commandReply;

};

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new CapturyPlugin();
}

extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "Captury";
}
