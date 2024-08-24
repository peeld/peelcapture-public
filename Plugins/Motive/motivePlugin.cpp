#include "peelCapPlugin.h"
#include "motivePlugin.h"

#include "NatNetCAPI.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include <algorithm>
#include <sstream>


void frameCallback(sFrameOfMocapData* pFrameOfData, void* pUserData)
{
	MotivePlugin* ref = (MotivePlugin*)pUserData;
	ref->inFrame(pFrameOfData);
}

void messageCallback(Verbosity level, const char* message)
{
	//if (!gMotive) { return; }
//gMotive->messageCallback(level, message);
}


MotivePlugin::MotivePlugin()
	: captureSubjects(false)
	, captureTimecode(false)
	, setCaptureFolder(false)
	, tcRate(0)
	, lastFrameValue(0)
	, error(ErrorCode_OK)
	, tc_h(0), tc_m(0), tc_s(0), tc_f(0)
	, playing(false)
{
	NatNet_SetLogCallback(::messageCallback);



};

MotivePlugin::~MotivePlugin() {
}

bool MotivePlugin::reconfigure(const char* value) {

	if (value == nullptr) { return false; }

	std::ostringstream oss;
	unsigned char version[4];
	NatNet_GetVersion(version);
	oss << "Natnet version: " 
	    << (int)version[0] << "." << (int)version[1] << "."
		<< (int)version[2] << "." << (int)version[3];

	logMessage(oss.str().c_str());

	logMessage("Reconfigure Motive Plugin\n");
	logMessage(value);
	logMessage("\n");

	teardown();

	updateState("OFFLINE", "");

	this->captureSubjects = false;
	this->captureTimecode = false;

	params.connectionType = ConnectionType_Multicast;
	params.serverCommandPort = 0;
	params.serverDataPort = 0;
	params.serverAddress = 0;
	params.localAddress = 0;
	params.multicastAddress = 0;
	params.subscribedDataOnly = true;

	memset(params.BitstreamVersion, 0, sizeof(params.BitstreamVersion));

	std::istringstream ss(value);

	std::string line;

	while (std::getline(ss, line)) {

		logMessage(line.c_str());

		std::size_t pos = line.find('=');
		if (pos == std::string::npos || pos + 1 == line.size()) {
			continue;
		}

		std::string name = line.substr(0, pos);
		std::string value = line.substr(pos + 1);

		if (name.size() == 0 || value.size() == 0) {
			continue;
		}

		if (name == "multicast") {
			params.connectionType = value[0] == '1'
				? ConnectionType_Multicast
				: ConnectionType_Unicast;
		}
		if (name == "commandPort") {
			params.serverCommandPort = std::atoi(value.c_str());
		}
		if (name == "dataPort") {
			params.serverDataPort = std::atoi(value.c_str());
		}
		if (name == "serverAddress") {
			value_serverAddress = value;
			params.serverAddress = value_serverAddress.c_str();
		}
		if (name == "localAddress") {
			value_localAddress = value;
			params.localAddress = value_localAddress.c_str();
		}
		if (name == "multicastAddress") {
			value_multicastAddress = value;
			params.multicastAddress = value_multicastAddress.c_str();
		}
		if (name == "subjects") {
			this->captureSubjects = value[0] == '1';
		}
		if (name == "timecode") {
			this->captureTimecode = value[0] == '1';
		}
		if (name == "capturefolder") {
			this->setCaptureFolder = value[0] == '1';
		}
	}

	if (this->params.serverAddress == 0 || this->params.serverAddress[0] == 0) {
		logMessage("Motive server address was empty, not connecting.");
		updateState("Error", "No server address");
		return false;
	}

	this->connect();

	return true;
}

void MotivePlugin::teardown() {};


bool MotivePlugin::sendMotive(const char* command)
{
	// https://wiki.optitrack.com/index.php?title=NatNet:_Class/Function_Reference#NatNetClient::SendMessageAndWait
	// https://wiki.optitrack.com/index.php?title=NatNet:_Remote_Requests/Commands
	// "Most commands : response buffer is a 4 byte success code (success=0, failure=1)"

	uint8_t* data;
	int   sz;
	auto err = client.SendMessageAndWait(command, (void**)&data, &sz);
	if (err != ErrorCode::ErrorCode_OK)
	{
		logMessage("Motive Command Failed");
		this->message = this->errorStr(err);
		logMessage(this->message.c_str());
		updateState("ERROR", message.c_str());
		return false;
	}
	if (data != nullptr && sz > 0)
	{
		/*		std::ostringstream ss;
				ss << "Motive Replied: " << sz;
				std::string msg = QString("Motive replied: %0\n").arg(sz);
				for (int i = 0; i < sz; i++)
				{
					msg += QString::asprintf("%02X ", data[i]);
					if (i % 32 == 31) msg += "\n";
				}
				emit onMessage(msg);
				emit commandResponse(true, QString());*/
	}
	else
	{
	}

	return true;
}


