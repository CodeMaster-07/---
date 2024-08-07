import sys
import socket
import os
import requests
import time
import json
import mysql.connector
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGridLayout, QMainWindow, QDialog, QPushButton, QSizePolicy, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QDateTime, QThread, pyqtSignal, QProcess, QCoreApplication
from PyQt5.QtGui import QColor, QFont, QMovie
from datetime import datetime

SERVER_URL = "http://192.168.0.5:5000"

class RackSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select Rack Number')
        self.setGeometry(100, 100, 800, 400)
        self.setStyleSheet("background-color: grey;")
        layout = QVBoxLayout()

        self.selected_rack_number = None
        self.buttons = []

        rack_label = QLabel("Select Rack Number")
        rack_label.setAlignment(Qt.AlignCenter)
        rack_label.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(rack_label)

        button_layout = QHBoxLayout()
        for i in range(1, 11):
            button = QPushButton(str(i))
            button.setFixedSize(100, 100)
            button.setStyleSheet("background-color: white; color: black; font-size: 20px;")
            button.clicked.connect(lambda _, b=button, n=i: self.select_rack_number(b, n))
            self.buttons.append(button)
            button_layout.addWidget(button)

        layout.addLayout(button_layout)

        self.ok_button = QPushButton('OK')
        self.ok_button.setStyleSheet("background-color: blue; color: white; font-size: 20px;")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def select_rack_number(self, button, number):
        self.selected_rack_number = number
        for b in self.buttons:
            b.setStyleSheet("background-color: white; color: black; font-size: 20px;")
        button.setStyleSheet("background-color: green; color: black; font-size: 20px;")

    def get_selected_rack_number(self):
        return self.selected_rack_number

class RackModeSelectionDialog(QDialog):
    def __init__(self, parent=None, rack_number=None):
        super().__init__(parent)
        self.setWindowTitle('Select Rack Mode')
        self.setGeometry(100, 100, 800, 400)
        self.setStyleSheet("background-color: grey;")
        self.rack_number = rack_number

        layout = QVBoxLayout()

        mode_label = QLabel(f"Rack Number : {self.rack_number}")
        mode_label.setAlignment(Qt.AlignCenter)
        mode_label.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(mode_label)

        self.selected_mode = None

        button_layout = QHBoxLayout()
        self.buttons = {}

        for mode in ["rack_mode", "center_mode"]:
            button = QPushButton(mode.capitalize().replace('_', ' '))
            button.setFixedSize(200, 100)
            button.setStyleSheet("background-color: white; color: black; font-size: 20px;")
            button.clicked.connect(lambda _, b=button, m=mode: self.select_mode(b, m))
            self.buttons[mode] = button
            button_layout.addWidget(button)

        layout.addLayout(button_layout)

        self.ok_button = QPushButton('OK')
        self.ok_button.setStyleSheet("background-color: blue; color: white; font-size: 20px;")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def select_mode(self, button, mode):
        self.selected_mode = mode
        for b in self.buttons.values():
            b.setStyleSheet("background-color: white; color: black; font-size: 20px;")
        button.setStyleSheet("background-color: green; color: black; font-size: 20px;")

    def get_selected_mode(self):
        return self.selected_mode

class BatteryDetailDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)
        try:
            self.setWindowTitle('Battery Detail')
            self.setGeometry(100, 100, 800, 600)
            layout = QGridLayout()
            layout.setContentsMargins(20, 10, 20, 10)

            labels = [
                "Rack Number", "USB Port", "Battery Status", "Battery Level", "Total Voltage",
                "Cell Voltage 1", "Cell Voltage 2", "Cell Voltage 3", "Cell Voltage 4", 
                "Cell Voltage 5", "Cell Voltage 6", "Cell Voltage 7", "Cell Temperature", "Created At", "Code Description"
            ]
            
            self.battery_data_keys = {
                "Rack Number": "rack_number",
                "USB Port": "usb_port_number",
                "Battery Status": "battery_status",
                "Battery Level": "battery_level",
                "Total Voltage": "battery_voltage",
                "Cell Voltage 1": "cell_voltage1",
                "Cell Voltage 2": "cell_voltage2",
                "Cell Voltage 3": "cell_voltage3",
                "Cell Voltage 4": "cell_voltage4",
                "Cell Voltage 5": "cell_voltage5",
                "Cell Voltage 6": "cell_voltage6",
                "Cell Voltage 7": "cell_voltage7",
                "Cell Temperature": "cell_temperature",
                "Created At": "created_at",
                "Code Description": "code_description"
            }

            self.value_labels = {}

            font = QFont("Arial", 14, QFont.Bold)

            for i, label in enumerate(labels):
                label_widget = QLabel(label)
                label_widget.setFont(font)
                label_widget.setStyleSheet("color: black;")
                layout.addWidget(label_widget, i, 0)
                value_widget = QLabel('N/A')
                value_widget.setFont(font)
                value_widget.setStyleSheet("color: black;")
                value_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                value_widget.setMinimumWidth(200)
                layout.addWidget(value_widget, i, 1)
                self.value_labels[label] = value_widget

            self.ok_button = QPushButton('OK')
            self.ok_button.setFont(font)
            self.ok_button.setStyleSheet("color: black;")
            self.ok_button.clicked.connect(self.hide)
            layout.addWidget(self.ok_button, len(labels) + 1, 1, 1, 1)
            self.setLayout(layout)
            self.setFixedSize(self.sizeHint())
        except Exception as e:
            print(f"Exception in BatteryDetailDialog __init__: {e}")

    def update_data(self, battery_data):
        try:
            for label, key in self.battery_data_keys.items():
                value = battery_data.get(key, 'N/A')
                self.value_labels[label].setText(str(value))
        except Exception as e:
            print(f"Exception in BatteryDetailDialog update_data: {e}")

    def showEvent(self, event):
        try:
            super().showEvent(event)
            self.move(self.parent().geometry().center() - self.rect().center())
        except Exception as e:
            print(f"Exception in BatteryDetailDialog showEvent: {e}")

class IPAddressInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)
        try:
            self.setWindowTitle('IP Address Input')
            self.setGeometry(100, 100, 600, 400)
            layout = QVBoxLayout()

            self.ip_inputs = []
            for i in range(10):
                input_layout = QHBoxLayout()
                label = QLabel(f"RAZ{i+1} IP:")
                input_layout.addWidget(label)
                ip_input = QHBoxLayout()
                for j in range(4):
                    octet_input = QLineEdit()
                    octet_input.setMaxLength(3)
                    octet_input.setFixedWidth(50)
                    octet_input.setAlignment(Qt.AlignCenter)
                    octet_input.installEventFilter(self)
                    ip_input.addWidget(octet_input)
                    self.ip_inputs.append(octet_input)
                    if j < 3:
                        ip_input.addWidget(QLabel("."))
                input_layout.addLayout(ip_input)
                layout.addLayout(input_layout)

            self.load_ip_config()

            self.ok_button = QPushButton('OK')
            self.ok_button.setStyleSheet("color: black;")
            self.ok_button.clicked.connect(self.save_and_accept)
            layout.addWidget(self.ok_button)
            self.setLayout(layout)
            self.setFixedSize(self.sizeHint())
        except Exception as e:
            print(f"Exception in IPAddressInputDialog __init__: {e}")

    def eventFilter(self, obj, event):
        try:
            if event.type() == event.KeyPress and obj in self.ip_inputs:
                idx = self.ip_inputs.index(obj)
                if event.key() in (Qt.Key_0, Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9):
                    if len(obj.text()) == 2:
                        if idx < len(self.ip_inputs) - 1:
                            self.ip_inputs[idx + 1].setFocus()
                elif event.key() == Qt.Key_Backspace:
                    if len(obj.text()) == 0 and idx > 0:
                        self.ip_inputs[idx - 1].setFocus()
            return super().eventFilter(obj, event)
        except Exception as e:
            print(f"Exception in IPAddressInputDialog eventFilter: {e}")

    def get_ip_addresses(self):
        try:
            ip_addresses = []
            for i in range(0, len(self.ip_inputs), 4):
                ip_address = ".".join(ip.text() for ip in self.ip_inputs[i:i+4])
                ip_addresses.append(ip_address)
            return ip_addresses
        except Exception as e:
            print(f"Exception in IPAddressInputDialog get_ip_addresses: {e}")

    def save_and_accept(self):
        try:
            self.save_ip_config()
            self.accept()
        except Exception as e:
            print(f"Exception in IPAddressInputDialog save_and_accept: {e}")

    def save_ip_config(self):
        try:
            ip_addresses = self.get_ip_addresses()
            with open('ip_config.json', 'w') as f:
                json.dump(ip_addresses, f)
        except Exception as e:
            print(f"Exception in IPAddressInputDialog save_ip_config: {e}")

    def load_ip_config(self):
        try:
            if os.path.exists('ip_config.json'):
                with open('ip_config.json', 'r') as f:
                    ip_addresses = json.load(f)
                    for i, ip_address in enumerate(ip_addresses):
                        octets = ip_address.split('.')
                        for j, octet in enumerate(octets):
                            self.ip_inputs[i * 4 + j].setText(octet)
        except Exception as e:
            print(f"Exception in IPAddressInputDialog load_ip_config: {e}")

