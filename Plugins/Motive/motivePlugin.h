#include "peelCapPlugin.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <mutex>
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

	static void messageCallback(Verbosity msgType, const char* msg);

	void onMessage(Verbosity msgType, const char* msg);

private:

	bool connect();
	bool disconnect();

	NatNetClient client;

	sNatNetClientConnectParams params;

	//! Capture subject info
	bool captureSubjects;

	//! Respond to transport events (play etc)
	bool transport;

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
	std::map<int, std::string> rigidbodyDict;

	std::vector<std::string> mSubjectList;
	std::vector<std::string> mRigidbodyList;

	int tc_h;
	int tc_m;
	int tc_s;
	int tc_f;

	void getSubjectNames();  // gets props too

	bool playing;

	bool connected;

	std::string message;

	std::string value_serverAddress;
	std::string value_localAddress;
	std::string value_multicastAddress;

	static std::vector<MotivePlugin*> instances;
	static std::mutex instances_mutex;

};

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new MotivePlugin();
}


extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "Motive";
}
