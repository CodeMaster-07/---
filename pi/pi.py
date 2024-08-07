import serial
import socket
import uuid
import threading
import time
import requests
import json
from tabulate import tabulate
import mysql.connector

def load_server_url():
    try:
        with open('server.json', 'r') as f:
            config = json.load(f)
            return config.get('server_url', 'error')
    except Exception as e:
        print(f"Failed to load server URL from server.json: {e}")
        return 'Error'

SERVER_URL = load_server_url()

def read_battery_data(serial_port):
    try:
        ser = serial.Serial(f'/dev/{serial_port}', 9600, timeout=1)
        ser.write(b'\x01\x05\x31\x30\x00\x04\x04')
        data = ser.read(26)
        ser.close()
        return data
    except Exception as e:
        return f"{serial_port}: {str(e)}"

def parse_battery_data(data):
    if len(data) < 26:
        return None
    
    state = data[4]
    soc = data[5]
    total_voltage = (data[7] << 8 | data[6]) * 0.001
    voltages = [(data[9 + i * 2] << 8 | data[8 + i * 2]) * 0.001 for i in range(7)]
    temperature = (data[23] << 8 | data[22]) * 0.1
    bcc = data[24]
    eot = data[25]

    return {
        'State': state,
        'SOC': soc,
        'TotalVoltage': total_voltage,
        'Voltages': voltages,
        'Temperature': temperature,
        'BCC': bcc,
        'EOT': eot,
        'RawData': data
    }

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.1.1'
    finally:
        s.close()
    return IP

def get_mac_address():
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e+2] for e in range(0, 11, 2)])

def send_data_to_api(battery_data, api_url):
    try:
        response = requests.post(f"{api_url}/upload", json=battery_data)
        if response.status_code == 200:
            return "API 전송 성공"
        else:
            return f"API 전송 실패: {response.status_code} {response.text}"
    except requests.exceptions.RequestException as e:
        return f"API 요청 실패: {str(e)}"

