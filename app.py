from flask import Flask, request, jsonify, send_file, render_template, send_from_directory, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
import csv
from openpyxl import Workbook
from datetime import datetime
import os
import time
import logging
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
CORS(app)

# Configure Flask
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECURE CREDENTIAL RECOVERY LAYER ---
# Recovers your API keys from Render's private background vault
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

logger.info(f"Loaded credentials target verification. API_ID configured: {API_ID > 0}")

class CourseExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        self.max_course_pages = int(os.getenv('MAX_COURSE_PAGES', '100'))
    
    def extract_course_info(self, url):
        try:
            logger.info(f"Extracting course info from: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            courses = self._extract_courses_from_page(soup, url)
            
            return {
                'success': True,
                'url': url,
                'courses_found': len(courses),
                'courses': courses
            }
        except Exception as e:
            logger.error(f"Extraction error for {url}: {e}")
            return {'success': False, 'url': url, 'error': str(e)}

    def _extract_courses_from_page(self, soup, base_url):
        courses = []
        course_containers = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'course|class|program', re.I))
        for container in course_containers:
            name_elem = container.find(['h1', 'h2', 'h3', '.course-title', '.title'])
            if name_elem and name_elem.get_text(strip=True):
                courses.append({
                    'course_name': name_elem.get_text(strip=True),
                    'institute_name': 'Dynamic Web Content Extractor',
                    'format': 'Online',
                    'availability': 'Open'
                })
        return courses

extractor = CourseExtractor()

@app.route('/api/extract', methods=['POST'])
def extract_courses():
    try:
        data = request.get_json() or {}
        urls = data.get('urls', [])
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400
        
        results = []
        for url in urls:
            if url.strip():
                result = extractor.extract_course_info(url.strip())
                results.append(result)
        
        return jsonify({
            'success': True,
            'results': results,
            'total_courses': sum(len(r.get('courses', [])) for r in results if r.get('success'))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return make_response(render_template('index.html'))

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
