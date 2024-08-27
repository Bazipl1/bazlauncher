from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QSpacerItem, QSizePolicy, QProgressBar, QPushButton, QApplication, QMainWindow, QFileDialog
from PyQt5.QtGui import QPixmap

from minecraft_launcher_lib.utils import get_minecraft_directory, get_version_list
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.command import get_minecraft_command

from random_username.generate import generate_username
from uuid import uuid1

from subprocess import call
from sys import argv, exit
import os
import zipfile

# Переменная для хранения пути к директории Minecraft
minecraft_directory = ''

class LaunchThread(QThread):
    launch_setup_signal = pyqtSignal(str, str)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)

    version_id = ''
    username = ''

    progress = 0
    progress_max = 0
    progress_label = ''

    def __init__(self):
        super().__init__()
        self.launch_setup_signal.connect(self.launch_setup)

    def launch_setup(self, version_id, username):
        self.version_id = version_id
        self.username = username

    def update_progress_label(self, value):
        self.progress_label = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def update_progress(self, value):
        self.progress = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def update_progress_max(self, value):
        self.progress_max = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def run(self):
        self.state_update_signal.emit(True)

        version_path = os.path.join(minecraft_directory, "versions", self.version_id)
        
        # Проверяем, существует ли директория Minecraft
        if not os.path.exists(minecraft_directory):
            os.makedirs(minecraft_directory)
            print(f"Created directory: {minecraft_directory}")
        
        # Проверяем, установлена ли версия Minecraft
        if not os.path.exists(version_path):
            install_minecraft_version(
                versionid=self.version_id,
                minecraft_directory=minecraft_directory,
                callback={
                    'setStatus': self.update_progress_label,
                    'setProgress': self.update_progress,
                    'setMax': self.update_progress_max
                }
            )

        if self.username == '':
            self.username = generate_username()[0]

        options = {
            'username': self.username,
            'uuid': str(uuid1()),
            'token': ''
        }

        try:
            # Выводим информацию для отладки
            print(f"Version ID: {self.version_id}")
            print(f"Minecraft Directory: {minecraft_directory}")
            print(f"Version Path: {version_path}")

            command = get_minecraft_command(self.version_id, minecraft_directory, options)
            command.append('--offline')  # Добавляем параметр для оффлайн режима
            print(f"Command: {command}")

            # Проверяем наличие JAR-файла
            jar_path = os.path.join(version_path, f"{self.version_id}.jar")
            if not os.path.exists(jar_path):
                print(f"JAR file not found: {jar_path}")
                return

            # Проверяем, существует ли основной класс в JAR-файле
            with zipfile.ZipFile(jar_path, 'r') as jar_file:
                if 'net/minecraft/client/main/Main.class' not in jar_file.namelist():
                    print(f"Main class not found in JAR file: {jar_path}")
                    return

            call(command)
        except Exception as e:
            print(f"Error launching Minecraft: {e}")

        self.state_update_signal.emit(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Создаём папку .bazlauncher в домашней директории пользователя
        home_directory = os.path.expanduser("~")
        global minecraft_directory
        minecraft_directory = os.path.join(home_directory, ".bazlauncher")

        if not os.path.exists(minecraft_directory):
            os.makedirs(minecraft_directory)
            print(f"Created directory: {minecraft_directory}")
        else:
            print(f"Directory already exists: {minecraft_directory}")

        self.setWindowTitle("Minecraft BazLauncher")
        self.resize(300, 400)
        self.centralwidget = QWidget(self)

        self.logo = QLabel(self.centralwidget)
        self.logo.setMaximumSize(QSize(256, 256))
        self.logo.setPixmap(QPixmap('assets/icon.png'))
        self.logo.setScaledContents(True)

        self.titlespacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.username = QLineEdit(self.centralwidget)
        self.username.setPlaceholderText('Username')

        self.version_select = QComboBox(self.centralwidget)
        self.update_version_options()

        self.progress_spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.start_progress_label = QLabel(self.centralwidget)
        self.start_progress_label.setVisible(False)
        self.start_progress = QProgressBar(self.centralwidget)
        self.start_progress.setVisible(False)

        self.start_button = QPushButton(self.centralwidget)
        self.start_button.setText('Play')
        self.start_button.clicked.connect(self.launch_game)

        self.browse_button = QPushButton(self.centralwidget)
        self.browse_button.setText('Select Minecraft Directory')
        self.browse_button.clicked.connect(self.select_directory)

        self.vertical_layout = QVBoxLayout(self.centralwidget)
        self.vertical_layout.setContentsMargins(15, 15, 15, 15)
        self.vertical_layout.addWidget(self.logo, 0, Qt.AlignHCenter)
        self.vertical_layout.addItem(self.titlespacer)
        self.vertical_layout.addWidget(self.username)
        self.vertical_layout.addWidget(self.version_select)
        self.vertical_layout.addWidget(self.browse_button)
        self.vertical_layout.addItem(self.progress_spacer)
        self.vertical_layout.addWidget(self.start_progress_label)
        self.vertical_layout.addWidget(self.start_progress)
        self.vertical_layout.addWidget(self.start_button)

        self.launch_thread = LaunchThread()
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)

        self.setCentralWidget(self.centralwidget)

    def update_version_options(self):
        """Обновление списка версий Minecraft"""
        try:
            versions = get_version_list()
            self.version_select.clear()
            for version in versions:
                self.version_select.addItem(version['id'])
        except Exception as e:
            print(f"Error fetching versions: {e}")

    def select_directory(self):
        """Открыть диалог для выбора директории Minecraft"""
        global minecraft_directory
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Minecraft Directory", "")
        if folder_selected:
            minecraft_directory = folder_selected
            print(f"Selected Minecraft Directory: {minecraft_directory}")

    def state_update(self, value):
        self.start_button.setDisabled(value)
        self.start_progress_label.setVisible(value)
        self.start_progress.setVisible(value)

    def update_progress(self, progress, max_progress, label):
        self.start_progress.setValue(progress)
        self.start_progress.setMaximum(max_progress)
        self.start_progress_label.setText(label)

    def launch_game(self):
        if not minecraft_directory:
            print("Minecraft directory not selected.")
            return
        self.launch_thread.launch_setup_signal.emit(self.version_select.currentText(), self.username.text())
        self.launch_thread.start()

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(argv)
    window = MainWindow()
    window.show()
    exit(app.exec_())
