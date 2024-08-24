#include "peelCapPlugin.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <functional>

#include "NatNetClient.h"

// https://docs.optitrack.com/developer-tools/natnet-sdk


class MotivePlugin : public PeelCapDeviceInterface {

public:

    MotivePlugin();

    ~MotivePlugin();

    const char* device() { return "MotiveDevice"; };

    bool reconfigure(const char*) override;

    void teardown() override;

    bool command(const char* name, const char* arg) override;

    const char* pluginCommand(const char*) override;

	void inFrame(sFrameOfMocapData*);

private:

	bool connect();
	bool disconnect();

	NatNetClient client;

	sNatNetClientConnectParams params;

	//! Capture subject info
	bool captureSubjects;

	//! Capture and emit timecode
	bool captureTimecode;

	//! Set the capture directory
	bool setCaptureFolder;

	int tcRate;
	int lastFrameValue;

	bool sendMotive(const char* cmd);

	ErrorCode error;

	std::string errorStr();
	std::string errorStr(ErrorCode);

	void messageCallback(int, const char*);

	std::map<int, std::string> subjectDict;
	std::map<int, std::string> propDict;

	std::vector<std::string> mSubjectList;
	std::vector<std::string> mPropList;

	int tc_h;
	int tc_m;
	int tc_s;
	int tc_f;

	void getSubjectNames();  // gets props too

	bool playing;

private:
	std::string message;

	std::string value_serverAddress;
	std::string value_localAddress;
	std::string value_multicastAddress;

};

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new MotivePlugin();
}


extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "Motive";
}
