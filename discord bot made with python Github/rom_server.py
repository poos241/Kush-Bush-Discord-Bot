from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

ROM_FOLDER = os.path.abspath("roms")  # make sure this is your roms directory

@app.route("/roms/<path:filename>")
def serve_rom(filename):
    # Security: prevent path traversal attacks
    safe_path = os.path.join(ROM_FOLDER, filename)
    if not os.path.isfile(safe_path):
        return abort(404)

    return send_from_directory(ROM_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