const char* MotivePlugin::pluginCommand(const char* command)
{
	// Called via pluginCommand

	logMessage(command);

	std::string scommand(command);

	if (scommand.rfind("SetDataDirectory:", 0) == 0) {
		std::ostringstream oss;
		oss << "SetCurrentSession,";
		oss << scommand.substr(10);
		sendMotive(oss.str().c_str());
	}

	return "";
}

bool MotivePlugin::command(const char* name, const char* arg)
{

	if (strcmp(name, "record") == 0) {
		std::ostringstream oss;
		oss << "SetRecordTakeName," << arg;
		if (sendMotive(oss.str().c_str()) && sendMotive("StartRecording"))
		{
			updateState("RECORDING", "");
		}
	}

	if (strcmp(name, "stop") == 0) {
		if (playing) {
			if (sendMotive("TimelineStop"))
			{
				updateState("ONLINE", "");
			}
			playing = false;
		}
		else
		{
			if (sendMotive("StopRecording"))
			{
				updateState("ONLINE", "");
			}
		}
	}

	if (strcmp(name, "play") == 0) {
		std::ostringstream oss;
		oss << "SetPlaybackTakeName," << arg;
		if (sendMotive(oss.str().c_str())) {

			if (sendMotive("TimelinePlay")) {
				updateState("PLAYING", arg);
				playing = true;
			}
		}

	}

	return true;
}


bool MotivePlugin::connect()
{
	logMessage("Motive Connecting");

	client.Disconnect();

	if (params.serverCommandPort == 0) {
		updateState("ERROR", "Command port not set");
		return false;
	}

	if (params.serverDataPort == 0) {
		updateState("ERROR", "Data port not set");
		return false;
	}

	if (params.serverAddress == 0 || params.serverAddress[0] == 0) {
		updateState("ERROR", "Server address not set");
		return false;
	}

	if (params.localAddress == 0 || params.localAddress[0] == 0) {
		updateState("ERROR", "Local address not set");
		return false;
	}

	if (params.multicastAddress == 0 || params.multicastAddress[0] == 0) {
		updateState("ERROR", "Mukticast address not set");
		return false;
	}

	if (this->captureSubjects) {
		client.SetFrameReceivedCallback(frameCallback, this);
	}

	error = client.Connect(params);
	if (error != ErrorCode_OK) {
		updateState("OFFLINE", "Could not connect");
		return false;
	}

	logMessage("Motive Connected");

	updateState("ONLINE", "");

	if (this->captureSubjects) {
		sendMotive("SubscribeToData,Skeleton");
	}

	return true;
}

void MotivePlugin::getSubjectNames()
{
	sDataDescriptions* dataDescriptions = 0;
	ErrorCode ret = client.GetDataDescriptionList(&dataDescriptions);
	if (ret != ErrorCode_OK)
	{
		return;
	}

	subjectDict.clear();

	for (int i = 0; i < dataDescriptions->nDataDescriptions; i++)
	{
		auto item = dataDescriptions->arrDataDescriptions[i];

		if (item.type == Descriptor_Skeleton)
		{
			auto skel = item.Data.SkeletonDescription;
			subjectDict[skel->skeletonID] = skel->szName;
		}

		if (item.type == Descriptor_RigidBody)
		{
			auto prop = item.Data.RigidBodyDescription;
			propDict[prop->ID] = prop->szName;
		}
	}

}

std::string MotivePlugin::errorStr(ErrorCode e)
{
	switch (e)
	{
	case ErrorCode_OK: return "No Error";
	case ErrorCode_Internal: return "Internal Error";
	case ErrorCode_External: return "External Error";
	case ErrorCode_Network: return "Network Error";
	case ErrorCode_Other: return "Other Error";
	case ErrorCode_InvalidArgument: return "Invalid Argument Error";
	case ErrorCode_InvalidOperation: return "Invalid Operation Error";
	case ErrorCode_InvalidSize: return "Invalid Size Error";
	}

	return "Unknown Error";
}

