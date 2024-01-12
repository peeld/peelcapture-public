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


def set_text1(value):
    getInstance().set_text1(value)


def set_text2(value):
    getInstance().set_text2(value)


def set_timecode_enabled(value):
    getInstance().set_timecode_enabled(value)


def set_take_enabled(value):
    getInstance().set_timecode_enabled(value)


class SlateWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.text = ""

    def set_text(self, value):
        self.text = value
        self.repaint()

    def paintEvent(self, e):

        super().paintEvent(e)

        painter = QtGui.QPainter(self)

        painter.setBrush(QtGui.QBrush(QtCore.Qt.black));
        painter.drawRect(self.rect())

        painter.setPen(QtGui.QPen(QtCore.Qt.white))

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

        self.setLayout(layout)

        self.resize(500, 350)

    def set_font(self, font_family, font_style):
        db = QtGui.QFontDatabase()
        f = db.font(font_family, font_style, 12)
        self.setFont(f)
        self.timecode.setFont(f)
        self.take.setFont(f)
        self.label1.setFont(f)
        self.label2.setFont(f)

    def set_take(self, name):
        self.take.set_text(str(name))

    def set_text1(self, value):
        self.label1.set_text(str(value))

    def set_text2(self, value):
        self.label2.set_text(str(value))

    def set_timecode_enabled(self, value):
        self.timecode.setVisible(value)

    def set_take_enabled(self, value):
        self.take.setVisible(value)
