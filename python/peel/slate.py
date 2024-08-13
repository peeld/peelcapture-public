from PySide6 import QtWidgets, QtCore, QtGui

from PeelApp import cmd

INSTANCE = None


def getInstance():
    global INSTANCE
    if INSTANCE is None:
        INSTANCE = Slate(cmd.getMainWindow())
    return INSTANCE


def show(value):
    if value:
        getInstance().show()
    else:
        getInstance().hide()


def set_font(font_family, font_style):
    getInstance().set_font(font_family, font_style)


def set_take(name):
    getInstance().set_take(name)


def set_take_recording(name):
    getInstance().set_take_recording(name)


def stop():
    getInstance().stop()


def set_text1(value):
    getInstance().set_text1(value)


def set_text2(value):
    getInstance().set_text2(value)


def set_timecode_enabled(value):
    getInstance().set_timecode_enabled(value)


def set_take_enabled(value):
    getInstance().set_take_enabled(value)


class SlateWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.text = ""
        self.color = QtCore.Qt.white

    def set_text(self, value):
        self.text = value
        self.repaint()

    def set_color(self, color):
        self.color = color
        self.repaint()

    def red(self):
        self.set_color(QtGui.QColor(220, 22, 22))

    def grey(self):
        self.set_color(QtGui.QColor(128, 128, 128))

    def white(self):
        self.set_color(QtCore.Qt.white)

    def paintEvent(self, e):

        super().paintEvent(e)

        painter = QtGui.QPainter(self)

        painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
        painter.drawRect(self.rect())

        painter.setPen(QtGui.QPen(self.color))

        rect = self.rect()
        f = QtGui.QFont(self.font())
        fm = QtGui.QFontMetrics(f)
        text_size = fm.size(QtCore.Qt.TextSingleLine, self.text, 0)

        if text_size.width() == 0 or text_size.height() == 0:
            return

        factor = float(self.width()) / float(text_size.width())
        hfactor = float(self.height()) / (float(text_size.height()) * factor)
        if hfactor < 1:
            factor = float(self.height()) / float(text_size.height())

        f.setPointSize(f.pointSizeF() * factor * 0.9)
        painter.setFont(f)

        painter.drawText(rect, QtCore.Qt.AlignHCenter, self.text)



class Slate(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.last_take_name = None

        layout = QtWidgets.QVBoxLayout()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.timecode = cmd.timecodeWidget(self, "Courier New", "Regular")
        layout.addWidget(self.timecode)

        self.take = SlateWidget(self)
        layout.addWidget(self.take)

        self.label1 = SlateWidget(self)
        layout.addWidget(self.label1)

        self.label2 = SlateWidget(self)
        layout.addWidget(self.label2)

        self.last_take = SlateWidget(self)
        layout.addWidget(self.last_take)

        self.setLayout(layout)

        self.resize(500, 350)

    def closeEvent(self, e):
        # tell the main app to uncheck the menu item
        cmd.notifySlateClosed()

    def set_font(self, font_family, font_style):
        db = QtGui.QFontDatabase()
        f = db.font(font_family, font_style, 12)
        self.setFont(f)
        self.timecode.setFont(f)
        self.take.setFont(f)
        self.label1.setFont(f)
        self.label2.setFont(f)

        f2 = db.font(font_family, font_style, 9)
        self.last_take.setFont(f2)
        self.last_take.grey()

    def set_take(self, name):
        self.take.set_text(str(name))

    def set_take_recording(self, name):
        self.last_take_name = name
        self.take.set_text(str(name))
        self.take.red()

    def stop(self):
        if self.last_take_name:
            self.last_take.set_text("LAST: " + str(self.last_take_name))
            self.last_take_name = None
        self.take.white()

    def set_text1(self, value):
        self.label1.set_text(str(value))

    def set_text2(self, value):
        self.label2.set_text(str(value))

    def set_timecode_enabled(self, value):
        self.timecode.setVisible(value)

    def set_take_enabled(self, value):
        self.take.setVisible(value)
