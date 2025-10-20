from dataclasses import dataclass
import sys
import os
import json
from PyQt6 import uic
from PyQt6.QtCore import QTimer, pyqtSlot, QPoint, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QWidget
)

class Model:
    #константы класса
    __min = 0
    __max = 100


    def __init__(self, a=1, b=50, c=100):
        self.__subscribers = []
        a, b, c = self.__fixRelations(a, b, c)
        self.__a = a
        self.__b = b
        self.__c = c
        print(f"Initialized with a={a}, b={b}, c={c}")

    def __notifySubscribers(self, a, b, c):
        for update_view in self.__subscribers:
            update_view(a, b, c)
            print(f"Notified subscriber with a={a}, b={b}, c={c}")

    def subscribe(self, callback):
        self.__subscribers.append(callback)

    @property
    def a(self):
        return self.__a
    @property
    def b(self):
        return self.__b
    @property
    def c(self):
        return self.__c
    
    def setABC(self, a, b, c):
        try:
            a = int(a)
            b = int(b)
            c = int(c)
        except ValueError:
            return
        if self.__a != a:
            changable = 'a'
        elif self.__b != b:
            changable = 'b'
        elif self.__c != c:
            changable = 'c'
        a, b, c = self.__fixRelations(a, b, c, changable=changable)
        if (a, b, c) != (self.__a, self.__b, self.__c):
            self.__a = a
            self.__b = b
            self.__c = c
            print(f"Set to a={a}, b={b}, c={c}")
            self.__notifySubscribers(a, b, c)

    def __fixRelations(self, a, b, c, changable=None):
        old_vars = (a, b, c)

        #обрабатываем всегда
        if a < Model.__min:
            a = Model.__min
        if a > Model.__max:
            a = Model.__max
        if b < Model.__min:
            b = Model.__min
        if c > Model.__max:
            c = Model.__max
        if c < Model.__min:
            c = Model.__min

        #разрешающее поведение
        if a > c:
            if changable == 'a':
                c = a
            elif changable == 'c':
                a = c
            else:
                a = c
        if b < a:
            if changable == 'b':
                # b - запрещающее поведение
                b=a
            elif changable == 'a':
                b = a
            else:
                b = a
        if b > c:
            if changable == 'b':
                # b - запрещающее поведение
                b=c
            elif changable == 'c':
                b = c
            else:
                b = c

        if old_vars != (a, b, c):
            print(f"Fixed relations: {old_vars} -> {(a, b, c)}")
            self.__notifySubscribers(a, b, c)

        return a, b, c
    
    def save(self, filename="model_state.json"):
        data = {'a': self.a, 'b': self.b, 'c': self.c}
        with open(filename, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def load(stream):
        data = json.load(stream)
        return Model(data.get('a', 1), data.get('b', 50), data.get('c', 100))
        


class Widget(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        if os.path.exists(savefile):
            self.model = Model.load(open(savefile))
        else:
            self.model = Model()

        self.model.subscribe(self.update_view)
        self.update_view(self.model.a, self.model.b, self.model.c)

        self.show()

        self.lineEdit_1.textChanged.connect(lambda text: self.model.setABC(text, self.model.b, self.model.c))
        self.lineEdit_2.textChanged.connect(lambda text: self.model.setABC(self.model.a, text, self.model.c))
        self.lineEdit_3.textChanged.connect(lambda text: self.model.setABC(self.model.a, self.model.b, text))
        self.spinBox_1.valueChanged.connect(lambda value: self.model.setABC(value, self.model.b, self.model.c))
        self.spinBox_2.valueChanged.connect(lambda value: self.model.setABC(self.model.a, value, self.model.c))
        self.spinBox_3.valueChanged.connect(lambda value: self.model.setABC(self.model.a, self.model.b, value))
        self.horizontalSlider_1.valueChanged.connect(lambda value: self.model.setABC(value, self.model.b, self.model.c))
        self.horizontalSlider_2.valueChanged.connect(lambda value: self.model.setABC(self.model.a, value, self.model.c))
        self.horizontalSlider_3.valueChanged.connect(lambda value: self.model.setABC(self.model.a, self.model.b, value))


    def update_view(self, a, b, c):
    # Отключаем сигналы, чтобы избежать рекурсии
        self.lineEdit_1.blockSignals(True)
        self.lineEdit_2.blockSignals(True)
        self.lineEdit_3.blockSignals(True)
        self.spinBox_1.blockSignals(True)
        self.spinBox_2.blockSignals(True)
        self.spinBox_3.blockSignals(True)
        self.horizontalSlider_1.blockSignals(True)
        self.horizontalSlider_2.blockSignals(True)
        self.horizontalSlider_3.blockSignals(True)

        self.lineEdit_1.setText(str(a))
        self.lineEdit_2.setText(str(b))
        self.lineEdit_3.setText(str(c))
        self.spinBox_1.setValue(a)
        self.spinBox_2.setValue(b)
        self.spinBox_3.setValue(c)
        self.horizontalSlider_1.setValue(a)
        self.horizontalSlider_2.setValue(b)
        self.horizontalSlider_3.setValue(c)

        self.lineEdit_1.blockSignals(False)
        self.lineEdit_2.blockSignals(False)
        self.lineEdit_3.blockSignals(False)
        self.spinBox_1.blockSignals(False)
        self.spinBox_2.blockSignals(False)
        self.spinBox_3.blockSignals(False)
        self.horizontalSlider_1.blockSignals(False)
        self.horizontalSlider_2.blockSignals(False)
        self.horizontalSlider_3.blockSignals(False)

    def closeEvent(self, event):
        self.model.save(savefile)
        super().closeEvent(event)


if __name__ == "__main__":
    savefile = "state.json"


    app = QApplication(sys.argv)
    window = Widget()
    sys.exit(app.exec())