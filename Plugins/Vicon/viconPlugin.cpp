#include "peelCapPlugin.h"
#include "viconPlugin.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <algorithm>

using namespace std::chrono_literals;

using namespace ViconDataStreamSDK::CPP;


const char* ViconError(ViconDataStreamSDK::CPP::Result::Enum result)
{
    switch (result)
    {
    case Result::Unknown: return "The result is unknown. Treat it as a failure.";
    case Result::NotImplemented: return "The function called has not been implemented in this version of the SDK.";
    case Result::Success: return "The function call succeeded.";
    case Result::InvalidHostName: return "The HostName parameter passed to Connect() is invalid.";
    case Result::InvalidMulticastIP: return "The MulticastIP parameter was not in the range \"224.0.0.0\" - \"239.255.255.255\"";
    case Result::ClientAlreadyConnected: return "Connect() was called whilst already connected to a DataStream.";
    case Result::ClientConnectionFailed: return "Connect() could not establish a connection to the DataStream server.";
    case Result::ServerAlreadyTransmittingMulticast: return "StartTransmittingMulticast() was called when the current DataStream server was already transmitting multicast on behalf of this client.";
    case Result::ServerNotTransmittingMulticast: return "StopTransmittingMulticast() was called when the current DataStream server was not transmitting multicast on behalf of this client.";
    case Result::NotConnected: return "You have called a function which requires a connection to the DataStream server, but do not have a connection.";
    case Result::NoFrame: return "You have called a function which requires a frame to be fetched from the DataStream server, but do not have a frame.";
    case Result::InvalidIndex: return "An index you have passed to a function is out of range.";
    case Result::InvalidCameraName: return "The Camera Name you passed to a function is invalid in this frame.";
    case Result::InvalidSubjectName: return "The Subject Name you passed to a function is invalid in this frame.";
    case Result::InvalidSegmentName: return "The Segment Name you passed to a function is invalid in this frame.";
    case Result::InvalidMarkerName: return "The Marker Name you passed to a function is invalid in this frame.";
    case Result::InvalidDeviceName: return "The Device Name you passed to a function is invalid in this frame.";
    case Result::InvalidDeviceOutputName: return "The Device Output Name you passed to a function is invalid in this frame.";
    case Result::InvalidLatencySampleName: return "The Latency Sample Name you passed to a function is invalid in this frame.";
    case Result::CoLinearAxes: return "The directions passed to SetAxisMapping() contain input which would cause two or more axes to lie along the same line, e.g. Up and Down are on the same line.";
    case Result::LeftHandedAxes: return "The directions passed to SetAxisMapping() would result in a left-handed coordinate system. This is not supported in the SDK.";
    case Result::HapticAlreadySet: return "Haptic feedback is already set.";
    case Result::EarlyDataRequested: return "Re-timed data requested is from before the first time sample we still have";
    case Result::LateDataRequested: return "Re-timed data requested is too far into the future to be predicted";
    case Result::InvalidOperation: return "The method called is not valid in the current mode of operation";
    case Result::NotSupported: return "The SDK version or operating system does not support this function.";
    case Result::ConfigurationFailed: return "The operating system configuration changed failed.";
    case Result::NotPresent: return "The requested data type is not present in the stream.";
    }
    return "Unknown Error";
}


ViconPlugin::ViconPlugin()
    : running(false)
    , messageFlag(false)
    , captureTimecode(false)
    , captureSubjects(false)
    , client(nullptr)
{
};

ViconPlugin::~ViconPlugin() {
    teardown();
}

// Must delete current entity and create a new one with the new ip and port
bool ViconPlugin::reconfigure(const char* value)
{
    // Setup the device and connectAxision using data in "value"

    logMessage("Reconfigure Vicon Plugin\n");
    logMessage(value);
    logMessage("\n");

    teardown();

    updateState("OFFLINE", "");

    if (value != nullptr)
    {
        std::istringstream ss(value);

        std::string line;

        while (std::getline(ss, line)) {
            std::size_t pos = line.find('=');
            if (pos != std::string::npos) {
                std::string name = line.substr(0, pos);
                std::string value = line.substr(pos + 1);
                if (name.size() > 0 && value.size() > 0) {
                    if (name == "host") { this->host = value; }
                    if (name == "subjects") { this->captureSubjects = value[0] == '1'; }
                    if (name == "timecode") { this->captureTimecode = value[0] == '1'; }
                }
            }
        }       
    }

    if (!this->host.empty()) {

        running = true;
        thread = std::thread(&ViconPlugin::run, this);
    }

    return true;
}

