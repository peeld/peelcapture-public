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

"""
from peel import shotgun_publish
from importlib import reload
reload(shotgun_publish)
import shotgun_api3
from PeelApp import cmd
w = shotgun_publish.gui()
"""

import shotgun_api3
from PySide6 import QtWidgets, QtCore
import json
import os.path
import os
from PeelApp import cmd
from functools import partial
import subprocess
from peel import movie
import urllib.parse
import peel


def validate_entities(sg, project_id):
    project = {'type': 'Project', 'id': project_id}
    entities = sg.schema_entity_read(project_entity=project).keys()

    required = ["ShootDay", "TaskTemplate",  "MocapTake", "Performer", "Note", "Version"]

    missing = []
    for i in required:
        if i not in entities:
            missing.append(i)

    return missing


def projects(sg):
    filters = [("is_template", "is_not", True), ("archived", "is_not", True)]
    return sg.find("Project", filters, ["id", "name", "sg_status"])


def shoot_days(sg, project_id):
    project = {'type': 'Project', 'id': project_id}
    return sg.find("ShootDay", [("project", "is", project)], ["id", "code"])


def task_templates(sg):
    return sg.find("TaskTemplate",  [('entity_type', 'is', 'MocapTake')], ["id", "code"])


class UploadGui(QtWidgets.QDialog):
    def __init__(self, sg, file_path, parent=None):
        super(UploadGui, self).__init__(parent)

        self.sg = sg

        self.settings = QtCore.QSettings("PeelDev", "PeelCapture")

        self.setStyleSheet("color: #eee")

        fp = open(file_path, 'r')
        self.data = json.load(fp)
        fp.close()

        self.resize(500, 200)
        
        layout = QtWidgets.QFormLayout()

        # Takes
        self.takes = QtWidgets.QLabel("Publishing %d takes" % len(self.data["takes"]))
        layout.addRow("", self.takes)

        # Info
        self.info = QtWidgets.QLabel()
        self.info.setStyleSheet("color: #ccc; ")
        layout.addWidget(self.info)

        # Projects
        self.projects = QtWidgets.QComboBox()
        self.projects.setStyleSheet("background: #a6a6a6; color: black;")
        for i in sorted(projects(self.sg), key=lambda v: v["name"]):
            self.projects.addItem(i["name"], i["id"])
        current_project = self.settings.value("project")
        if current_project is not None:
            self.projects.setCurrentText(str(current_project))
        self.projects.currentIndexChanged.connect(self.on_project_changed)
        layout.addRow("Projects", self.projects)

        # Shoot Day
        self.shoot = QtWidgets.QLineEdit()
        self.shoot.setStyleSheet("background: #a6a6a6; color: black;")
        layout.addRow("Shoot Day", self.shoot)
        self.shoot_days_completer = None
        if 'shoot' in self.data:
            self.shoot.setText(self.data['shoot'])

        # Task templates
        self.task_templates = QtWidgets.QComboBox()
        self.task_templates.setStyleSheet("background: #a6a6a6; color: black;")

        for i in sorted(task_templates(sg), key=lambda v: v["code"]):
            self.task_templates.addItem(i["code"], i["id"])
        layout.addRow("Task Template", self.task_templates)

        self.compress_cb = QtWidgets.QCheckBox("")
        layout.addRow("Compress: ", self.compress_cb)
        self.compress_cb.setChecked(True)

        # Progress Bar
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setVisible(False)
        self.progressBar.setStyleSheet("QProgressBar::chunk { background: #444; } "
                        "QProgressBar{ text-align: center; color: #ccc; padding: 1px; height:10px; }")
        layout.addWidget(self.progressBar)

        # Buttons

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.okay = QtWidgets.QPushButton("Publish")
        self.okay.pressed.connect(self.do_publish)
        buttons.addWidget(self.okay)
        buttons.addStretch(1)

        layout.addItem(buttons)
        
        self.setLayout(layout)

        self.populate_shoot_days()

    def do_close(self):
        self.close()
        self.deleteLater()

    def on_project_changed(self, _=None):
        self.populate_shoot_days()

    def populate_shoot_days(self):

        project_id = self.projects.currentData()
        if project_id is None:
            return

        self.settings.setValue("project", self.projects.currentText())

        project_id = self.projects.currentData()
        if project_id is None:
            return

        missing = validate_entities(self.sg, project_id)
        if missing:
            self.info.setText('<FONT COLOR="red">Missing Entities: ' + ",".join(missing) + '</FONT>')
            return

        shoots = shoot_days(self.sg, project_id)
        items = sorted([i['code'] for i in shoots])
        self.shoot_days_completer = QtWidgets.QCompleter(items, self)
        self.shoot_days_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.shoot.setCompleter(self.shoot_days_completer)

    def do_publish(self):

        if self.shoot.text() == "":
            QtWidgets.QMessageBox.warning(self, "Error", "Please provide a shoot day name")
            return

        try:
            self.setCursor(QtCore.Qt.BusyCursor)

            self.progressBar.setVisible(True)
            self.progressBar.setMaximum(len(self.data['takes']))

            project_id = self.projects.currentData()
            project = {'type': 'Project', 'id': project_id}

            shoot_day = self.shoot.text()
            search = [('project', 'is', project), ("code", "is", shoot_day)]
            ret = self.sg.find("ShootDay", search, ["id", "code"])
            if ret:
                shoot_day = ret[0]
            else:
                shoot_day = self.sg.create("ShootDay", {'project': project, 'code': shoot_day})

            task_template_id = self.task_templates.currentData()

            added = 0
            updated = 0
            files = 0

            fields = self.sg.schema_field_read("MocapTake").keys()

            for row in self.data['takes']:

                # For each take

                self.progressBar.setValue(updated + added)
                self.progressBar.setFormat(row['takeName'] + " %p%")

                if row["takeName"] == "":
                    row["takeName"] = "???"

                # Mocap Take Entity

                row_data = {'project': project,
                            'sg_shoot_day': shoot_day,
                            'sg_n_g':       row["select"] == "NG",
                            'sg_select':    row["select"] in ["A", "B"],
                            'code':         row["takeName"],
                            'description':  row["description"] + "\nSelect: " + row["select"]
                            }

                if 'sg_tc_start' in fields:
                    row_data['sg_tc_start'] = row["start"]

                if 'sg_tc_end' in fields:
                    row_data['sg_tc_end'] = row["end"]

                if 'notes' in fields:
                    row_data['sg_notes'] = row["notes"]

                if 'sg_path_to_movie' in fields:
                    row_data['sg_path_to_movie'] = cmd.currentConfig["DataDirectory"]

                if 'sg_tc_marks' in fields:
                    name_timecodes = [f"{mark['name']}: {mark['timecode']}" for mark in row['marks']]
                    row_data['sg_tc_marks'] = ', '.join(name_timecodes)

                if task_template_id is not None:
                    row_data['task_template'] = {'type': 'TaskTemplate', 'id': task_template_id}

                search = [('project', "is", project),
                          ('sg_shoot_day', 'is', shoot_day),
                          ('code', 'is', row["takeName"])]

                ret = self.sg.find("MocapTake", search, ["id", "task_template"])
                if ret:
                    self.sg.update("MocapTake", ret[0]['id'], row_data)
                    updated += 1
                    row_id = ret[0]['id']
                else:
                    performers = []
                    if 'subjects' in row:
                        subjects = row['subjects']
                        if subjects:
                            for subject in subjects:
                                ret = self.sg.find("Performer", [('code', 'is', subject)], ["code"])
                                if ret:
                                    performers.append(ret[0])
                                else:
                                    performers.append(self.sg.create("Performer", {'code': subject, 'project': project}))

                    if performers:
                        row_data['performers'] = performers

                    notes = []

                    if len(row["notes"]) > 0:
                        notes.append(self.sg.create("Note", {'project': project, 'content': row["notes"]}))

                    info = ""
                    if 'marks' in row:
                        for mark in row["marks"]:
                            if 'name' in mark and 'timecode' in mark:
                                info += mark['timecode'] + " :" + mark['name'] + "\n"

                    if info:
                        notes.append(self.sg.create("Note", {'project': project, 'content': info}))

                    if notes:
                        row_data['notes'] = notes

                    ret = self.sg.create('MocapTake', row_data)
                    row_id = ret["id"]
                    added += 1

                has_thumb = False

                # Version Entity (linked)
                take_name = row["takeName"].replace('-', '_')
                for full_path in peel.movies(take_name):
                    print("Upload: " + str(full_path))

                    movie_dir, movie_name = os.path.split(full_path)
                    device_dir = os.path.split(movie_dir)[1]
                    movie_name = os.path.splitext(movie_name)[0]
                    movie_code = device_dir + " " + movie_name

                    filter = [('project', 'is', project),
                              ('code', 'is', movie_code),
                              ('entity', 'is', {'type': 'MocapTake', 'id': row_id})]

                    # Check to see if it already exists
                    ret = self.sg.find("Version", filter, ["id"])
                    if ret:
                        continue

                    # Create the version entity
                    data = {'project': project,
                            'code': movie_code,
                            'description': row["description"],
                            'entity': {'type': 'MocapTake', 'id': row_id}
                            }
                    result = self.sg.create('Version', data)

                    if self.compress_cb.isChecked():
                        # Make a h264
                        d = os.path.join(movie_dir, ".h264")
                        if not os.path.isdir(d):
                            os.mkdir(d)

                        movie_path = os.path.join(movie_dir, ".h264", movie_name + ".mp4")
                        if not os.path.isfile(movie_path):
                            self.progressBar.setFormat("Compressing Video %p%")
                            movie.make_h264(full_path, movie_path)
                    else:
                        movie_path = full_path

                    self.progressBar.setFormat("Uploading %p")
                    self.sg.upload("Version", result["id"], movie_path, "sg_uploaded_movie", movie_name)

                    if not has_thumb:
                        self.sg.upload_thumbnail("MocapTake", row_id, peel.movie.make_thumb(movie_path))
                        has_thumb = True

                    files += 1

            self.progressBar.setValue(self.progressBar.maximum())
            self.progressBar.setFormat("Done")

            QtWidgets.QMessageBox.information(self, "Takes", "%d added, %d updated, %d files uploaded" % (added, updated, files))

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            raise e

        finally:
            self.unsetCursor()

        self.close()


def gui():

    for k in ['ShotgunUrl', 'ShotgunScript', 'ShotgunKey']:
        if k not in cmd.currentConfig:
            print("Missing config key: " + k)
            return

    config = cmd.currentConfig
    url = config['ShotgunUrl']
    script = config['ShotgunScript']
    key = config['ShotgunKey']

    if url.startswith("http://") or url.startswith("https://"):
        url = 'https://' + urllib.parse.urlparse(url).hostname
    else:
        url = 'https://' + url

    sg = shotgun_api3.Shotgun(url, script_name=script, api_key=key)
    w = UploadGui(sg, cmd.getCurrentFile(), cmd.getMainWindow())
    w.show()
    w.exec_()
    w.deleteLater()
    #w.exec_()
    #return w