class DataFetcher(QThread):
    data_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, mode, rack_number, initial_seconds=30):
        super().__init__()
        self.mode = mode.lower()
        self.rack_number = rack_number
        self.last_check_time = None
        self.initial_seconds = initial_seconds
        self._stop_event = False
        self.error_messages_shown = set()

    def run(self):
        while not self._stop_event:
            try:
                self.fetch_and_update_data()
                time.sleep(1.5)
            except Exception as e:
                self.error_occurred.emit("Run Error", str(e))

    def fetch_and_update_data(self):
        try:
            response = requests.get(f"{SERVER_URL}/get_mode", params={"rackNumber": self.rack_number})
            response.raise_for_status()
            self.mode = response.json().get('selected_mode', 'rack_mode').lower()

            if self.mode == 'center_mode':
                response = requests.post("http://mirudeveloper.iptime.org:8080/api/SelectBatteryInfo", json={"rackNumber": str(self.rack_number)})
                response.raise_for_status()
                data = response.json()
                self.data_fetched.emit(data)
            else:
                response = requests.get(f"{SERVER_URL}/get_config", params={"mode": self.mode})
                response.raise_for_status()
                db_config = response.json()

                connection = mysql.connector.connect(**db_config)
                cursor = connection.cursor(dictionary=True)

                if self.last_check_time is None:
                    cursor.execute("""
                        SELECT tbi.*, ci.description AS code_description
                        FROM transfer_battery_info tbi
                        LEFT JOIN code_info ci ON tbi.code_number = ci.code_number
                        WHERE tbi.rack_number = %s AND tbi.created_at >= NOW() - INTERVAL %s SECOND
                    """, (self.rack_number, self.initial_seconds))
                else:
                    cursor.execute("""
                        SELECT tbi.*, ci.description AS code_description
                        FROM transfer_battery_info tbi
                        LEFT JOIN code_info ci ON tbi.code_number = ci.code_number
                        WHERE tbi.rack_number = %s AND tbi.created_at > %s
                    """, (self.rack_number, self.last_check_time))

                data = cursor.fetchall()
                cursor.close()
                connection.close()
                if data:
                    self.last_check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.data_fetched.emit(data)
        except mysql.connector.Error as err:
            self.error_occurred.emit("Database Connection Error", f"An error occurred while connecting to the database: {err}")
        except requests.RequestException as err:
            self.error_occurred.emit("Request Error", f"An error occurred during the request: {err}")
        except Exception as e:
            self.error_occurred.emit("Unknown Error", f"An unknown error occurred: {e}")

    def stop(self):
        self._stop_event = True

