#include "peelCapPlugin.h"

#pragma warning( disable : 4200)
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
        port = 2101;
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

        if (value == nullptr)
        {
            return false;
        }

        std::string stringValue(value);
        size_t pos = stringValue.find(':');
        if (pos != -1)
        {
            this->host = stringValue.substr(0, pos);
            this->port = atoi(stringValue.substr(pos + 1).c_str());
        }
        else
        {
            this->host = stringValue;
            this->port = 2101;
        }

        connectToCaptry();
        return true;
    }

    void connectToCaptry()
    {
        int res = Captury_connect(host.c_str(), port);

        if (res != 1)
        {
            updateState("ERROR", "Error Connecting");
        }

        const char* status =  Captury_getStatus();
        if (status == nullptr)
        {
            strcpy(info, "No Connection");
            updateState("ERROR", "No Connection");
        }
        else
        {
            updateState("ONLINE", status);
        }

    }

    void disonnectFromCaptury()
    {
        Captury_disconnect();
        updateState("OFFLINE", "");
    }

    void teardown() override
    {
        disonnectFromCaptury();
        running = false;
    };

    bool command(const char* name, const char* arg)
    {
        int res;

        if (!enabled)
        {
            updateState("OFFLINE", "");
            return true;
        }

        if (strcmp(name, "record") == 0)
        {
            std::string sn = currentShotName + "_" + std::string(arg);
            res = Captury_setShotName(sn.c_str());
            if (res != 0)
            {
                updateState("ONLINE", "");
                return true;
            }

            res = Captury_startRecording();
            if (res > 0)
            {
                updateState("RECORDING", "");
                recording = true;
            }            
            else
            {
                updateState("ERROR", "Could not record");
            }

            return true;
        }

        if (strcmp(name, "stop") == 0)
        {
            int res = Captury_stopRecording();
            if (res == 1)
            {
                updateState("ONLINE", "");
                recording = false;
            }
            else
            {
                updateState("ERROR", "Could not stop");
            }
            return true;
        }

        if (strcmp(name, "shotName") == 0)
        {
            currentShotName = arg;
        }

        return true;
    }

    void setEnabled(bool b) override {
        enabled = b;
        if (!enabled) {
            this->disonnectFromCaptury();            
        }
        else {
            this->connectToCaptry();

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
        if (!enabled)
            return "OFFLINE";

        const char* status = Captury_getStatus();
        if (status == nullptr)
        {
            return "ERROR";
        }
        else
        {
            strncpy(info, status, 255);
            return "ONLINE";
        }
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
    int port;
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
