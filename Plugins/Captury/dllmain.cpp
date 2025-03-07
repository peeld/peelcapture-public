#include "peelCapPlugin.h"

#pragma warning( disable : 4200)
#include "RemoteCaptury.h"

#include <iostream>
#include <thread>
#include <memory>
#include <sstream>
#include <iomanip>
#include <cstring>
#include <unordered_set>
#include <vector>
#include <string>
#include <algorithm>

// #define DEBUG_STOP_OPT_FORCE    __pragma(optimize("", off))
// DEBUG_STOP_OPT_FORCE

static void newPose(CapturyActor* actor, CapturyPose* pose, int trackingQuality, void* userArg);
static void actorChanged(int actorId, int mode, void* userArg);

class CapturyPlugin : public PeelCapDeviceInterface {
public:

    CapturyPlugin() : running(true) {
        port = 2101;
        enabled = false;
        recording = false;
        captureTimecode = false;
        captureSubjects = false;
        framerate = -1.0f;
        info[0] = '\0';
    };

    ~CapturyPlugin()
    {
        running = false;
    }

    const char* device() { return "Captury"; };

    bool reconfigure(const char* values) override
    {
        if (values == nullptr) {
            return false;
        }

        std::istringstream ss(values);

        std::string line;
        while (std::getline(ss, line)) {

            size_t pos = line.find('=');
            if (pos == std::string::npos)
                continue;

            std::string name = line.substr(0, pos);
            std::string value = line.substr(pos + 1);
            if (name.empty() || value.empty())
                continue;

            if (name == "host") {
                size_t pos = value.find(':');
                if (pos != std::string::npos) {
                    this->host = value.substr(0, pos);
                    this->port = atoi(value.substr(pos + 1).c_str());
                } else {
                    this->host = value;
                    this->port = 2101;
                }
            } else if (name == "timecode") {
                this->captureTimecode = (value == "1");
            } else if (name == "subjects") {
                this->captureSubjects = (value == "1");
            }
        }

        connectToCaptury();
        return true;
    }

    void teardown() override
    {
        disonnectFromCaptury();
        running = false;
    };

    bool command(const char* name, const char* arg)
    {
        int res;

        if (!enabled) {
            updateState("OFFLINE", "");
            return true;
        }

        if (strcmp(name, "record") == 0) {
            std::string sn = arg;
            res = Captury_setShotName(sn.c_str());
            if (res != 1) {
                updateState("ONLINE", "");
                return true;
            }

            int64_t startTime = Captury_startRecording();
            if (startTime > 0) {
                updateState("RECORDING", "");
                recording = true;
            } else {
                updateState("ERROR", "Could not record");
            }

            return true;
        }

        if (strcmp(name, "stop") == 0) {
            int res = Captury_stopRecording();
            if (res == 1) {
                updateState("ONLINE", "");
                recording = false;
            } else {
                updateState("ERROR", "Could not stop");
            }
            return true;
        }

        if (strcmp(name, "shotName") == 0) {
            currentShotName = arg;
        }

        return true;
    }

