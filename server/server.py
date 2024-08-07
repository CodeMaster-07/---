from flask import Flask, request, jsonify
import json

app = Flask(__name__)

CONFIG_FILE = 'config.json'

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

config = load_config()

@app.route('/set_mode', methods=['POST'])
def set_mode():
    rack_number = str(request.json.get('rackNumber'))
    mode = request.json.get('mode', 'Rack_Mode')
    if rack_number in config['racks']:
        config['racks'][rack_number] = mode
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return jsonify({"status": "success", "rackNumber": rack_number, "selected_mode": mode})
    else:
        return jsonify({"status": "failure", "message": "Invalid rack number"}), 400

@app.route('/get_mode', methods=['GET'])
def get_mode():
    rack_number = request.args.get('rackNumber')
    if rack_number and rack_number in config['racks']:
        selected_mode = config['racks'][rack_number]
        return jsonify({"rackNumber": rack_number, "selected_mode": selected_mode})
    else:
        return jsonify({"status": "failure", "message": "Invalid or missing rack number"}), 400

@app.route('/get_config', methods=['GET'])
def get_config():
    mode = request.args.get('mode')
    if mode in config:
        return jsonify(config[mode])
    else:
        return jsonify({"status": "failure", "message": "Invalid or missing mode"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
