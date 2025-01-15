# M3U8 Downloader

This project is a web application that allows you to download videos from M3U8 URLs. It uses Flask for the backend and a Chrome extension to capture M3U8 URLs from websites like hianime and similar sites.

## Features

- Capture M3U8 URLs from websites using a Chrome extension
- Queue and manage video downloads
- Monitor download progress and history
- Supports downloading videos without re-encoding using FFmpeg

## Installation

### Prerequisites

- Python 3.6+
- FFmpeg
- Google Chrome

### Setup

1. Clone the repository:

    ```sh
    git clone https://github.com/BhagwatBhati16/m3u8-downloader.git
    cd m3u8-downloader
    ```

2. Install the required Python packages:

    ```sh
    pip install -r requirements.txt
    ```

3. Ensure FFmpeg is installed and available in your system's PATH. If you are on Windows, place the `ffmpeg.exe` binary in the `bin` directory.

4. Run the Flask application:

    ```sh
    python app.py
    ```

    The application will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

### Chrome Extension Setup

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable "Developer mode" using the toggle switch in the top right corner.
3. Click on "Load unpacked" and select the `HTTP-Headers-Chrome-Web-Store` directory from this repository.

## Usage

1. Open the Chrome extension popup and ensure it is active.
2. Navigate to a website like hianime and start playing a video.
3. The extension will capture the M3U8 URL and send it to the Flask application.
4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser to monitor and manage your downloads.

## Acknowledgements

- Paul Hempshall for the original HTTP Headers extension code (https://github.com/phempshall/http-headers.git).
- FFmpeg for the powerful multimedia framework.
