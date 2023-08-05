#include "peelCapPlugin.h"
#include "MocapApi.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <sstream>
#include <cstring>
#include <iomanip>
#include <mutex>



using namespace std;
using namespace std::this_thread; // sleep_for, sleep_until
using namespace std::chrono; // nanoseconds, system_clock, seconds   

class AxisStudioPlugin : public PeelCapDeviceInterface {
public:
    
    AxisStudioPlugin() {
        // Initialize values to invalid/null values here
        mcpError = MocapApi::EMCPError::Error_None;
        mcpApplication = nullptr;
        applicationHandle = 0;
        mcpSettings = nullptr;
        mcpSettingsHandle = 0;
        commandInterface = nullptr;
        commandHandle = 0;
        notifyInterface = nullptr;
        notifyHandle = 0;

        enabled = true;
        recording = false;

        host = "";
        port = 0;
    }

    ~AxisStudioPlugin() {
        teardown();
    }

    bool initializeEntity() {

        mcpError = MocapApi::MCPGetGenericInterface(MocapApi::IMCPApplication_Version,
            reinterpret_cast<void**>(&mcpApplication));
        if (!checkState("Getting Interface")) { return false; }

        mcpError = mcpApplication->CreateApplication(&applicationHandle);
        if (!checkState("Creating Application")) { return false; }

        mcpError = MocapApi::MCPGetGenericInterface(MocapApi::IMCPSettings_Version,
            reinterpret_cast<void**>(&mcpSettings));
        if (!checkState("Getting Mocap Interface")) { return false; }

        mcpError = mcpSettings->CreateSettings(&mcpSettingsHandle);
        if (!checkState("Creating settings")) { return false; }

        mcpError = mcpSettings->SetSettingsTCP(host.c_str(), port, mcpSettingsHandle);
        if (!checkState("Setting TCP")) { return false; }

        mcpError = mcpApplication->SetApplicationSettings(mcpSettingsHandle, applicationHandle);
        if (!checkState("Settings Application")) { return false; }
        
        mcpError = mcpApplication->OpenApplication(applicationHandle);
        if (!checkState("Opening Application")) { return false; }

        if (this->enabled)
            updateState("ONLINE", "");
        else
            updateState("OFFLINE", "");

        return true;

    }

    const char* device() { return "axisstudio"; };

    // Must delete current entity and create a new one with the new ip and port
    bool reconfigure(const char* value) override {

        // Setup the device and connection using data in "value"

        logMessage("Reconfigure Axis");
        logMessage(value);

        teardown();

        if (value != nullptr)
        {
            std::string svalue(value);

            auto pos = svalue.find(':');
            if (pos == -1) return false;

            this->host = svalue.substr(0, pos);

            std::string sport = svalue.substr(pos + 1, svalue.length());

            this->port = static_cast<uint16_t>(std::atoi(sport.c_str()));
        }

        setEnabled(false);

        return initializeEntity();
    }

    void teardown() override {

        if (commandInterface != nullptr && commandHandle != 0)
        {
            mcpError = commandInterface->DestroyCommand(commandHandle);
            checkState("Destroying Command");

            commandInterface = nullptr;
            commandHandle = 0;
        }
        if (notifyInterface != nullptr && notifyHandle != 0)
        {
            mcpError = notifyInterface->DestroyRecordNotify(notifyHandle);
            checkState("Destroying RecordNotify");

            notifyInterface = nullptr;
            notifyHandle = 0;
        }

        if (mcpSettings != nullptr)
        {
            mcpError = mcpSettings->DestroySettings(mcpSettingsHandle);
            checkState("Destroying Settings");

            mcpSettings = nullptr;
            mcpSettingsHandle = 0;
        }

        if (mcpApplication != nullptr)
        {
            mcpError = mcpApplication->CloseApplication(applicationHandle);
            checkState("Closing Application");

            mcpError = mcpApplication->DestroyApplication(applicationHandle);
            checkState("Destroying Application"); 

            mcpApplication = nullptr;
        }
    }