    void setEnabled(bool b) override
    {
        enabled = b;
        if (!enabled) {
            this->disonnectFromCaptury();
        } else {
            this->connectToCaptury();
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
        if (status == nullptr) {
            return "ERROR";
        } else {
            strncpy(info, status, 254);
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

    void newFrame(int64_t timestamp)
    {
        if (captureTimecode) {
            if (framerate == -1.0f) {
                int num, denom;
                Captury_getFramerate(&num, &denom);
                framerate = ((float)num) / denom;
            }

            if (timestamp < 0)
                return;

            time_t nowInSeconds = timestamp / 1000000;
            if (nowInSeconds > 86410) {
                struct tm* today = gmtime(&nowInSeconds);
                today->tm_hour = 0;
                today->tm_min = 0;
                today->tm_sec = 0;
                time_t todayTime = mktime(today);
                if (todayTime < nowInSeconds) {
                    timestamp -= todayTime * 1000000l;
                    nowInSeconds = timestamp / 1000000;
                }
            }

            struct tm *t = gmtime(&nowInSeconds);
            if (t != NULL) {
                uint64_t subSec = timestamp - nowInSeconds * 1000000;
                int frame = subSec * framerate / 1000000;
                timecode(t->tm_hour, t->tm_min, t->tm_sec, frame, framerate, false);
            }
        }
    }

    void actorChanged(const std::string& name, bool isProp, CapturyActorStatus mode)
    {
        switch (mode) {
        case ACTOR_SCALING:
        case ACTOR_TRACKING:
            if (isProp) {
                if (knownProps.count(name))
                    return;
                knownProps.insert(name);
            } else {
                if (knownSubjects.count(name))
                    return;
                knownSubjects.insert(name);
            }
            break;
        case ACTOR_STOPPED:
        case ACTOR_DELETED:
        case ACTOR_UNKNOWN:
            if (isProp) {
                if (knownSubjects.count(name) == 0)
                    return;
                knownSubjects.erase(name);
            } else {
                if (knownSubjects.count(name) == 0)
                    return;
                knownSubjects.erase(name);
            }
            break;
        }

        if (isProp) {
            std::vector<std::string> propList;
            propList.insert(propList.end(), knownProps.begin(), knownProps.end());
            std::sort(propList.begin(), propList.end());

            std::vector<const char*> stringList;
            for (int i = 0; i < (int)propList.size(); i++) { stringList.push_back(propList[i].c_str()); }
            this->props(&stringList[0], (int)stringList.size());
        } else {
            std::vector<std::string> subjectList;
            subjectList.insert(subjectList.end(), knownSubjects.begin(), knownSubjects.end());
            std::sort(subjectList.begin(), subjectList.end());

            std::vector<const char*> stringList;
            for (int i = 0; i < (int)subjectList.size(); i++) { stringList.push_back(subjectList[i].c_str()); }
            this->subjects(&stringList[0], (int)stringList.size());
        }
    }

    char info[255];
    bool enabled;
    bool running;
    bool recording;
    bool captureTimecode;
    bool captureSubjects;
    std::string host;
    int port;
    float framerate;
    std::string currentShotName;
    std::string commandReply;
    std::unordered_set<std::string> knownSubjects;
    std::unordered_set<std::string> knownProps;

protected:
    void connectToCaptury()
    {
        if (host.empty() || !enabled)
            return;

        const char* status = Captury_getStatus();
        if (status == nullptr) {
            int res = Captury_connect(host.c_str(), port);

            if (res != 1) {
                updateState("ERROR", "Error Connecting");
            }

            status = Captury_getStatus();
            if (status == nullptr) {
                strcpy(info, "No Connection");
                updateState("ERROR", "No Connection");
            } else {
                updateState("ONLINE", status);
            }
        }

        if (captureTimecode) {
            Captury_registerNewPoseCallback(newPose, this);
            Captury_startStreaming(CAPTURY_STREAM_POSES | CAPTURY_STREAM_COMPRESSED);
        }
        if (captureSubjects) {
            Captury_registerActorChangedCallback(::actorChanged, this);
            if (!captureTimecode)
                Captury_startStreaming(CAPTURY_STREAM_COMPRESSED);
        }
    }

    void disonnectFromCaptury()
    {
        Captury_registerNewPoseCallback(NULL, NULL);
        Captury_registerActorChangedCallback(NULL, NULL);
        Captury_stopStreaming();

        Captury_disconnect();
        updateState("OFFLINE", "");
    }
};

static void newPose(CapturyActor* actor, CapturyPose* pose, int trackingQuality, void* userArg)
{
    ((CapturyPlugin*)userArg)->newFrame(pose->timestamp);
}

static void actorChanged(int actorId, int mode, void* userArg)
{
    const CapturyActor* actor = Captury_getActor(actorId);
    if (actor == NULL)
        return;

    ((CapturyPlugin*)userArg)->actorChanged(actor->name, actor->numJoints < 3, (CapturyActorStatus)mode);
    Captury_freeActor(actor);
}

extern "C" PEEL_PLUGIN_API PeelCapDeviceInterface * createPlugin() {
    return new CapturyPlugin();
}

extern "C" PEEL_PLUGIN_API const char* getIdentifier() {
    return "Captury";
}
