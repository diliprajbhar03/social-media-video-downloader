import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from pytube import YouTube
import tempfile
import threading
import time
from urllib.parse import urlparse
import re
import json
from datetime import datetime, date

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configure the database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback for development
    database_url = "postgresql://user:password@localhost:5432/youtube_downloader"
    logging.warning("DATABASE_URL not found, using fallback database URL")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Global variable to store download progress
download_progress = {}

def is_valid_youtube_url(url):
    """Validate if the URL is a valid YouTube URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtu\.be/([^?]+)',
        r'youtube\.com/embed/([^?]+)',
        r'youtube\.com/v/([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_info(url):
    """Get video information from YouTube URL with database caching"""
    try:
        # Extract video ID for caching
        video_id = extract_video_id(url)
        if not video_id:
            return None, "Invalid YouTube URL"
        
        # Check if we have cached info for this video
        from models import VideoInfo
        cached_video = VideoInfo.query.filter_by(video_id=video_id).first()
        
        if cached_video:
            # Update access tracking
            cached_video.update_access()
            
            # Return cached data
            quality_options = json.loads(cached_video.available_qualities) if cached_video.available_qualities else []
            video_info = {
                'title': cached_video.title,
                'length': cached_video.duration,
                'views': cached_video.views,
                'thumbnail_url': cached_video.thumbnail_url,
                'author': cached_video.author,
                'quality_options': quality_options
            }
            logging.info(f"Retrieved cached video info for: {cached_video.title}")
            return video_info, None
        
        # Fetch fresh data from YouTube
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
        
        # Cache video information in database
        try:
            new_video_info = VideoInfo(
                video_id=video_id,
                video_url=url,
                title=yt.title,
                author=yt.author,
                duration=yt.length,
                views=yt.views,
                thumbnail_url=yt.thumbnail_url,
                available_qualities=json.dumps(quality_options)
            )
            db.session.add(new_video_info)
            db.session.commit()
            logging.info(f"Cached video info for: {yt.title}")
        except Exception as cache_error:
            logging.error(f"Error caching video info: {str(cache_error)}")
            db.session.rollback()
        
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

@app.route('/stats')
def stats():
    return render_template('stats.html')

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
    """Download video with selected quality and track in database"""
    data = request.get_json()
    url = data.get('url', '').strip()
    itag = data.get('itag')
    
    if not url or not itag:
        return jsonify({'error': 'Missing URL or quality selection'}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        # Get user information
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        session_id = session.get('session_id', str(time.time()))
        session['session_id'] = session_id
        
        # Generate unique download ID
        download_id = f"download_{int(time.time())}"
        download_progress[download_id] = {'progress': 0, 'status': 'starting'}
        
        def download_thread():
            download_record = None
            try:
                from models import DownloadHistory, PopularVideo, DownloadStats
                
                yt = YouTube(url)
                stream = yt.streams.get_by_itag(itag)
                
                if not stream:
                    download_progress[download_id]['status'] = 'error'
                    download_progress[download_id]['error'] = 'Selected quality not available'
                    return
                
                # Create download record
                video_id = extract_video_id(url)
                quality = stream.resolution or 'Audio Only'
                download_type = 'video' if stream.resolution else 'audio'
                
                download_record = DownloadHistory(
                    video_title=yt.title,
                    video_url=url,
                    video_id=video_id,
                    author=yt.author,
                    duration=yt.length,
                    views=yt.views,
                    thumbnail_url=yt.thumbnail_url,
                    quality=quality,
                    download_type=download_type,
                    file_size=stream.filesize,
                    itag=itag,
                    user_ip=user_ip,
                    user_agent=user_agent,
                    session_id=session_id,
                    download_started_at=datetime.utcnow(),
                    status='downloading'
                )
                db.session.add(download_record)
                db.session.commit()
                
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                filename = f"{yt.title}_{stream.resolution or 'audio'}.{stream.subtype}"
                # Clean filename
                filename = re.sub(r'[<>:"/\\|?*]', '', filename)
                filepath = os.path.join(temp_dir, filename)
                
                download_progress[download_id]['status'] = 'downloading'
                download_progress[download_id]['filename'] = filename
                download_progress[download_id]['record_id'] = download_record.id
                
                # Download with progress callback
                def progress_callback(stream, chunk, bytes_remaining):
                    total_size = stream.filesize
                    bytes_downloaded = total_size - bytes_remaining
                    progress = int((bytes_downloaded / total_size) * 100)
                    download_progress[download_id]['progress'] = progress
                
                yt.register_on_progress_callback(progress_callback)
                stream.download(output_path=temp_dir, filename=filename)
                
                # Update download record as completed
                download_record.status = 'completed'
                download_record.download_completed_at = datetime.utcnow()
                
                # Update popular videos tracking
                popular_video = PopularVideo.query.filter_by(video_id=video_id).first()
                if popular_video:
                    popular_video.increment_downloads()
                else:
                    new_popular = PopularVideo(
                        video_id=video_id,
                        video_title=yt.title,
                        author=yt.author,
                        thumbnail_url=yt.thumbnail_url
                    )
                    db.session.add(new_popular)
                
                # Update daily stats
                today = date.today()
                daily_stats = DownloadStats.query.filter_by(date=today).first()
                if not daily_stats:
                    daily_stats = DownloadStats(date=today)
                    db.session.add(daily_stats)
                
                daily_stats.total_downloads += 1
                if download_type == 'video':
                    daily_stats.video_downloads += 1
                else:
                    daily_stats.audio_downloads += 1
                
                daily_stats.total_bytes_downloaded += (stream.filesize or 0)
                
                db.session.commit()
                
                download_progress[download_id]['status'] = 'completed'
                download_progress[download_id]['filepath'] = filepath
                download_progress[download_id]['progress'] = 100
                
                logging.info(f"Download completed: {yt.title} - {quality}")
                
            except Exception as e:
                logging.error(f"Download error: {str(e)}")
                download_progress[download_id]['status'] = 'error'
                download_progress[download_id]['error'] = str(e)
                
                # Update download record as failed
                if download_record:
                    try:
                        download_record.status = 'failed'
                        download_record.error_message = str(e)
                        db.session.commit()
                    except Exception as db_error:
                        logging.error(f"Error updating failed download record: {str(db_error)}")
                        db.session.rollback()
        
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

@app.route('/api/stats')
def get_download_stats():
    """Get download statistics"""
    try:
        from models import DownloadStats, DownloadHistory, PopularVideo
        
        # Get recent daily stats
        recent_stats = DownloadStats.query.order_by(DownloadStats.date.desc()).limit(7).all()
        
        # Get total counts
        total_downloads = db.session.query(db.func.count(DownloadHistory.id)).scalar() or 0
        total_video_downloads = db.session.query(db.func.count(DownloadHistory.id)).filter(
            DownloadHistory.download_type == 'video'
        ).scalar() or 0
        total_audio_downloads = db.session.query(db.func.count(DownloadHistory.id)).filter(
            DownloadHistory.download_type == 'audio'
        ).scalar() or 0
        
        # Get popular videos
        popular_videos = PopularVideo.query.order_by(PopularVideo.download_count.desc()).limit(10).all()
        
        # Get recent downloads
        recent_downloads = DownloadHistory.query.filter(
            DownloadHistory.status == 'completed'
        ).order_by(DownloadHistory.download_completed_at.desc()).limit(10).all()
        
        stats = {
            'total_downloads': total_downloads,
            'total_video_downloads': total_video_downloads,
            'total_audio_downloads': total_audio_downloads,
            'daily_stats': [
                {
                    'date': stat.date.isoformat(),
                    'total_downloads': stat.total_downloads,
                    'video_downloads': stat.video_downloads,
                    'audio_downloads': stat.audio_downloads,
                    'total_bytes': stat.total_bytes_downloaded
                }
                for stat in recent_stats
            ],
            'popular_videos': [
                {
                    'video_id': video.video_id,
                    'title': video.video_title,
                    'author': video.author,
                    'download_count': video.download_count,
                    'thumbnail_url': video.thumbnail_url
                }
                for video in popular_videos
            ],
            'recent_downloads': [
                {
                    'title': download.video_title,
                    'author': download.author,
                    'quality': download.quality,
                    'download_type': download.download_type,
                    'completed_at': download.download_completed_at.isoformat() if download.download_completed_at else None
                }
                for download in recent_downloads
            ]
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logging.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': 'Error retrieving statistics'}), 500

@app.route('/api/history')
def get_download_history():
    """Get download history with pagination"""
    try:
        from models import DownloadHistory
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', 'all')
        
        query = DownloadHistory.query
        
        if status_filter != 'all':
            query = query.filter(DownloadHistory.status == status_filter)
        
        downloads = query.order_by(DownloadHistory.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'downloads': [download.to_dict() for download in downloads.items],
            'total': downloads.total,
            'pages': downloads.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': downloads.has_next,
            'has_prev': downloads.has_prev
        })
        
    except Exception as e:
        logging.error(f"Error getting history: {str(e)}")
        return jsonify({'error': 'Error retrieving download history'}), 500

# Initialize database tables
with app.app_context():
    # Import models to ensure they are registered with SQLAlchemy
    import models
    db.create_all()
    logging.info("Database tables created successfully")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
