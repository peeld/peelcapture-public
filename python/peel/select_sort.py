from PySide6 import QtWidgets, QtCore, QtGui
import os
import json
import shutil
from PeelApp import cmd


class SelectSort(QtWidgets.QDialog):
    def __init__(self, settings, parent):
        super(SelectSort, self).__init__(parent)
        self.data = None
        self.takeList = {}
        self.pcFile = os.path.basename(cmd.getCurrentFile()).split('/')[-1]

        self.selectList = None

        self.setWindowTitle("Select Sort " + self.pcFile)

        if settings is None:
            self.settings = QtCore.QSettings("PeelDev", "PeelCapture")
        else:
            self.settings = settings

        self.data_dir = None
        if "DataDirectory" in cmd.currentConfig:
            self.data_dir = cmd.currentConfig["DataDirectory"]

        layout = QtWidgets.QVBoxLayout()

        # File Path Browser
        file_layout = QtWidgets.QHBoxLayout()
        dest_label = QtWidgets.QLabel("Destination Folder: ")
        self.dest_dir = QtWidgets.QLineEdit()
        self.dest_dir.setText(str(self.data_dir))
        self.dest_dir_button = QtWidgets.QPushButton("...")
        self.dest_dir_button.released.connect(self.browse_directory)
        file_layout.addWidget(dest_label)
        file_layout.addWidget(self.dest_dir)
        file_layout.addWidget(self.dest_dir_button)
        layout.addItem(file_layout)

        # Take selections they want to be sorted
        select_layout = QtWidgets.QHBoxLayout()
        select_label = QtWidgets.QLabel("Selects: ")
        self.select_input = QtWidgets.QLineEdit()
        self.select_input.setText(settings.value("select_sort_selects", "A, B"))
        select_layout.addWidget(select_label)
        select_layout.addWidget(self.select_input)
        layout.addItem(select_layout)

        # Log
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setStyleSheet("background: #eee")
        layout.addWidget(self.log)

        self.log_message("Destination: the folder you want to sort the \"Select\" takes into.\n" \
                         "Selects: the selections you want to be sorted (e.g. A,B,NG)\n")
        # Buttons
        self.go_button = QtWidgets.QPushButton("Reorganize Files")
        self.go_button.released.connect(self.go)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.released.connect(self.teardown)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.go_button)
        button_layout.addWidget(self.close_button)

        layout.addItem(button_layout)

        self.setLayout(layout)

        self.resize(500, 300)

    # User chooses destination folder
    def browse_directory(self):
        d = cmd.currentConfig["DataDirectory"]
        ret = QtWidgets.QFileDialog.getExistingDirectory(self, "Shoot Dir", d)
        if ret:
            self.dest_dir.setText(ret)

    # create dictionary with (takeName, select)
    def load_peelcap_json(self):
        f = open(os.path.join(self.data_dir, self.pcFile))
        self.data = ''
        self.data = json.load(f)
        self.log_message("Loaded " + self.pcFile)

        # Check that takes is not empty
        if (self.data is None) or ("takes" not in self.data) or (len(self.data["takes"]) < 1):
            self.log_message("Error " + self.pcFile + " is empty or has no takes to sort.")
            return False
        for take in self.data["takes"]:
            select = take["select"]
            take_name = take["takeName"]
            self.takeList[take_name] = select
        return True

    def go(self):
        if self.load_peelcap_json() is False:
            return

        self.settings.setValue("select-sort-selects", self.select_input.text())

        self.selectList = [i.strip() for i in self.select_input.text().split(",")]

        devices = self.get_immediate_subdirectories(self.data_dir)

        for device in devices:
            device_dir = os.path.join(self.data_dir, device)
            for file in os.listdir(device_dir):
                file_name = os.path.splitext(file)[0]
                if file_name not in self.takeList:
                    continue
                select = self.takeList[file_name]
                if (select not in self.selectList) or (select == ""):
                    continue
                path = self.create_dir(self.dest_dir.text(), select)
                self.copy_over(select, device, file, os.path.join(device_dir, file), path)

    def get_immediate_subdirectories(self, a_dir):
        return [name for name in os.listdir(a_dir)
                if os.path.isdir(os.path.join(a_dir, name)) and (name not in self.selectList)]

    # Copies the file at filePath to destination dir and names the file {device}{select}_{takeName}
    def copy_over(self, select, device, file_name, file_path, dest):
        if os.path.isfile(file_path):
            new_name = device + select + "_" + file_name
            shutil.copyfile(file_path, os.path.join(dest, new_name))
            self.log_message("Copied " + new_name + " to " + dest)

    def create_dir(self, path, name):
        new_path = os.path.join(path, name)
        if not os.path.isdir(new_path):
            try:
                os.mkdir(new_path)
                self.log_message("Created " + name + " folder in " + path)
            except IOError as e:
                self.log_message("Error could not create " + name + " folder in " + path + "" + str(e))
                return
        return new_path

    def log_message(self, message):
        self.log.appendPlainText(message)
        print("> " + message)

    def teardown(self):
        self.close()



