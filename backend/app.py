from flask import Flask, request, jsonify, send_file
import csv, os, requests, threading
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Constants
CSV_FILE = 'MovieDB.csv'
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Function: Search movie entries from CSV
def search_movie(movie_name):
    results = []
    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if movie_name.lower() in row['Movie Name'].lower():
                results.append({
                    'title': row['Movie Name'],
                    'link': row['URL'],
                    'year': row['Release Year'],
                    'quality': row['Resolution']
                })
    return results

# Function: Use Playwright to fetch real MP4 URL
def fetch_real_mp4_url(stream_page_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        mp4_url = None

        def handle_response(response):
            nonlocal mp4_url
            if ".mp4" in response.url:
                mp4_url = response.url

        page.on("response", handle_response)
        page.goto(stream_page_url, timeout=60000)
        page.wait_for_timeout(5000)  # wait for network activity
        browser.close()
        return mp4_url

# Route: Search for movies
@app.route('/search')
def search():
    movie = request.args.get('movie')
    if not movie:
        return jsonify({"error": "No movie provided"}), 400
    return jsonify(search_movie(movie))

# Function: Thread to download the movie
def download_thread(title, quality, url, filename):
    mp4_url = fetch_real_mp4_url(url)
    if not mp4_url:
        print(f"Failed to fetch MP4 URL for {title}")
        return

    with requests.get(mp4_url, stream=True) as r:
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    print(f"Downloaded: {filename}")

# Route: Download request
@app.route('/download', methods=['POST'])
def download():
    data = request.json
    title = data.get('title')
    quality = data.get('quality')
    url = data.get('link')

    if not all([title, quality, url]):
        return jsonify({"error": "Missing data"}), 400

    safe_title = title.replace('/', '_').replace('\\', '_')
    filename = os.path.join(DOWNLOAD_FOLDER, f"{safe_title} {quality}.mp4")

    thread = threading.Thread(target=download_thread, args=(title, quality, url, filename))
    thread.start()

    return jsonify({"message": "Download started", "file": filename})

# Route: Download file from server
@app.route('/get_file')
def get_file():
    file_path = request.args.get('file')
    if not file_path or not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True)

# Run server
if __name__ == '__main__':
    app.run(debug=True)
