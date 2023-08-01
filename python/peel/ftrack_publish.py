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
from PeelApp import cmd
from importlib import reload

import ftrack_api

from peel import ftrack_publish
reload(ftrack_publish)

g = ftrack_publish.FTrackGui(cmd.getMainWindow())
g.show()
"""

from PeelApp import cmd
import ftrack_api
from PySide6 import QtWidgets, QtCore
import urllib.parse
import json
from peel import movie
import peel


class FTrackGui(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FTrackGui, self).__init__(parent)

        self.settings = QtCore.QSettings("PeelDev", "PeelCapture")

        config = cmd.currentConfig

        self.data = {}
        self.load_data()

        # Ftrack api can be funny about the formatting of the url, so we need to sanitize it first
        url = config['FTrackUrl']
        if url.startswith("http://") or url.startswith("https://"):
            self.url = 'https://' + urllib.parse.urlparse(url).hostname
        else:
            self.url = 'https://' + url

        self.user = config['FTrackUser']
        self.key = config['FTrackKey']

        try:
            self.session = ftrack_api.Session(server_url=self.url, api_user=self.user, api_key=self.key)
            self.projects = self.session.query('Project where status is active')
        except Exception as e:
            label = QtWidgets.QLabel("Could not connect to FTrack.. check the settings?")
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(label)
            self.setLayout(layout)
            return

        layout = QtWidgets.QFormLayout()

        # Project
        self.project = QtWidgets.QComboBox()

        selected = None
        for row, project in enumerate(self.projects):
            self.project.addItem(project['full_name'])
            if 'project' in self.data and project['full_name'].lower() == self.data['project'].lower():
                selected = row

        if selected:
            self.project.setCurrentIndex(selected)

        layout.addRow("Project", self.project)

        # Schema
        self.schema = QtWidgets.QComboBox()
        self.schema.addItems(["Scene/Take", "Scene/Shot/Take", "Sequence/Shot"])

        layout.addRow("Schema", self.schema)

        # Scene

        self.shoot = QtWidgets.QLineEdit()
        if 'shoot' in self.data:
            self.shoot.setText(self.data['shoot'])
        layout.addRow("Shoot", self.shoot)

        # Buttons

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.okay = QtWidgets.QPushButton("Publish")
        self.okay.pressed.connect(self.do_publish)
        buttons.addWidget(self.okay)
        buttons.addStretch(1)
        layout.addItem(buttons)

        self.setLayout(layout)

    def load_data(self):
        fp = open(cmd.getCurrentFile(), 'r')
        self.data = json.load(fp)
        fp.close()

    def current_project(self):
        row = self.project.currentIndex()
        if row == -1:
            return None
        return self.projects[row]

    def new_entity(self, entity, parent_ref, name, description):
        try:
            item = self.session.create(entity, {'name': name})
            item['description'] = description
            item['parent'] = parent_ref
            self.session.commit()
            return item
        except ftrack_api.exception.ServerError:
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not create {entity} entity - is it enabled?")
            raise

    def new_scene(self, parent_ref, name, description=""):
        project_ref = self.current_project()
        if project_ref is None:
            return
        return self.new_entity("Scene", project_ref, name, description)

    def new_episode(self, name, description=""):
        project_ref = self.current_project()
        if project_ref is None:
            return
        return self.new_entity("Episode", project_ref, name, description)

    def new_sequence(self, parent_ref, name, description=""):
        return self.new_entity("Sequence", parent_ref, name, description)

    def new_shot(self, parent_ref, name, description=""):
        return self.new_entity("Shot", parent_ref, name, description)

    def add_take(self, entity, parent, row):

        project = self.current_project()
        if project is None:
            return

        if parent is None:
            return

        item = self.session.create(entity)
        item['name'] = row['takeName']
        item['parent'] = parent
        item['description'] = row['description']
        # This generates an error: "TypedContext dates must be within project start and end dates."
        #item['start_date'] = row['start']
        #item['end_date'] = row['end']
        item.create_note(row['notes'], author=None)
        item['metadata']['select'] = row['select']
        item['metadata']['subjects'] = ','.join(row['subjects'])
        item['metadata']['marks'] = ','.join(row['marks'])
        item['metadata']['shot'] = row['shotName']
        item['metadata']['take'] = row['take']

        mov = peel.movies(row['takeName'])
        if mov:
            thumb = movie.make_thumb(mov[0])
            item.create_thumbnail(thumb)

        #sequence['children'].append(new_shot)

        self.session.commit()
        return item

    def find_or_create_episode(self, project_id, episode):
        found_episode = self.session.query(f"Episode where project.id like '{project_id}' and name like '{episode}'")
        if len(found_episode) > 0:
            return found_episode.one()
        else:
            return self.new_episode(episode)

    def find_or_create_sequence(self, parent_ref, sequence):
        q = f"Sequence where parent.id  is '{parent_ref['id']}' and name like '{sequence}'"
        found_sequence = self.session.query(q)
        if len(found_sequence) > 0:
            return found_sequence.one()
        else:
            return self.new_sequence(parent_ref, sequence)

    def find_or_create_scene(self, parent_ref, scene):
        q = f"Scene where parent.id like '{parent_ref['id']}' and name like '{scene}'"
        found = self.session.query(q)
        if len(found) > 0:
            return found.one()
        else:
            return self.new_scene(parent_ref, scene)

    def find_or_create_shot(self, parent_ref, shot):
        q = f"Shot where parent.id like '{parent_ref['id']}' and name like '{shot}'"
        found = self.session.query(q)
        if len(found) > 0:
            return found.one()
        else:
            return self.new_shot(parent_ref, shot)

    def do_publish(self):

        try:
            self.setCursor(QtCore.Qt.BusyCursor)

            self.load_data()

            shoot = self.shoot.text()
            project = self.current_project()
            project_id = project['id']

            if not shoot:
                QtWidgets.QMessageBox.warning(self, "Error", "Please set the shoot day name")
                return

            schema = self.schema.currentText()

            take_type = None
            shot_type = None
            shoot_ref = None

            if schema == "Scene/Take":
                take_type = "Take"
                shoot_ref = self.find_or_create_scene(project, shoot)

            if schema == "Scene/Shot/Take":
                shot_type = "Shot"
                take_type = "Take"
                shoot_ref = self.find_or_create_scene(project, shoot)

            if schema == "Sequence/Shot":
                take_type = "Shot"
                shoot_ref = self.find_or_create_sequence(project, shoot)

            for row in self.data['takes']:

                if shot_type == "Shot":
                    parent_ref = self.find_or_create_shot(shoot_ref, row['shotName'])
                else:
                    parent_ref = shoot_ref

                q = f"{take_type} where parent.id is '{parent_ref['id']}' and name like '{row['takeName']}'"
                found_shot = self.session.query(q)

                if len(found_shot) == 0:
                    self.add_take(take_type, parent_ref, row)
        finally:
            self.unsetCursor()

        QtWidgets.QMessageBox.information(self, "FTrack", "Update Complete")


def gui():

    g = FTrackGui(cmd.getMainWindow())
    g.show()
    g.exec_()
    g.deleteLater()




