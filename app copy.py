from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

# Path to FFmpeg binary
def get_ffmpeg_path():
    current_dir = os.path.dirname(__file__)
    if os.name == "nt":  # Windows
        return os.path.join(current_dir, "ffmpeg", "bin", "ffmpeg.exe")
    else:  # Linux/Mac
        return os.path.join(current_dir, "ffmpeg", "bin", "ffmpeg")

@app.route('/capture', methods=['POST'])
def capture():
    data = request.json
    if not data or 'url' not in data:
        app.logger.error("Invalid data received: %s", data)
        return jsonify({"error": "Invalid data"}), 400

    url = data['url']
    app.logger.info("Received .m3u8 URL: %s", url)

    # Save the file dynamically based on the URL
    output_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(output_dir, exist_ok=True)
    file_name = os.path.basename(url).split("?")[0]
    output_file = os.path.join(output_dir, file_name.replace(".m3u8", ".mp4"))

    ffmpeg_path = get_ffmpeg_path()
    command = [ffmpeg_path, "-i", url, "-c", "copy", output_file]

    try:
        subprocess.run(command, check=True)
        app.logger.info("Download complete: %s", output_file)
        return jsonify({"message": f"Downloaded {url} to {output_file}"}), 200
    except subprocess.CalledProcessError as e:
        app.logger.error("Error during FFmpeg execution: %s", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