void ViconPlugin::run()
{
    // Thread

    std::vector< std::string > subjectList;
    std::vector< std::string > propList;
    Output_GetSubjectCount SubjectResult;
    Output_Connect ConnectResult;
    Output_GetTimecode TimecodeResult;

    while (running)
    {
        if (!client)
        {
            if (!messageFlag) {
                logMessage("Connecting to vicon\n");
                messageFlag = true;
            }

            client = std::make_shared< ViconDataStreamSDK::CPP::Client>();

            ConnectResult = client->Connect(host);

            if (running && ConnectResult.Result != Result::Success)
            {
                client.reset();
                std::this_thread::sleep_for(2000ms);
                continue;
            }

            logMessage("Vicon Connected\n");
            updateState("ONLINE", "");
            messageFlag = false;
        }

        Output_GetFrame FrameResult = client->GetFrame();
        if (FrameResult.Result == Result::NotConnected)
        {
            logMessage("Vicon Disconnected");            
            client.reset();
            client = nullptr;
            updateState("OFFLINE", "");
            continue;
        }

        if (FrameResult.Result == Result::NoFrame)
        {
            continue;
        }

        if (FrameResult.Result != Result::Success)
        {
            std::ostringstream oss;
            oss << "Vicon Error " << ViconError(FrameResult.Result);
            logMessage(oss.str().c_str());
            updateState("ERROR", ViconError(FrameResult.Result));
            continue;
        }

        if (captureTimecode)
        {
            TimecodeResult = client->GetTimecode();

            if (TimecodeResult.Result == Result::Success && TimecodeResult.Standard != TimecodeStandard::None)
            {
                int rate = 0;
                bool dropFrame = false;
                switch (TimecodeResult.Standard)
                {
                case TimecodeStandard::PAL:       rate = 25; break;
                case TimecodeStandard::NTSC:      rate = 30; break;
                case TimecodeStandard::NTSCDrop:  rate = 30; dropFrame = true; break;
                case TimecodeStandard::Film:
                case TimecodeStandard::NTSCFilm:  rate = 24; break;
                case TimecodeStandard::ATSC:      rate = 60; break;
                }
                timecode(TimecodeResult.Hours, TimecodeResult.Minutes, TimecodeResult.Seconds, TimecodeResult.Frames, (float)rate, dropFrame);
            }
        }

        if (captureSubjects)
        {
            SubjectResult = client->GetSubjectCount();

            if (SubjectResult.Result == Result::Success && SubjectResult.SubjectCount > 0)
            {
                unsigned int SubjectCount = SubjectResult.SubjectCount;

                subjectList.clear();
                propList.clear();

                for (unsigned int SubjectIndex = 0; SubjectIndex < SubjectCount; ++SubjectIndex)
                {
                    String subjectName = client->GetSubjectName(SubjectIndex).SubjectName;
                    std::string sName = subjectName;

                    int n = client->GetSegmentCount(subjectName).SegmentCount;
                    if (n == 1) {
                        propList.push_back(subjectName.operator std::string());
                    }
                    else {
                        subjectList.push_back(subjectName.operator std::string());
                    }
                }

                std::sort(subjectList.begin(), subjectList.end());
                std::sort(propList.begin(), propList.end());

                if (subjectList != this->mSubjects)
                {
                    mSubjects = subjectList;
                    std::vector<const char*> stringList;
                    for (int i = 0; i < mSubjects.size(); i++) { stringList.push_back(mSubjects[i].c_str()); }
                    if (stringList.size() == 0) { this->subjects(nullptr, 0); }
                    else { this->subjects(&stringList[0], (int)stringList.size()); }
                    
                }

                if (propList != this->mProps)
                {
                    mProps = propList;
                    std::vector<const char*> stringList;
                    for (int i = 0; i < mProps.size(); i++) { stringList.push_back(mProps[i].c_str()); }
                    if (stringList.size() == 0) { this->props(nullptr, 0); }
                    else { this->props(&stringList[0], (int)stringList.size()); }
                }
            }
        }
    }
    client.reset();
}


void ViconPlugin::teardown() {
    if (running) {
        running = false;
        thread.join();
    }
};

bool ViconPlugin::command(const char* name, const char* arg)
{

    return true;
}

const char* ViconPlugin::pluginCommand(const char*) { return ""; }
