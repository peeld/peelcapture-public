#include "peelCapPlugin.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <sstream>
#include <iomanip>



class MyPlugin : public PeelCapDeviceInterface {
public:

    MyPlugin() : running(false) {
        myThread = std::make_shared<std::thread>(&MyPlugin::loop, this);
        frame = 0;
        host = "127.0.0.1";
        value = 0;
        enabled = false;
        recording = false;
        info[0] = 0;
    };

    ~MyPlugin() {
        running = false;
        myThread->join();
    }

    const char* device() { return "MyDevice"; };

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
            frame += 4000;
            recording = true;
            updateState("RECORDING", info);
        }
        if (strcmp(name, "stop") == 0)
        {
            recording = false;
            updateState("ONLINE", info);
        }
        return true;
    }

    void setEnabled(bool b) override {
        enabled = b;
        if (!enabled) {
            updateState("OFFLINE", info);
        }
        else {
            updateState("ONLINE", info);
        }
    }

    bool getEnabled() override {
        return enabled;
    }

    const char* getInfo()
    {
        return info;
    }

    const char* getState()
    {
        if (enabled)
            return "ONLINE";
        else
            return "OFFLINE";
    }

    void loop()
    {
        running = true;

        using namespace std::chrono_literals;

        int h, m, s, f;
        std::ostringstream oss;

        while (running)
        {
            std::this_thread::sleep_for(33ms);

            f = frame % 30;
            value = (frame - f) / 30;
            s = value % 60;
            value = (value - s) / 60;
            m = value % 60;
            h = (value - m) / 60;

            timecode(h, m, s, f, 30, false);

            std::ostringstream oss;
            oss.str("");
            oss << std::setfill('0') << std::setw(2) << h;
            oss << std::setfill('0') << std::setw(2) << m;
            oss << std::setfill('0') << std::setw(2) << s;
            oss << std::setfill('0') << std::setw(2) << f;

            // strncpy(info, oss.str().c_str(), 255);

            frame++;
			
			/*

            if (f == 0) {
                if (!enabled)
                {
                    updateState("OFFLINE", info);
                }
                else
                {
                    if (recording)
                        updateState("RECORDING", info);
                    else
                        updateState("ONLINE", info);
                }
            }*/
        }
    }

    char info[255];
    bool enabled;
    bool recording;
    std::shared_ptr<std::thread> myThread;
    bool running;
    size_t frame;
    std::string host;
    int value;

};

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new MyPlugin();
}

extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "MyDevice";
}