std::string MotivePlugin::errorStr()
{
	return errorStr(error);
}

void MotivePlugin::messageCallback(int verbosity, const char* message)
{
	//emit onMessage(QString("Motive> %0\n").arg(message));
}

bool MotivePlugin::disconnect()
{
	error = client.Disconnect();
	return error == ErrorCode_OK;
}

void MotivePlugin::inFrame(sFrameOfMocapData* frame)
{
	if (captureSubjects)
	{
		std::vector< std::string > subjectList;
		for (int s = 0; s < frame->nSkeletons; s++)
		{
			auto skeleton = frame->Skeletons[s];
			int sid = skeleton.skeletonID;

			if (subjectDict.find(sid) == subjectDict.end())
			{
				// Name isn't in the list, get the list
				getSubjectNames();
			}

			if (subjectDict.find(sid) != subjectDict.end())
			{
				subjectList.push_back(subjectDict[sid]);
			}
		}

		std::vector< std::string > propList;
		for (int p = 0; p < frame->nRigidBodies; p++)
		{
			auto prop = frame->RigidBodies[p];
			int pid = prop.ID;
			if (propDict.find(pid) == propDict.end())
			{
				getSubjectNames();
			}
			if (propDict.find(pid) != propDict.end())
			{
				propList.push_back(propDict[pid]);
			}
		}

		std::sort(subjectList.begin(), subjectList.end());
		std::sort(propList.begin(), propList.end());

		if (this->mSubjectList != subjectList) {
			this->mSubjectList = subjectList;
			if (this->mSubjectList.size() == 0) {
				this->subjects(nullptr, 0);
			}
			else {
				std::vector<const char*> ptr;
				for (auto& i : this->mSubjectList) { ptr.push_back(i.c_str()); }
				this->subjects(&ptr[0], ptr.size());
			}

		}

		if (this->mPropList != propList) {
			this->mPropList = propList;
			if (this->mPropList.size() == 0) {
				this->props(nullptr, 0);
			}
			else {
				std::vector<const char*> ptr;
				for (auto& i : this->mPropList) { ptr.push_back(i.c_str()); }
				this->props(&ptr[0], ptr.size());
			}

		}
	}
	else
	{
		if (this->mSubjectList.size() > 0)
		{
			// Clear the list
			this->subjects(NULL, 0);
			this->mSubjectList.clear();
		}

		if (this->mPropList.size() > 0) {
			this->props(NULL, 0);
			this->mPropList.clear();

		}
	}

	if (captureTimecode)
	{
		int subframe;
		int h = 0, m = 0, s = 0, f = 0;
		if (NatNet_DecodeTimecode(frame->Timecode, frame->TimecodeSubframe, &h, &m, &s, &f, &subframe) == ErrorCode_OK)
		{
			if (f == 0 && lastFrameValue > 0) tcRate = lastFrameValue + 1;

			if ((tc_h != h || tc_m != m || tc_s != s || tc_f != f) && tcRate != 0) {
				timecode(h, m, s, f, tcRate, false);
				tc_h = h;
				tc_m = m;
				tc_s = s;
				tc_f = f;
			}
			lastFrameValue = f;
		}
	}
}


/*
void MotivePlugin::sendCommand(QString command)
{
	// linked to python commands:  cmd.motiveCommand(...)
	// https://wiki.optitrack.com/index.php?title=NatNet:_Class/Function_Reference#NatNetClient::SendMessageAndWait
	// https://wiki.optitrack.com/index.php?title=NatNet:_Remote_Requests/Commands
	// "Most commands : response buffer is a 4 byte success code (success=0, failure=1)"

	uint8_t* data;
	int   sz;
	std::string cmd = command.toUtf8().data();
	auto err = client.SendMessageAndWait(cmd.c_str(), (void**)&data, &sz);
	if (err != ErrorCode::ErrorCode_OK)
	{
		emit commandResponse(false, errorStr(err));
		return;
	}
	if (data != nullptr && sz > 0)
	{
		QString msg = QString("Motive replied: %0\n").arg(sz);
		for (int i = 0; i < sz; i++)
		{
			msg += QString::asprintf("%02X ", data[i]);
			if (i % 32 == 31) msg += "\n";
		}
		emit onMessage(msg);
		emit commandResponse(true, QString());
	}
	else
	{
		emit commandResponse(false, "No data");
	}
}*/