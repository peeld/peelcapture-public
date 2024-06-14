#include "peelCapPlugin.h"

#include "DataStreamClient.h"

#include <thread>
#include <string>
#include <vector>

class ViconPlugin : public PeelCapDeviceInterface {
public:

    ViconPlugin();

    ~ViconPlugin();

    const char* device() { return "ViconDevice"; };

    bool reconfigure(const char*) override;

    void teardown() override;

    bool command(const char* name, const char* arg) override;

    const char* pluginCommand(const char*) override;

    void run();

    std::thread thread;

    ViconDataStreamSDK::CPP::Client *client;

    std::string host;

    std::vector< std::string > mSubjects;
    std::vector< std::string > mProps;

    bool running;
    bool messageFlag;
    bool captureTimecode;
    bool captureSubjects;

};

const char* ViconError(ViconDataStreamSDK::CPP::Result::Enum);

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new ViconPlugin();
}

extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "Vicon";
}
