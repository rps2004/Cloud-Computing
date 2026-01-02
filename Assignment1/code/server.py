# app.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/reverse', methods=['POST'])
def reverse_string():
    data = request.get_json(force=True, silent=True) or {}
    input_str = data.get("text", "")
    reversed_str = input_str[::-1]
    return jsonify({"reversed": reversed_str})

if __name__ == "__main__":
    # host=0.0.0.0 so it works in Docker/Kubernetes
    app.run(host="0.0.0.0", port=5000, debug=False)
