# Social Media Video Downloader

A powerful Flask-based web application that allows you to download videos from multiple social media platforms in various qualities.

## 🌟 Supported Platforms

- **YouTube** - Videos in multiple resolutions and audio-only formats
- **Instagram** - Posts, Reels, IGTV, and Stories
- **Facebook** - Videos and Watch content
- **Twitter/X** - Tweet videos
- **Snapchat** - Spotlight videos and Stories

## ✨ Features

- 🎯 Automatic platform detection from URL
- 📊 Multiple quality options including audio-only
- ⚡ Real-time download progress tracking
- 🎨 Modern dark theme UI with glassmorphism effects
- 📱 Fully responsive design
- 💾 PostgreSQL database for download history and statistics
- 🔄 Video information caching for better performance
- 📈 Download analytics and popular videos tracking

## 🛠️ Technologies Used

- **Backend**: Flask (Python)
- **Video Processing**: 
  - pytubefix for YouTube
  - yt-dlp for Instagram, Facebook, Twitter, and Snapchat
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: 
  - Bootstrap 5 (Dark Theme)
  - Vanilla JavaScript
  - Feather Icons
- **Server**: Gunicorn

## 📋 Requirements

- Python 3.11+
- PostgreSQL database
- Required Python packages (see installation)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/diliprajbhar03/social-media-video-downloader.git
cd social-media-video-downloader
```

2. Install dependencies:
```bash
pip install flask flask-sqlalchemy gunicorn psycopg2-binary pytubefix yt-dlp
```

3. Set up environment variables:
```bash
export DATABASE_URL="your_postgresql_connection_string"
export SESSION_SECRET="your_secret_key"
```

4. Run the application:
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

5. Open your browser and navigate to `http://localhost:5000`

## 💻 Usage

1. Paste a video URL from any supported platform
2. Click "Get Video Info" to fetch video details
3. Select your preferred quality
4. Click download and wait for the file to be ready
5. Your download will start automatically

## 📁 Project Structure

```
├── app.py              # Main Flask application
├── models.py           # Database models
├── main.py             # Application entry point
├── templates/          # HTML templates
│   ├── base.html
│   └── index.html
└── static/             # Static assets
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## 🔐 Security Notes

- Never commit your `DATABASE_URL` or `SESSION_SECRET` to version control
- Use environment variables for sensitive data
- The app uses secure session management

## 📝 Database Schema

The application tracks:
- Download history with platform information
- Video metadata caching
- Download statistics and analytics
- Popular videos tracking

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

## 📄 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

**Dilip Rajbhar**
- GitHub: [@diliprajbhar03](https://github.com/diliprajbhar03)

## ⚠️ Disclaimer

This tool is for personal use only. Please respect copyright laws and the terms of service of the platforms you're downloading from.

---

Made with ❤️ using Flask and Python
