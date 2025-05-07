
from flask import Flask, request, jsonify, send_file
import csv, os, requests, threading
from playwright.sync_api import sync_playwright

app = Flask(__name__)
CSV_FILE = 'MovieDB.csv'
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

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
        page.wait_for_timeout(5000)
        browser.close()
        return mp4_url

@app.route('/search')
def search():
    movie = request.args.get('movie')
    return jsonify(search_movie(movie))

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    title = data['title']
    quality = data['quality']
    url = data['link']

    safe_title = title.replace('/', '_').replace('\', '_')
    filename = os.path.join(DOWNLOAD_FOLDER, f"{safe_title} {quality}.mp4")

    def _download_thread():
        mp4_url = fetch_real_mp4_url(url)
        if not mp4_url:
            return

        with requests.get(mp4_url, stream=True) as r:
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

    thread = threading.Thread(target=_download_thread)
    thread.start()

    return jsonify({"message": "Download started", "file": filename})

@app.route('/get_file')
def get_file():
    file_path = request.args.get('file')
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
