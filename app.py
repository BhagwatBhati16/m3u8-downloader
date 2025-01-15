from flask import Flask, request, jsonify, render_template
import os
import subprocess
import time
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from queue import Queue
from threading import Thread, Lock
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables for download management
download_queue = Queue()
current_download = None
download_lock = Lock()
download_history = {}

def get_ffmpeg_path():
    current_dir = os.path.dirname(__file__)
    if os.name == "nt":
        return os.path.join(current_dir, "ffmpeg", "bin", "ffmpeg.exe")
    return "ffmpeg"  # Use system ffmpeg if not Windows

def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

def calculate_speed(start_time, bytes_downloaded):
    elapsed_time = time.time() - start_time
    if elapsed_time == 0:
        return 0
    return bytes_downloaded / elapsed_time

def download_video(url, output_path, download_id):
    global current_download
    
    try:
        logger.info(f"Starting download for ID: {download_id}")
        logger.info(f"URL: {url}")
        logger.info(f"Output path: {output_path}")

        current_download.update({
            'status': 'downloading',
            'start_time': time.time(),
            'bytes_downloaded': 0,
            'speed': 0
        })

        ffmpeg_path = get_ffmpeg_path()
        
        # Modified FFmpeg command with additional parameters
        command = [
            ffmpeg_path,
            "-y",  # Overwrite output file if it exists
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",  # Allow various protocols
            "-i", url,
            "-c", "copy",  # Copy without re-encoding
            "-bsf:a", "aac_adtstoasc",  # Fix for AAC audio
            "-progress", "pipe:1",
            "-stats",
            output_path
        ]

        logger.info(f"FFmpeg command: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )

        progress_pattern = re.compile(r'out_time_ms=(\d+)|total_size=(\d+)')
        
        # Start a thread to read stderr
        def log_stderr():
            for line in process.stderr:
                logger.debug(f"FFmpeg stderr: {line.strip()}")

        stderr_thread = Thread(target=log_stderr)
        stderr_thread.daemon = True
        stderr_thread.start()

        last_update_time = time.time()
        last_bytes = 0

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.debug(f"FFmpeg stdout: {output.strip()}")
                matches = progress_pattern.finditer(output)
                current_bytes = 0
                
                for match in matches:
                    if match.group(2):  # total_size match
                        current_bytes = int(match.group(2))
                        
                if current_bytes > 0 and current_bytes != last_bytes:
                    current_time = time.time()
                    time_diff = current_time - last_update_time
                    if time_diff > 0:
                        speed = (current_bytes - last_bytes) / time_diff
                        current_download.update({
                            'bytes_downloaded': current_bytes,
                            'formatted_size': format_bytes(current_bytes),
                            'speed': speed,
                            'formatted_speed': format_bytes(speed) + '/s'
                        })
                    last_bytes = current_bytes
                    last_update_time = current_time

        # Check process exit code
        exit_code = process.poll()
        logger.info(f"FFmpeg process exited with code: {exit_code}")

        if exit_code == 0:
            current_download['status'] = 'completed'
            logger.info(f"Download completed successfully for ID: {download_id}")
        else:
            stderr_output = process.stderr.read()
            current_download['status'] = 'failed'
            current_download['error'] = stderr_output
            logger.error(f"Download failed for ID: {download_id}. Error: {stderr_output}")

    except Exception as e:
        logger.exception(f"Exception during download for ID: {download_id}")
        current_download['status'] = 'failed'
        current_download['error'] = str(e)
    finally:
        # Move to history and process next in queue
        download_history[download_id] = current_download.copy()
        start_next_download()

def start_next_download():
    global current_download
    
    with download_lock:
        current_download = None
        if not download_queue.empty():
            download_info = download_queue.get()
            current_download = download_info
            thread = Thread(
                target=download_video,
                args=(download_info['url'], download_info['output_path'], download_info['id'])
            )
            thread.daemon = True  # Make thread daemon so it won't block program exit
            thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture():
    data = request.json
    if not data or 'url' not in data:
        return jsonify({"error": "Invalid data"}), 400

    url = data['url']
    logger.info(f"Captured new URL: {url}")

    download_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    download_info = {
        'id': download_id,
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    download_history[download_id] = download_info
    return jsonify({"message": "URL received", "download_id": download_id}), 200

@app.route('/start_download', methods=['POST'])
def start_download():
    try:
        data = request.get_json()
        if not data or 'download_id' not in data or 'filename' not in data:
            return jsonify({"error": "Invalid data"}), 400

        download_id = data['download_id']
        if download_id not in download_history:
            return jsonify({"error": "Download ID not found"}), 404

        filename = secure_filename(data['filename'])
        if not filename.endswith('.mp4'):
            filename += '.mp4'

        output_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        logger.info(f"Starting download process for ID: {download_id}, filename: {filename}")

        download_info = {
            'id': download_id,
            'filename': filename,
            'output_path': output_path,
            'status': 'queued',
            'url': download_history[download_id]['url'],
            'timestamp': datetime.now().isoformat()
        }

        download_queue.put(download_info)
        download_history[download_id].update(download_info)

        if current_download is None:
            start_next_download()

        return jsonify({
            "message": "Download queued",
            "download_id": download_id,
            "position": download_queue.qsize(),
            "success": True
        }), 200

    except Exception as e:
        logger.exception("Error in start_download")
        return jsonify({
            "error": f"Failed to queue download: {str(e)}",
            "success": False
        }), 500

@app.route('/download_status', methods=['GET'])
def get_download_status():
    return jsonify({
        "current_download": current_download,
        "queue_size": download_queue.qsize(),
        "history": download_history
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)