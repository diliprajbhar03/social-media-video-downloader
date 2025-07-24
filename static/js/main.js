// YouTube Downloader JavaScript

class YouTubeDownloader {
    constructor() {
        this.selectedQuality = null;
        this.currentUrl = null;
        this.downloadId = null;
        this.progressInterval = null;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Get video info button
        document.getElementById('get-info-btn').addEventListener('click', () => {
            this.getVideoInfo();
        });
        
        // Enter key on URL input
        document.getElementById('youtube-url').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.getVideoInfo();
            }
        });
        
        // Download button
        document.getElementById('download-btn').addEventListener('click', () => {
            this.startDownload();
        });
        
        // New download button
        document.getElementById('new-download-btn').addEventListener('click', () => {
            this.resetInterface();
        });
        
        // Retry download button
        document.getElementById('retry-download-btn').addEventListener('click', () => {
            this.startDownload();
        });
    }
    
    async getVideoInfo() {
        const urlInput = document.getElementById('youtube-url');
        const url = urlInput.value.trim();
        
        if (!url) {
            this.showError('Please enter a YouTube URL');
            return;
        }
        
        this.currentUrl = url;
        this.hideError();
        this.showLoading(true);
        this.hideVideoInfo();
        
        try {
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to get video information');
            }
            
            this.displayVideoInfo(data);
            
        } catch (error) {
            console.error('Error getting video info:', error);
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    displayVideoInfo(videoInfo) {
        // Set video details
        document.getElementById('video-thumbnail').src = videoInfo.thumbnail_url;
        document.getElementById('video-title').textContent = videoInfo.title;
        document.getElementById('video-author').textContent = videoInfo.author;
        document.getElementById('video-duration').textContent = videoInfo.duration;
        document.getElementById('video-views').textContent = videoInfo.views;
        
        // Create quality options
        const qualityOptionsContainer = document.getElementById('quality-options');
        qualityOptionsContainer.innerHTML = '';
        
        videoInfo.quality_options.forEach((option, index) => {
            const optionElement = this.createQualityOption(option, index);
            qualityOptionsContainer.appendChild(optionElement);
        });
        
        // Show video info and quality selection
        this.showVideoInfo();
        this.showQualitySelection();
        
        // Add staggered animations
        setTimeout(() => {
            document.getElementById('video-info').classList.add('fade-in');
        }, 100);
        
        setTimeout(() => {
            document.getElementById('quality-selection').classList.add('slide-in-left');
        }, 300);
    }
    
    createQualityOption(option, index) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4';
        
        const card = document.createElement('div');
        card.className = 'card quality-option h-100';
        card.dataset.itag = option.itag;
        card.dataset.quality = option.quality;
        
        const typeIcon = option.type === 'audio' ? 'headphones' : 'video';
        const typeBadge = option.type === 'audio' ? 'Audio' : 'Video';
        
        card.innerHTML = `
            <div class="card-body text-center">
                <i data-feather="${typeIcon}" class="mb-2"></i>
                <h6 class="card-title">${option.quality}</h6>
                <span class="badge bg-secondary quality-badge">${typeBadge}</span>
                <div class="text-muted small mt-2">${option.filesize}</div>
            </div>
        `;
        
        card.addEventListener('click', () => {
            this.selectQuality(option.itag, card);
        });
        
        col.appendChild(card);
        return col;
    }
    
    selectQuality(itag, cardElement) {
        // Remove selection from all options
        document.querySelectorAll('.quality-option').forEach(option => {
            option.classList.remove('selected');
        });
        
        // Select current option
        cardElement.classList.add('selected');
        this.selectedQuality = itag;
        
        // Enable download button
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.classList.remove('disabled');
        downloadBtn.disabled = false;
        
        // Re-initialize feather icons for the new content
        feather.replace();
    }
    
    async startDownload() {
        if (!this.selectedQuality || !this.currentUrl) {
            this.showError('Please select a quality option');
            return;
        }
        
        this.hideError();
        this.showDownloadProgress();
        this.resetDownloadProgress();
        
        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: this.currentUrl,
                    itag: this.selectedQuality
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to start download');
            }
            
            this.downloadId = data.download_id;
            this.monitorDownloadProgress();
            
        } catch (error) {
            console.error('Error starting download:', error);
            this.showDownloadError(error.message);
        }
    }
    
    monitorDownloadProgress() {
        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/download_progress/${this.downloadId}`);
                const progress = await response.json();
                
                if (progress.status === 'downloading') {
                    this.updateProgress(progress.progress || 0);
                    document.getElementById('download-status').innerHTML = `
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Downloading...</span>
                        </div>
                        <span>Downloading... ${progress.progress || 0}%</span>
                    `;
                } else if (progress.status === 'completed') {
                    this.updateProgress(100);
                    this.showDownloadComplete();
                    clearInterval(this.progressInterval);
                } else if (progress.status === 'error') {
                    this.showDownloadError(progress.error || 'Download failed');
                    clearInterval(this.progressInterval);
                }
                
            } catch (error) {
                console.error('Error checking download progress:', error);
                this.showDownloadError('Failed to check download progress');
                clearInterval(this.progressInterval);
            }
        }, 1000);
    }
    
    updateProgress(percentage) {
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.innerHTML = `<span class="fw-bold">${percentage}%</span>`;
    }
    
    showDownloadComplete() {
        document.getElementById('download-status').classList.add('d-none');
        document.getElementById('download-complete').classList.remove('d-none');
        document.getElementById('download-complete').classList.add('bounce-in');
        
        // Set download link
        const downloadLink = document.getElementById('download-link');
        downloadLink.href = `/download_file/${this.downloadId}`;
        
        // Re-initialize feather icons
        feather.replace();
    }
    
    showDownloadError(message) {
        document.getElementById('download-status').classList.add('d-none');
        document.getElementById('download-error').classList.remove('d-none');
        document.getElementById('download-error-message').textContent = message;
        
        // Re-initialize feather icons
        feather.replace();
    }
    
    resetDownloadProgress() {
        document.getElementById('download-status').classList.remove('d-none');
        document.getElementById('download-complete').classList.add('d-none');
        document.getElementById('download-error').classList.add('d-none');
        this.updateProgress(0);
    }
    
    showError(message) {
        const errorAlert = document.getElementById('error-alert');
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
        
        // Re-initialize feather icons
        feather.replace();
    }
    
    hideError() {
        document.getElementById('error-alert').classList.add('d-none');
    }
    
    showLoading(show) {
        const spinner = document.getElementById('loading-spinner');
        const getInfoBtn = document.getElementById('get-info-btn');
        
        if (show) {
            spinner.classList.remove('d-none');
            getInfoBtn.classList.add('loading');
            getInfoBtn.disabled = true;
        } else {
            spinner.classList.add('d-none');
            getInfoBtn.classList.remove('loading');
            getInfoBtn.disabled = false;
        }
    }
    
    showVideoInfo() {
        document.getElementById('video-info').classList.remove('d-none');
    }
    
    hideVideoInfo() {
        document.getElementById('video-info').classList.add('d-none');
        document.getElementById('quality-selection').classList.add('d-none');
        document.getElementById('download-progress').classList.add('d-none');
    }
    
    showQualitySelection() {
        document.getElementById('quality-selection').classList.remove('d-none');
    }
    
    showDownloadProgress() {
        document.getElementById('download-progress').classList.remove('d-none');
    }
    
    resetInterface() {
        // Clear URL input
        document.getElementById('youtube-url').value = '';
        
        // Hide all sections
        this.hideVideoInfo();
        this.hideError();
        
        // Reset variables
        this.selectedQuality = null;
        this.currentUrl = null;
        this.downloadId = null;
        
        // Clear progress interval
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        // Reset download button
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.classList.add('disabled');
        downloadBtn.disabled = true;
        
        // Focus on URL input
        document.getElementById('youtube-url').focus();
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new YouTubeDownloader();
});