    const char* getState() { return state.c_str(); }
    const char* getInfo() { return info.c_str(); }

    void updateState(const char* state_, const char* info_)
    {
        PeelCapDeviceInterface::updateState(state_, info_);
        this->state = state_;
        this->info = info_;
    }

    bool checkState(const char* msg)
    {
        if (mcpError == MocapApi::Error_None)
            return true;
        if (mcpError == MocapApi::Error_ServerNotReady)
            msg = "No TCP connection";
        std::ostringstream oss;
        oss << msg << ": " << getErrorStr(mcpError);
        info = oss.str();
        updateState("ERROR", oss.str().c_str());
        logMessage(oss.str().c_str());
        return false;
    }

    bool command(const char* name, const char* arg)
    {
        if (!enabled)
        {
            updateState("OFFLINE", "");
            return true;
        }

        if (strcmp(name, "record") == 0)
        {
            if (commandInterface == nullptr)
                mcpError = MocapApi::MCPGetGenericInterface(MocapApi::IMCPCommand_Version,
                    reinterpret_cast<void**>(&commandInterface));
                if (!checkState("")) { return false; }

            mcpError = commandInterface->CreateCommand(MocapApi::CommandStartRecored, &commandHandle);
            if (!checkState("")) { return false; }

            sleep_for(milliseconds(100));

            if (arg != NULL && arg != "") {
                mcpError = commandInterface->SetCommandExtraLong(MocapApi::CommandExtraLong_Extra0,
                    reinterpret_cast<intptr_t>(arg), commandHandle);
                if (!checkState("")) { return false; }
            }
            mcpError = mcpApplication->QueuedServerCommand(commandHandle, applicationHandle);
            if (!checkState("Could not record")) { return false; }
            
            sleep_for(milliseconds(100));

            PollEvents();
        }  

        if (strcmp(name, "stop") == 0)
        {
            if (commandInterface == nullptr)
                mcpError = MocapApi::MCPGetGenericInterface(MocapApi::IMCPCommand_Version,
                    reinterpret_cast<void**>(&commandInterface));
                if (!checkState("")) { return false; }

            mcpError = commandInterface->CreateCommand(MocapApi::CommandStopRecored, &commandHandle);
            if (!checkState("")) { return false; }

            sleep_for(milliseconds(100));

            mcpError = mcpApplication->QueuedServerCommand(commandHandle, applicationHandle);
            if (!checkState("Stopping")) { return false; }
            
            sleep_for(milliseconds(100));

            PollEvents();
        }       

        return true;
    }

    //Check for Record Notifications from Axis Studio(RecordStarted, RecordStopped, RecordFinished)
    void PollEvents()
    {
        vector<MocapApi::MCPEvent_t> events;
        uint32_t unEvent = 0;
            
        mcpError = mcpApplication->PollApplicationNextEvent(nullptr, &unEvent,
            applicationHandle);
        checkState("Could not PollEvents");
            
        bool hasUnhandledEvents = unEvent > 0;
        if (hasUnhandledEvents) {
            events.resize(unEvent);
            for (auto& e : events) {
                e.size = sizeof(MocapApi::MCPEvent_t);
                e.eventType = MocapApi::MCPEvent_None;
            }
            mcpError = mcpApplication->PollApplicationNextEvent(events.data(), &unEvent, applicationHandle);
            checkState("Could not PollEvents");
            
            hasUnhandledEvents = unEvent > 0;
            events.resize(unEvent);
        }
        if (hasUnhandledEvents) {
            std::lock_guard<std::mutex> lock(Critical);

            for (const auto& e : events) {
                if (e.eventType == MocapApi::MCPEvent_Error) {
                    mcpError = e.eventData.systemError.error;
                    checkState("");
                }
                else if (e.eventType == MocapApi::MCPEvent_Notify)
                {   
                    MocapApi::EMCPNotify notifyType = e.eventData.notifyData._notify;
                    notifyHandle = e.eventData.notifyData._notifyHandle;
                    
                    if (notifyInterface == nullptr) {
                        mcpError = MocapApi::MCPGetGenericInterface(MocapApi::IMCPRecordNotify_Version,
                            reinterpret_cast<void**>(&notifyInterface));
                        checkState("Getting RecordNotify Interface");
                    }

                    const char* name = nullptr;
                    mcpError = notifyInterface->RecordNotifyGetTakeName(&name, notifyHandle);
                    checkState("Getting TakeName");

                    if (name == nullptr){
                        return;
                    }
                    if (notifyType == MocapApi::EMCPNotify::Notify_RecordStarted) {
                        recording = true;
                        updateState("RECORDING", "");
                    }
                    else if (notifyType == MocapApi::EMCPNotify::Notify_RecordStoped) {
                        recording = false;
                        updateState("ONLINE", "");
                    }
                    else if (notifyType == MocapApi::EMCPNotify::Notify_RecordFinished) {
                        recording = false;
                        updateState("ONLINE", "");
                    }
                    
                }
            }
        }
    }
    void setEnabled(bool b) override {
        enabled = b;
        if (!enabled) {
            updateState("OFFLINE", info.c_str());
        }
        else {
            updateState("ONLINE", info.c_str());
        }
    }

