# Copyright (c) 2022 Peel Software Development Inc
# All Rights Reserved.
#
# THIS SOFTWARE AND DOCUMENTATION ARE PROVIDED "AS IS" AND WITH ALL FAULTS AND DEFECTS WITHOUT WARRANTY OF ANY KIND. TO
# THE MAXIMUM EXTENT PERMITTED UNDER APPLICABLE LAW, PEEL SOFTWARE DEVELOPMENT, ON ITS OWN BEHALF AND ON BEHALF OF ITS
# AFFILIATES AND ITS AND THEIR RESPECTIVE LICENSORS AND SERVICE PROVIDERS, EXPRESSLY DISCLAIMS ALL WARRANTIES, WHETHER
# EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, WITH RESPECT TO THE SOFTWARE AND DOCUMENTATION, INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT, AND WARRANTIES THAT MAY
# ARISE OUT OF COURSE OF DEALING, COURSE OF PERFORMANCE, USAGE, OR TRADE PRACTICE. WITHOUT LIMITATION TO THE FOREGOING,
# PEEL SOFTWARE DEVELOPMENT PROVIDES NO WARRANTY OR UNDERTAKING, AND MAKES NO REPRESENTATION OF ANY KIND THAT THE
# LICENSED SOFTWARE WILL MEET REQUIREMENTS, ACHIEVE ANY INTENDED RESULTS, BE COMPATIBLE, OR WORK WITH ANY OTHER
# SOFTWARE, APPLICATIONS, SYSTEMS, OR SERVICES, OPERATE WITHOUT INTERRUPTION, MEET ANY PERFORMANCE OR RELIABILITY
# STANDARDS OR BE ERROR FREE, OR THAT ANY ERRORS OR DEFECTS CAN OR WILL BE CORRECTED.
#
# IN NO EVENT WILL PEEL SOFTWARE DEVELOPMENT OR ITS AFFILIATES, OR ANY OF ITS OR THEIR RESPECTIVE LICENSORS OR SERVICE
# PROVIDERS, BE LIABLE TO ANY THIRD PARTY FOR ANY USE, INTERRUPTION, DELAY, OR INABILITY TO USE THE SOFTWARE; LOST
# REVENUES OR PROFITS; DELAYS, INTERRUPTION, OR LOSS OF SERVICES, BUSINESS, OR GOODWILL; LOSS OR CORRUPTION OF DATA;
# LOSS RESULTING FROM SYSTEM OR SYSTEM SERVICE FAILURE, MALFUNCTION, OR SHUTDOWN; FAILURE TO ACCURATELY TRANSFER, READ,
# OR TRANSMIT INFORMATION; FAILURE TO UPDATE OR PROVIDE CORRECT INFORMATION; SYSTEM INCOMPATIBILITY OR PROVISION OF
# INCORRECT COMPATIBILITY INFORMATION; OR BREACHES IN SYSTEM SECURITY; OR FOR ANY CONSEQUENTIAL, INCIDENTAL, INDIRECT,
# EXEMPLARY, SPECIAL, OR PUNITIVE DAMAGES, WHETHER ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT, BREACH OF
# CONTRACT, TORT (INCLUDING NEGLIGENCE), OR OTHERWISE, REGARDLESS OF WHETHER SUCH DAMAGES WERE FORESEEABLE AND WHETHER
# OR NOT THE LICENSOR WAS ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.


from __future__ import print_function
import pickle
import os.path
import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
from PySide6 import QtWidgets, QtCore, QtGui
import timecode

class GoogleGui(QtWidgets.QDialog):
    def __init__(self, file_path, sheet_id=None, parent=None):
        super(GoogleGui, self).__init__(parent)

        self.settings = QtCore.QSettings("PeelDev", "PeelCapture")

        fp = open(file_path, 'r')
        self.data = json.load(fp)
        fp.close()

        layout = QtWidgets.QFormLayout()

        self.takes = QtWidgets.QLabel("Publishing %d takes" % len(self.data["takes"]))
        layout.addRow("", self.takes)

        # Framerate
        self.fps = QtWidgets.QLineEdit()
        self.fps.setText("29.97")
        layout.addRow("Fps", self.fps)

        # Sheet
        self.sheet = QtWidgets.QLineEdit()
        if sheet_id:
            self.sheet.setText(sheet_id)
        layout.addRow("Sheet Id", self.sheet)

        # Range
        self.range = QtWidgets.QLineEdit()
        self.range.setText("Sheet1!A1")
        layout.addRow("Range", self.range)

        # Fields
        self.fields = QtWidgets.QLineEdit()
        self.fields.setText("take,name,select,start,end,duration,description,info,notes,subject-count,subjects,markin,markout,marked-duration")
        layout.addRow("Fields", self.fields)

        # Buttons

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.okay = QtWidgets.QPushButton("Publish")
        self.okay.pressed.connect(self.do_publish)
        buttons.addWidget(self.okay)
        buttons.addStretch(1)

        layout.addItem(buttons)

        self.setLayout(layout)

        self.resize(500, 200)

    def connect(self):

        cwd = os.path.dirname(os.path.abspath(__file__))

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.join(cwd, 'credentials.json'), ['https://www.googleapis.com/auth/spreadsheets'])
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('sheets', 'v4', credentials=creds)

    def do_publish(self):

        service = self.connect()

        sheet_id = self.sheet.text()
        range = self.range.text()

        sheet = service.spreadsheets()

        fields = self.fields.text().split(",")
        fields = [i.strip() for i in fields]

        fps = float(self.fps.text())

        values = []

        values.append(fields)

        for row in self.data['takes']:

            # Find first mark in
            markin = None
            for mark in row.get('marks', []):
                if mark['name'] == "in":
                    markin = mark["timecode"]
                    break

            # Find last mark out
            markout = None
            for mark in row.get('marks', []):
                if mark['name'] == "out":
                    markout = mark["timecode"]

            subjects = row.get('subjects', [])
            items = []
            for field in fields:

                start = row.get('start', None)
                end = row.get('end', None)

                if field.lower() == "take":    items.append(row.get('take', None))
                if field.lower() == "name":    items.append(row.get('takeName', None))
                if field.lower() == "select":  items.append(row.get('select', None))
                if field.lower() == "start":   items.append(start)
                if field.lower() == "end":     items.append(end)
                if field.lower() == "description":   items.append(row.get('description', None))
                if field.lower() == "info":    items.append(row.get('info', None))
                if field.lower() == "notes":   items.append(row.get('notes', None))
                if field.lower() == "subject-count": items.append(len(subjects))
                if field.lower() == "subjects": items.append(",".join(subjects))
                if field.lower() == "markin":   items.append(markin)
                if field.lower() == "markout":  items.append(markout)

                if field.lower() == "marked-duration" and markin and markout:
                    start_frame = timecode.Timecode(fps, markin).frames
                    end_frame = timecode.Timecode(fps, markout).frames
                    duration = (end_frame - start_frame) / fps
                    items.append(duration)

                if field.lower() == "duration" and start and end:
                    start_frame = timecode.Timecode(fps, start).frames
                    end_frame = timecode.Timecode(fps, end).frames
                    duration = (end_frame - start_frame) / fps
                    items.append(duration)

            values.append(items)

        body = {'values': values, 'majorDimension': "ROWS", 'range': range}

        request = sheet.values().append(spreadsheetId=sheet_id,
                                        range=range,
                                        valueInputOption="USER_ENTERED",
                                        insertDataOption="OVERWRITE",
                                        body=body)

        try:
            response = request.execute()
            print(response)
        except googleapiclient.errors.HttpError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))


