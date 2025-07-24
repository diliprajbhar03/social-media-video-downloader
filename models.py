from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Import the db instance from app.py
from app import db

class DownloadHistory(db.Model):
    """Model to track download history"""
    __tablename__ = 'download_history'
    
    id = db.Column(db.Integer, primary_key=True)
    video_title = db.Column(db.String(500), nullable=False)
    video_url = db.Column(db.String(1000), nullable=False)
    video_id = db.Column(db.String(50), nullable=False)  # YouTube video ID
    author = db.Column(db.String(200))
    duration = db.Column(db.Integer)  # Duration in seconds
    views = db.Column(db.BigInteger)
    thumbnail_url = db.Column(db.String(1000))
    
    # Download details
    quality = db.Column(db.String(50), nullable=False)  # e.g., "720p", "Audio Only"
    download_type = db.Column(db.String(20), nullable=False)  # "video" or "audio"
    file_size = db.Column(db.BigInteger)  # File size in bytes
    itag = db.Column(db.String(10))  # YouTube stream itag
    
    # User and session info
    user_ip = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.Text)
    session_id = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    download_started_at = db.Column(db.DateTime)
    download_completed_at = db.Column(db.DateTime)
    
    # Status tracking
    status = db.Column(db.String(20), default='initiated')  # initiated, downloading, completed, failed
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<DownloadHistory {self.video_title[:50]}...>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'video_title': self.video_title,
            'video_url': self.video_url,
            'video_id': self.video_id,
            'author': self.author,
            'duration': self.duration,
            'views': self.views,
            'quality': self.quality,
            'download_type': self.download_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'download_completed_at': self.download_completed_at.isoformat() if self.download_completed_at else None,
            'status': self.status
        }

class VideoInfo(db.Model):
    """Model to cache video information"""
    __tablename__ = 'video_info'
    
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(50), unique=True, nullable=False)
    video_url = db.Column(db.String(1000), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(200))
    duration = db.Column(db.Integer)
    views = db.Column(db.BigInteger)
    thumbnail_url = db.Column(db.String(1000))
    description = db.Column(db.Text)
    
    # Quality options (stored as JSON string)
    available_qualities = db.Column(db.Text)  # JSON string of quality options
    
    # Cache management
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    access_count = db.Column(db.Integer, default=1)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<VideoInfo {self.title[:50]}...>'
    
    def update_access(self):
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        db.session.commit()

class DownloadStats(db.Model):
    """Model to track overall download statistics"""
    __tablename__ = 'download_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, default=datetime.utcnow().date())
    
    # Daily counters
    total_downloads = db.Column(db.Integer, default=0)
    video_downloads = db.Column(db.Integer, default=0)
    audio_downloads = db.Column(db.Integer, default=0)
    failed_downloads = db.Column(db.Integer, default=0)
    
    # Data volume
    total_bytes_downloaded = db.Column(db.BigInteger, default=0)
    
    # Unique users
    unique_ips = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DownloadStats {self.date} - {self.total_downloads} downloads>'

class PopularVideo(db.Model):
    """Model to track most popular videos"""
    __tablename__ = 'popular_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(50), unique=True, nullable=False)
    video_title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(200))
    thumbnail_url = db.Column(db.String(1000))
    
    # Popularity metrics
    download_count = db.Column(db.Integer, default=1)
    first_downloaded = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_downloaded = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PopularVideo {self.video_title[:50]}... - {self.download_count} downloads>'
    
    def increment_downloads(self):
        """Increment download count"""
        self.download_count += 1
        self.last_downloaded = datetime.utcnow()
        db.session.commit()