    bool getEnabled() override {
        return enabled;
    }

    string getErrorStr(int ErrorId)
    {
        MocapApi::EMCPError Err = (MocapApi::EMCPError)(ErrorId);
        switch (Err)
        {
        case MocapApi::Error_MoreEvent:
            return "Error_MoreEvent";
        case MocapApi::Error_InsufficientBuffer:
            return "Error_InsufficientBuffer";
        case MocapApi::Error_InvalidObject:
            return "Error_InvalidObject";
        case MocapApi::Error_InvalidHandle:
            return "Error_InvalidHandle";
        case MocapApi::Error_InvalidParameter:
            return "Error_InvalidParameter";
        case MocapApi::Error_NotSupported:
            return "Error_NotSupported";
        case MocapApi::Error_IgnoreUDPSetting:
            return "Error_IgnoreUDPSetting";
        case MocapApi::Error_IgnoreTCPSetting:
            return "Error_IgnoreTCPSetting";
        case MocapApi::Error_IgnoreBvhSetting:
            return "Error_IgnoreBvhSetting";
        case MocapApi::Error_JointNotFound:
            return "Error_JointNotFound";
        case MocapApi::Error_WithoutTransformation:
            return "Error_WithoutTransformation";
        case MocapApi::Error_NoneMessage:
            return "Error_NoneMessage";
        case MocapApi::Error_NoneParent:
            return "Error_NoneParent";
        case MocapApi::Error_NoneChild:
            return "Error_NoneChild";
        case MocapApi::Error_AddressInUse:
            return "Error_AddressInUse";
        case MocapApi::Error_ServerNotReady:
            return "Error_ServerNotReady";
        case MocapApi::Error_ClientNotReady:
            return "Error_ClientNotReady";
        case MocapApi::Error_IncompleteCommand:
            return "Error_IncompleteCommand";
        case MocapApi::Error_UDP:
            return "Error_UDP";
        case MocapApi::Error_TCP:
            return "Error_TCP";
        case MocapApi::Error_QueuedCommandFaild:
            return "Error_QueuedCommandFaild";
        default:
            return "Error_Unknown";
        }
    }


    MocapApi::EMCPError mcpError;
    MocapApi::IMCPApplication* mcpApplication;
    MocapApi::MCPApplicationHandle_t applicationHandle;
    MocapApi::IMCPSettings* mcpSettings;
    MocapApi::MCPSettingsHandle_t mcpSettingsHandle;
    MocapApi::IMCPCommand* commandInterface;
    MocapApi::MCPCommandHandle_t commandHandle;
    MocapApi::IMCPRecordNotify* notifyInterface;
    MocapApi::MCPRecordNotifyHandle_t notifyHandle;

    bool enabled;
    bool recording;
    std::string host;
    uint16_t port;

    std::string state;
    std::string info;
    
    std::mutex Critical;

};

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new AxisStudioPlugin();
}

extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "AxisStudio";
}
