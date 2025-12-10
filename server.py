from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__, static_folder='.', static_url_path='')

METADATA_FILE = 'metadata.json'

@app.route('/save-metadata', methods=['POST'])
def save_metadata():
    try:
        new_json = request.get_json(force=True)
        if not isinstance(new_json, (dict, list)):
            return jsonify({'ok': False, 'error': 'Erwarte ein JSON-Objekt oder Array im Body'}), 400

        # Schreibe die Datei (UTF-8, schöner formatiert)
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_json, f, ensure_ascii=False, indent=2)

        return jsonify({'ok': True, 'message': 'metadata.json gespeichert'}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# statische Dateien (index.html, assets) aus dem Repo-Ordner ausliefern
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Nur lokal (127.0.0.1), Port 8008
    app.run(host='127.0.0.1', port=8007, debug=True)