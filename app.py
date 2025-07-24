import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from pytube import YouTube
import tempfile
import threading
import time
from urllib.parse import urlparse
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Global variable to store download progress
download_progress = {}

def is_valid_youtube_url(url):
    """Validate if the URL is a valid YouTube URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

def get_video_info(url):
    """Get video information from YouTube URL"""
    try:
        yt = YouTube(url)
        
        # Get available streams
        video_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
        audio_streams = yt.streams.filter(only_audio=True, file_extension='mp4')
        
        # Prepare quality options
        quality_options = []
        
        # Add video qualities
        seen_resolutions = set()
        for stream in video_streams:
            if stream.resolution and stream.resolution not in seen_resolutions:
                quality_options.append({
                    'itag': stream.itag,
                    'quality': stream.resolution,
                    'type': 'video',
                    'filesize': stream.filesize or 0
                })
                seen_resolutions.add(stream.resolution)
        
        # Add audio-only option
        if audio_streams:
            audio_stream = audio_streams.first()
            quality_options.append({
                'itag': audio_stream.itag,
                'quality': 'Audio Only',
                'type': 'audio',
                'filesize': audio_stream.filesize or 0
            })
        
        video_info = {
            'title': yt.title,
            'length': yt.length,
            'views': yt.views,
            'thumbnail_url': yt.thumbnail_url,
            'author': yt.author,
            'quality_options': quality_options
        }
        
        return video_info, None
    
    except Exception as e:
        logging.error(f"Error getting video info: {str(e)}")
        return None, str(e)

def format_duration(seconds):
    """Format duration from seconds to MM:SS or HH:MM:SS"""
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours}:{minutes:02d}:{seconds:02d}"

def format_filesize(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info_route():
    """Get video information from YouTube URL"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'Please enter a YouTube URL'}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Please enter a valid YouTube URL'}), 400
    
    video_info, error = get_video_info(url)
    
    if error:
        return jsonify({'error': f'Error loading video: {error}'}), 400
    
    # Format the data for display
    formatted_info = {
        'title': video_info['title'],
        'duration': format_duration(video_info['length']),
        'views': f"{video_info['views']:,}" if video_info['views'] else "Unknown",
        'thumbnail_url': video_info['thumbnail_url'],
        'author': video_info['author'],
        'quality_options': [
            {
                'itag': option['itag'],
                'quality': option['quality'],
                'type': option['type'],
                'filesize': format_filesize(option['filesize'])
            }
            for option in video_info['quality_options']
        ]
    }
    
    return jsonify(formatted_info)

@app.route('/download', methods=['POST'])
def download_video():
    """Download video with selected quality"""
    data = request.get_json()
    url = data.get('url', '').strip()
    itag = data.get('itag')
    
    if not url or not itag:
        return jsonify({'error': 'Missing URL or quality selection'}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        # Generate unique download ID
        download_id = f"download_{int(time.time())}"
        download_progress[download_id] = {'progress': 0, 'status': 'starting'}
        
        def download_thread():
            try:
                yt = YouTube(url)
                stream = yt.streams.get_by_itag(itag)
                
                if not stream:
                    download_progress[download_id]['status'] = 'error'
                    download_progress[download_id]['error'] = 'Selected quality not available'
                    return
                
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                filename = f"{yt.title}_{stream.resolution or 'audio'}.{stream.subtype}"
                # Clean filename
                filename = re.sub(r'[<>:"/\\|?*]', '', filename)
                filepath = os.path.join(temp_dir, filename)
                
                download_progress[download_id]['status'] = 'downloading'
                download_progress[download_id]['filename'] = filename
                
                # Download with progress callback
                def progress_callback(stream, chunk, bytes_remaining):
                    total_size = stream.filesize
                    bytes_downloaded = total_size - bytes_remaining
                    progress = int((bytes_downloaded / total_size) * 100)
                    download_progress[download_id]['progress'] = progress
                
                yt.register_on_progress_callback(progress_callback)
                stream.download(output_path=temp_dir, filename=filename)
                
                download_progress[download_id]['status'] = 'completed'
                download_progress[download_id]['filepath'] = filepath
                download_progress[download_id]['progress'] = 100
                
            except Exception as e:
                logging.error(f"Download error: {str(e)}")
                download_progress[download_id]['status'] = 'error'
                download_progress[download_id]['error'] = str(e)
        
        # Start download in background thread
        thread = threading.Thread(target=download_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'download_id': download_id,
            'message': 'Download started'
        })
        
    except Exception as e:
        logging.error(f"Error starting download: {str(e)}")
        return jsonify({'error': f'Error starting download: {str(e)}'}), 500

@app.route('/download_progress/<download_id>')
def get_download_progress(download_id):
    """Get download progress"""
    progress_info = download_progress.get(download_id, {'status': 'not_found'})
    return jsonify(progress_info)

@app.route('/download_file/<download_id>')
def download_file(download_id):
    """Serve the downloaded file"""
    progress_info = download_progress.get(download_id)
    
    if not progress_info or progress_info.get('status') != 'completed':
        return jsonify({'error': 'Download not completed or not found'}), 404
    
    filepath = progress_info.get('filepath')
    filename = progress_info.get('filename')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        logging.error(f"Error serving file: {str(e)}")
        return jsonify({'error': 'Error serving file'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
