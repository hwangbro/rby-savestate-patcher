from PySide2.QtCore import Qt
from PySide2.QtWidgets import *
from PySide2.QtGui import QFont
import os

from patch import *
from ROM import ROM
from game import BadGameRomException

label_font = QFont("Helvetica", 14, QFont.Bold)
label_font2 = QFont("Helvetica", 12, QFont.Bold)


def Run():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    main = PromptWindow()
    main.show()
    app.exec_()


class PromptWindow(QWidget):
    def __init__(self, parent=None):
        super(PromptWindow, self).__init__(parent)

        self.setWindowTitle("Pokemon RBY State Flasher v1.4")
        self.layout = QVBoxLayout()
        self.label = QLabel(f"Please open a vanilla \nRed/Blue or Yellow ROM to start")
        self.label.setFont(label_font)
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.setAlignment(self.label, Qt.AlignHCenter)

        self.open_btn = QPushButton("Open ROM...")
        self.open_btn.setMaximumWidth(100)
        self.open_btn.clicked.connect(self.open_rom_btn_clicked)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.open_btn)
        self.layout.setAlignment(self.open_btn, Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setFixedSize(self.sizeHint())

    def open_rom_btn_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load ROM", "", "ROM File (*.gb *.gbc)"
        )
        if file_path:
            try:
                self.flash_window = FlashWindow(file_path)
                self.flash_window.show()
                self.close()
            except BadGameRomException:
                self.error_window = MessageWindow(
                    "Invalid ROM, could not read. Try another..."
                )
                self.error_window.show()


class MessageWindow(QWidget):
    def __init__(self, message, parent=None):
        super(MessageWindow, self).__init__(parent)

        self.layout = QVBoxLayout()
        self.label = QLabel(message)
        self.label.setFont(label_font)
        self.layout.addWidget(self.label)

        self.close_btn = QPushButton("OK")
        self.close_btn.clicked.connect(self.closed_btn_clicked)
        self.close_btn.setMaximumWidth(50)
        self.layout.addWidget(self.close_btn)
        self.layout.setAlignment(self.close_btn, Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setFixedSize(self.sizeHint())

    def closed_btn_clicked(self):
        self.close()


class FlashWindow(QWidget):
    def __init__(self, file_path, parent=None):
        self.existingSSRomPath = None
        super(FlashWindow, self).__init__(parent)
        self.setWindowTitle("Pokemon RBY State Flasher v1.4")

        self.rom = ROM(file_path)
        self.patch = Patch(self.rom)

        self.layout = QGridLayout()
        self.label = QLabel(f"Current ROM: {self.rom.game.type}")
        self.label.setFont(label_font2)
        self.layout.addWidget(self.label, 0, 1, 1, -1)
        self.layout.setAlignment(self.label, Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setFixedSize(450, 300)

        self.add_item_btn = QPushButton("Add States")
        self.add_item_btn.clicked.connect(self.add_state)
        self.layout.addWidget(self.add_item_btn, 1, 1, 1, 2)

        self.erase_item_btn = QPushButton("Erase State")
        self.erase_item_btn.clicked.connect(self.delete_list_item)
        self.layout.addWidget(self.erase_item_btn, 1, 3, 1, 2)

        self.rename_btn = QPushButton("Rename State")
        self.rename_btn.clicked.connect(self.rename_btn_clicked)
        self.layout.addWidget(self.rename_btn, 1, 5, 1, 2)

        self.load_label = QLabel("Load states from an existing ROM")
        self.load_label.setFont(label_font2)
        self.layout.addWidget(self.load_label, 2, 1, 1, -1)
        self.layout.setAlignment(self.load_label, Qt.AlignHCenter)
        self.load_btn = QPushButton("Open ROM...")
        self.load_btn.clicked.connect(self.load_btn_clicked)
        self.layout.addWidget(self.load_btn, 3, 1, 1, 3)

        self.save_btn = QPushButton("Save As...")
        self.save_btn.clicked.connect(self.save_btn_clicked)
        self.layout.addWidget(self.save_btn, 3, 4, 1, 3)

        self.state_list = QListWidget()
        self.state_list.setDefaultDropAction(Qt.MoveAction)
        self.state_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.layout.addWidget(self.state_list, 0, 0, -1, 1)

        self.layout.setAlignment(self.load_label, Qt.AlignHCenter | Qt.AlignBottom)

    def add_state(self):
        filePaths, _ = QFileDialog.getOpenFileNames(
            self, "Load SaveStates", "", "Gambatte Quick Save Files (*.gqs)"
        )
        for filePath in filePaths:
            if self.state_list.count() >= self.rom.game.max_states:
                self.error_message = MessageWindow("Maximum number of states reached.")
                self.error_message.show()
                return

            name = os.path.basename(filePath)[:-4]
            State = make_state(name, filePath, self.rom.game.cgb)

            item = QListWidgetItem(State.get_name())
            item.setData(0x100, State)
            row = (
                self.state_list.currentRow()
                if self.state_list.selectedItems()
                else self.state_list.count()
            )
            self.state_list.insertItem(row, item)

    def rename_btn_clicked(self):
        if self.state_list.selectedItems():
            item = self.state_list.currentItem()
            self.RenameWindow = RenameWindow(item)
            self.RenameWindow.show()

    def save_btn_clicked(self):
        states = {}
        for i in range(self.state_list.count()):
            states[i] = self.state_list.item(i).data(0x100)

        self.patch.states = states
        self.patch.inject_all_states()

        fileName, _ = QFileDialog.getSaveFileName(
            self, "Save ROM", "", "ROM File (*.gbc *.gb)"
        )
        message = "File has been saved successfully"
        if fileName:
            try:
                with open(fileName, "wb") as f:
                    f.write(self.patch.rom)
            except:
                message = "Something went wrong."

            self.SaveConfirmation = MessageWindow(message)
            self.SaveConfirmation.show()

    def update_list(self):
        self.state_list.clear()
        for idx, state in self.patch.states.items():
            item = QListWidgetItem(state.get_name())
            item.setData(0x100, state)
            self.state_list.addItem(item)

    def load_btn_clicked(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Load Existing SaveState ROM", "", "ROM File (*.gb *.gbc)"
        )
        if filePath:
            self.patch.extract_all_states(filePath)
            self.update_list()

    def delete_list_item(self):
        if self.state_list.selectedItems():
            item = self.state_list.currentItem()
            self.state_list.takeItem(self.state_list.row(item))


class RenameWindow(QWidget):
    def __init__(self, item, parent=None):
        super(RenameWindow, self).__init__(parent, Qt.WindowCloseButtonHint)
        self.setWindowTitle("Rename State")

        self.layout = QGridLayout()
        self.item = item

        self.label = QLabel("Enter new name:")
        self.state_name_box = QLineEdit(item.data(0x100).get_name())
        self.state_name_box.setMaxLength(20)
        self.state_name_box.selectAll()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_btn_clicked)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.ok_btn_clicked)

        self.layout.addWidget(self.label, 0, 0, 1, -1)
        self.layout.addWidget(self.state_name_box, 1, 0, 1, -1)
        self.layout.addWidget(self.cancel_btn, 2, 0, 1, 1)
        self.layout.addWidget(self.ok_btn, 2, 1, 1, 1)
        self.setLayout(self.layout)

    def cancel_btn_clicked(self):
        self.close()

    def ok_btn_clicked(self):
        if self.state_name_box.text().strip() == "":
            return
        self.item.data(0x100).set_name(self.state_name_box.text())
        self.item.setText(self.item.data(0x100).get_name())
        self.close()


if __name__ == "__main__":
    Run()