class TableView(QMainWindow):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint)
        self.mode = None
        self.rack_number = None
        self.data_fetcher = None
        self.detail_dialog = BatteryDetailDialog(self)
        self.battery_cache = {}
        self.ip_addresses = []
        self.error_messages_shown = set()

        self.initUI()

        self.select_rack_number()
        self.select_mode()
        self.get_ip_addresses()
        self.start_data_fetcher()

    def initUI(self):
        self.setWindowTitle('Battery Data Viewer')
        self.setGeometry(0, 0, 1280, 720)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tableWidget = QTableWidget()
        layout.addWidget(self.tableWidget)

        self.loading_label = QLabel(self)
        self.loading_movie = QMovie("loading.gif")
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)
        self.loading_label.hide()

        self.info_layout = QHBoxLayout()
        self.time_label = QLabel(self)
        self.time_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.time_label.setFont(QFont("Arial", 15))
        self.time_label.setStyleSheet("color: black;")
        self.info_layout.addWidget(self.time_label)

        self.reselect_rack_button = QPushButton("Rack Reselection")
        self.reselect_rack_button.setStyleSheet("color: black;")
        self.reselect_rack_button.clicked.connect(self.reselect_rack)
        self.info_layout.addWidget(self.reselect_rack_button)

        self.reselect_mode_button = QPushButton("Mode Reselection")
        self.reselect_mode_button.setStyleSheet("color: black;")
        self.reselect_mode_button.clicked.connect(self.reselect_mode)
        self.info_layout.addWidget(self.reselect_mode_button)

        self.restart_program_button = QPushButton("Program Restart")
        self.restart_program_button.setStyleSheet("color: black;")
        self.restart_program_button.clicked.connect(self.restart_program)
        self.info_layout.addWidget(self.restart_program_button)

        self.ip_address_label = QLabel(self)
        self.ip_address_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.ip_address_label.setFont(QFont("Arial", 15))
        self.ip_address_label.setStyleSheet("color: black;")
        self.info_layout.addWidget(self.ip_address_label)

        layout.addLayout(self.info_layout)

        self.update_time()

    def select_rack_number(self):
        dialog = RackSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.rack_number = dialog.get_selected_rack_number()
        else:
            sys.exit()

    def select_mode(self):
        dialog = RackModeSelectionDialog(self, rack_number=self.rack_number)
        if dialog.exec_() == QDialog.Accepted:
            self.mode = dialog.get_selected_mode()
            self.send_mode_to_server(self.mode)
        else:
            sys.exit()

    def send_mode_to_server(self, mode):
        try:
            response = requests.post(f"{SERVER_URL}/set_mode", json={"rackNumber": self.rack_number, "mode": mode.lower()})
            if response.status_code == 200:
                print(f"Mode set to {mode} on server")
            else:
                self.show_error_message("Mode Setting Failed", f"Failed to set mode on server: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.show_error_message("Mode Setting Failed", f"Error setting mode on server: {e}")
        except Exception as e:
            self.show_error_message("Mode Setting Failed", f"Unknown error setting mode on server: {e}")

    def get_ip_addresses(self):
        dialog = IPAddressInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.ip_addresses = dialog.get_ip_addresses()
        else:
            sys.exit()

    def start_data_fetcher(self):
        self.show_loading_animation()
        if self.data_fetcher:
            self.data_fetcher.stop()
            self.data_fetcher.wait()

        self.data_fetcher = DataFetcher(self.mode, self.rack_number, initial_seconds=30)  # 최근 30초 간의 데이터를 가져오도록 설정
        self.data_fetcher.data_fetched.connect(self.handle_data_fetched)
        self.data_fetcher.error_occurred.connect(self.show_error_message)
        self.data_fetcher.start()

    def show_loading_animation(self):
        self.loading_label.show()
        self.loading_movie.start()

    def hide_loading_animation(self):
        self.loading_movie.stop()
        self.loading_label.hide()

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.254.254.254', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def update_time(self):
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm AP")
        self.time_label.setText(current_time)
        self.ip_address_label.setText(f"IP Address: {self.get_ip_address()}")

    def handle_data_fetched(self, data):
        try:
            self.hide_loading_animation()
            if self.mode == "center_mode":
                for battery in data:
                    key = (battery[14], battery[13])
                    self.battery_cache[key] = {
                        'battery_status': battery[2],
                        'battery_level': battery[3],
                        'battery_voltage': battery[4],
                        'cell_temperature': battery[11],
                        'cell_voltage1': battery[5],
                        'cell_voltage2': battery[6],
                        'cell_voltage3': battery[7],
                        'cell_voltage4': battery[8],
                        'cell_voltage5': battery[9],
                        'cell_voltage6': battery[10],
                        'cell_voltage7': battery[11],
                        'code_number': battery[17],
                        'code_description': battery[19]
                    }
            else:
                for battery in data:
                    key = (battery['client_ip'], battery['usb_port_number'])
                    self.battery_cache[key] = battery

            self.update_table()
            self.update_time()
        except Exception as e:
            print(f"Exception in handle_data_fetched: {e}")

    def update_table(self):
        self.tableWidget.show()
        self.tableWidget.setRowCount(10)
        self.tableWidget.setColumnCount(10)
        self.tableWidget.setHorizontalHeaderLabels([f"usb{i+1}" for i in range(10)])
        self.tableWidget.setVerticalHeaderLabels([f"RAZ{i+1}" for i in range(10)])

        for i in range(10):
            self.tableWidget.setRowHeight(i, 68)
            self.tableWidget.setColumnWidth(i, 120)

        for (client_ip, usb_index), battery in self.battery_cache.items():
            try:
                raz_index = self.ip_addresses.index(client_ip)
            except ValueError:
                continue

            usb_index = int(usb_index.replace("usb_hub_port", "")) - 1

            item = QTableWidgetItem(str(battery['battery_level']))
            item.setTextAlignment(Qt.AlignCenter)
            item.setFont(QFont("Arial", 30, QFont.Bold))
            item.setForeground(QColor(Qt.black))

            if battery['battery_status'] == 1:
                item.setBackground(QColor(0, 255, 0))
            elif battery['battery_status'] == 2:
                item.setBackground(QColor(255, 0, 0))
            else:
                item.setBackground(QColor(255, 255, 0))

            if battery.get('code_number') in [10, 20, 30]:
                item.setBackground(QColor(128, 0, 128))

            self.tableWidget.setItem(raz_index, usb_index, item)
            item.setData(Qt.UserRole, battery)

        for i in range(10):
            for j in range(10):
                if (self.ip_addresses[i], f"usb_hub_port{j+1}") not in self.battery_cache:
                    item = QTableWidgetItem("N/A")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFont(QFont("Arial", 30, QFont.Bold))
                    item.setForeground(QColor(Qt.black))
                    item.setBackground(QColor(211, 211, 211))
                    self.tableWidget.setItem(i, j, item)

        self.tableWidget.cellClicked.connect(self.showDetail)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.setSelectionMode(QTableWidget.NoSelection)

    def showDetail(self, row, column):
        item = self.tableWidget.item(row, column)
        if item:
            battery_data = item.data(Qt.UserRole)
            if battery_data:
                self.detail_dialog.update_data(battery_data)
                self.detail_dialog.setModal(True)
                self.detail_dialog.show()

    def reselect_rack(self):
        self.data_fetcher.stop()
        self.select_rack_number()
        self.select_mode()
        self.get_ip_addresses()
        self.start_data_fetcher()

    def reselect_mode(self):
        self.data_fetcher.stop()
        self.select_mode()
        self.start_data_fetcher()

    def restart_program(self):
        self.close()
        QCoreApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def show_error_message(self, title, message):
        if (title, message) not in self.error_messages_shown:
            self.error_messages_shown.add((title, message))
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.exec_()

    def showFullScreen(self):
        super().showFullScreen()

    def closeEvent(self, event):
        if self.data_fetcher:
            self.data_fetcher.stop()
            self.data_fetcher.wait()
        event.accept()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        viewer = TableView()
        viewer.showFullScreen()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Exception in main: {e}")
