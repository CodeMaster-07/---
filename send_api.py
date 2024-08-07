import requests

url = "http://mirudeveloper.iptime.org:8080/api/SelectBatteryInfo"

payload = {
    "rackNumber": "1",
}
try:
    response = requests.post(url, json=payload)
    response_data = response.json()
    print("Server response:", response_data)
except Exception as e:
    print(f"Error occurred: {e}")