def send_data_to_mysql(state, soc, total_voltage, voltages, temperature, usb_port, ip_address, mac_address, rack_number, code_number, db_config):
    connection = None
    try:
        if not all(k in db_config for k in ('host', 'user', 'password', 'database')):
            raise ValueError("Incomplete database configuration")

        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        cursor = connection.cursor()

        query = """
            CALL InsertBatteryInfoProc(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        data = (
            state, soc, total_voltage,
            f"{voltages[0]:.3f}",
            f"{voltages[1]:.3f}",
            f"{voltages[2]:.3f}",
            f"{voltages[3]:.3f}",
            f"{voltages[4]:.3f}",
            f"{voltages[5]:.3f}",
            f"{voltages[6]:.3f}",
            usb_port, ip_address, mac_address, rack_number, temperature, code_number
        )

        cursor.execute(query, data)
        connection.commit()
        return f"{usb_port}: 데이터 전송 성공"
    except (mysql.connector.Error, ValueError) as err:
        return f"Error: {err}"
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def print_battery_data(data, usb_port):
    raw_data_hex = ' '.join([f'{byte:02X}' for byte in data['RawData']])
    state_str = "방전" if data['State'] == 2 else "충전"
    voltages = [f'{v:.3f}V ({v*1000:.0f}mV)' for v in data['Voltages']]
    output = [
        ["USB Port", usb_port],
        ["상태", state_str],
        ["SOC", f"{data['SOC']}%"],
        ["전체 전압", f"{data['TotalVoltage']:.1f}V"],
        *[[f"전압 {i+1}", voltages[i]] for i in range(7)],
        ["온도", f"{data['Temperature']:.1f}도"],
        ["BCC", f"0x{data['BCC']:02X}"],
        ["EOT", f"0x{data['EOT']:02X}"],
        ["Raw Data", raw_data_hex]
    ]
    return tabulate(output, headers=["Parameter", "Value"], tablefmt="grid")

def check_usb_port(serial_port, ip_address, mac_address, rack_number, results, index, db_config, mode, api_url):
    try:
        if db_config is None:
            results[index] = f"{serial_port}: 데이터베이스 구성 정보를 가져올 수 없음"
            return

        data = read_battery_data(serial_port)
        if isinstance(data, str):
            results[index] = f"{serial_port}: 인식실패\n{data}"
            if mode == "senter_mode":
                battery_data = {
                    "IP": ip_address,
                    "UsbPortLocation": serial_port,
                    "MAC": mac_address,
                    "Status": 10,
                    "BatteryLevel": 0,
                    "Voltage": 0,
                    "CellTemper": 0,
                    "Cell1": 0,
                    "Cell2": 0,
                    "Cell3": 0,
                    "Cell4": 0,
                    "Cell5": 0,
                    "Cell6": 0,
                    "Cell7": 0,
                    "Current": 0,
                    "CodeNumber": 10
                }
                results[index] += send_data_to_api(battery_data, api_url)
            else:
                send_data_to_mysql(0, 0, 0, [0] * 7, 0, serial_port, ip_address, mac_address, rack_number, 10, db_config)
        elif data:
            parsed_data = parse_battery_data(data)
            if parsed_data:
                results[index] = print_battery_data(parsed_data, serial_port)
                if mode == "senter_mode":
                    battery_data = {
                        "IP": ip_address,
                        "UsbPortLocation": serial_port,
                        "MAC": mac_address,
                        "Status": parsed_data['State'],
                        "BatteryLevel": parsed_data['SOC'],
                        "Voltage": parsed_data['TotalVoltage'],
                        "CellTemper": parsed_data['Temperature'],
                        "Cell1": parsed_data['Voltages'][0],
                        "Cell2": parsed_data['Voltages'][1],
                        "Cell3": parsed_data['Voltages'][2],
                        "Cell4": parsed_data['Voltages'][3],
                        "Cell5": parsed_data['Voltages'][4],
                        "Cell6": parsed_data['Voltages'][5],
                        "Cell7": parsed_data['Voltages'][6],
                        "Current": 0,  # Current 값이 필요하다면 적절히 변경 필요
                        "CodeNumber": 0  # 코드 번호도 적절히 설정 필요
                    }
                    results[index] += send_data_to_api(battery_data, api_url)
                else:
                    results[index] += send_data_to_mysql(
                        parsed_data['State'], parsed_data['SOC'], parsed_data['TotalVoltage'],
                        parsed_data['Voltages'], parsed_data['Temperature'],
                        serial_port, ip_address, mac_address, rack_number, 0, db_config
                    )
            else:
                results[index] = f"{serial_port}: 정보없음"
                if mode == "senter_mode":
                    battery_data = {
                        "IP": ip_address,
                        "UsbPortLocation": serial_port,
                        "MAC": mac_address,
                        "Status": 20,
                        "BatteryLevel": 0,
                        "Voltage": 0,
                        "CellTemper": 0,
                        "Cell1": 0,
                        "Cell2": 0,
                        "Cell3": 0,
                        "Cell4": 0,
                        "Cell5": 0,
                        "Cell6": 0,
                        "Cell7": 0,
                        "Current": 0,
                        "CodeNumber": 20
                    }
                    results[index] += send_data_to_api(battery_data, api_url)
                else:
                    send_data_to_mysql(0, 0, 0, [0] * 7, 0, serial_port, ip_address, mac_address, rack_number, 20, db_config)
        else:
            results[index] = f"{serial_port}: 인식실패"
            if mode == "senter_mode":
                battery_data = {
                    "IP": ip_address,
                    "UsbPortLocation": serial_port,
                    "MAC": mac_address,
                    "Status": 10,
                    "BatteryLevel": 0,
                    "Voltage": 0,
                    "CellTemper": 0,
                    "Cell1": 0,
                    "Cell2": 0,
                    "Cell3": 0,
                    "Cell4": 0,
                    "Cell5": 0,
                    "Cell6": 0,
                    "Cell7": 0,
                    "Current": 0,
                    "CodeNumber": 10
                }
                results[index] += send_data_to_api(battery_data, api_url)
            else:
                send_data_to_mysql(0, 0, 0, [0] * 7, 0, serial_port, ip_address, mac_address, rack_number, 10, db_config)
    except Exception as e:
        results[index] = f"{serial_port}: 예외 발생\n{str(e)}"


def fetch_db_config(mode):
    try:
        response = requests.get(f"{SERVER_URL}/get_config", params={"mode": mode.lower()})
        response.raise_for_status()
        config = response.json()
        return config
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Failed to fetch DB config: {e}")
        return None


def fetch_current_mode(rack_number):
    try:
        response = requests.get(f"{SERVER_URL}/get_mode", params={"rackNumber": rack_number})
        response.raise_for_status()
        return response.json().get('selected_mode', 'rack_mode')
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch current mode: {e}")
        return 'rack_mode'

def main():
    rack_number = 1  # Example rack number, set this accordingly

    while True:
        try:
            current_mode = fetch_current_mode(rack_number)
            config = fetch_db_config(current_mode)
            if not config:
                print("Config not found, retrying in 5 seconds...")
                time.sleep(5)
                continue

            ip_address = get_ip_address()
            mac_address = get_mac_address()
            usb_ports = [f'usb_hub_port{port}' for port in range(1, 11)]

            while True:
                new_mode = fetch_current_mode(rack_number)
                if new_mode != current_mode:
                    print(f"Mode changed from {current_mode} to {new_mode}")
                    current_mode = new_mode
                    config = fetch_db_config(current_mode)
                    if not config:
                        print("Config not found, retrying in 5 seconds...")
                        time.sleep(5)
                        continue

                results = [None] * len(usb_ports)
                threads = []
                for i, usb_port in enumerate(usb_ports):
                    thread = threading.Thread(target=check_usb_port, args=(usb_port, ip_address, mac_address, rack_number, results, i, config, current_mode, config['api_server_url'] if current_mode == "senter_mode" else None))
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

                for result in results:
                    print(result)

                time.sleep(1)
        except Exception as e:
            print(f"Main loop exception: {e}")
            time.sleep(1)

if __name__ == '__main__':
    main()
