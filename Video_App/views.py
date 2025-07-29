import os
import json
import logging
import tempfile
import subprocess
import signal
from urllib.parse import urlparse
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoDownloaderService:
    
    def __init__(self):
        self.download_dir = getattr(settings, 'DOWNLOAD_DIR', os.path.join(settings.MEDIA_ROOT, 'downloads'))
        self.ensure_download_dir()
    
    def ensure_download_dir(self):
        """Ensure download directory exists"""
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir, exist_ok=True)
    
    def _cleanup_temp_dir(self, temp_dir):
        """Helper to clean up temporary directories."""
        if os.path.exists(temp_dir):
            try:
                for f in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    def validate_url(self, url):
        """Validate if URL is from supported platforms"""
        if not url or not url.strip():
            return False, "URL cannot be empty"
        
        supported_domains = [
            'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch',
            'instagram.com', 'twitter.com', 'x.com', 'tiktok.com',
            'vimeo.com', 'dailymotion.com'
        ]
        
        try:
            parsed_url = urlparse(url.strip())
            domain = parsed_url.netloc.lower()
            
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            for supported_domain in supported_domains:
                if domain == supported_domain or domain.endswith('.' + supported_domain):
                    return True, "Valid URL"
            
            return False, f"Unsupported platform. Supported: {', '.join(supported_domains)}"
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    def extract_video_info(self, url):
        """Extract video information including available formats"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'cookiefile': None,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'extractor_retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract relevant information
                video_info = {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', ''),
                    'formats': []
                }
                
                # Process available formats
                formats = info.get('formats', [])
                processed_formats = self.process_formats(formats)
                video_info['formats'] = processed_formats
                
                return True, video_info
                
        except yt_dlp.DownloadError as e:
            logger.error(f"yt-dlp download error: {str(e)}")
            return False, f"Failed to extract video info: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in extract_video_info: {str(e)}")
            return False, f"An unexpected error occurred: {str(e)}"
    
    def process_formats(self, formats):
        """Process and categorize available formats"""
        processed_formats = []
        seen_qualities = set()
        
        # Separate video and audio formats
        video_formats = []
        audio_formats = []
        combined_formats = []  # Formats that already have both video and audio
        
        for f in formats:
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            height = f.get('height')
            
            if vcodec != 'none' and acodec != 'none' and height:
                # Format has both video and audio
                combined_formats.append(f)
            elif vcodec != 'none' and height and isinstance(height, (int, float)) and height > 0:
                # Video only format
                format_id = f.get('format_id', '')
                protocol = f.get('protocol', '')
                
                # Skip problematic formats
                if protocol in ['m3u8_native'] and 'hls' in format_id:
                    continue
                
                video_formats.append(f)
            elif acodec != 'none' and vcodec == 'none':
                # Audio only format
                audio_formats.append(f)
        
        # Sort formats by quality
        def sort_key(x):
            height = x.get('height', 0) or 0
            fps = x.get('fps', 0) or 0
            return (height, fps)
        
        # Process combined formats first (these don't need merging)
        combined_formats.sort(key=sort_key, reverse=True)
        for fmt in combined_formats:
            height = fmt.get('height')
            if not height or height <= 0:
                continue
                
            quality_id = f"{height}p"
            fps = fmt.get('fps') or 30
            if fps > 30:
                quality_id += f"{fps}"
            
            if quality_id not in seen_qualities:
                seen_qualities.add(quality_id)
                
                filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                
                format_info = {
                    'format_id': fmt.get('format_id'),
                    'quality': f"{quality_id} (ready to download)",
                    'height': height,
                    'width': fmt.get('width') or 0,
                    'fps': fps,
                    'ext': fmt.get('ext', 'mp4'),
                    'vcodec': fmt.get('vcodec', 'unknown'),
                    'acodec': fmt.get('acodec', 'unknown'),
                    'has_audio': True,
                    'filesize': filesize,
                    'filesize_mb': f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Unknown",
                    'category': self.get_quality_category(height),
                    'note': "Complete video with audio - no merging needed",
                    'protocol': fmt.get('protocol', 'https'),
                    'will_merge': False,
                    'is_large': filesize and filesize > 1024 * 1024 * 1024,  # > 1GB
                }
                
                processed_formats.append(format_info)
        
        # Process video-only formats (these will need merging)
        video_formats.sort(key=sort_key, reverse=True)
        
        # Get best audio format for size estimation
        best_audio = None
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
        
        for fmt in video_formats:
            height = fmt.get('height')
            if not height or height <= 0:
                continue
            
            quality_id = f"{height}p"
            fps = fmt.get('fps') or 30
            if fps > 30:
                quality_id += f"{fps}"
            
            # Skip if we already have this quality from combined formats
            if quality_id in seen_qualities:
                continue
                
            seen_qualities.add(quality_id)
            
            video_filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            
            # Calculate estimated combined size
            estimated_size = None
            estimated_size_mb = None
            is_large = False
            
            if video_filesize and best_audio and best_audio.get('filesize'):
                estimated_size = video_filesize + best_audio.get('filesize')
                estimated_size_mb = round(estimated_size / (1024 * 1024), 1)
                is_large = estimated_size > 1024 * 1024 * 1024  # > 1GB
            elif video_filesize:
                estimated_size = int(video_filesize * 1.1)
                estimated_size_mb = round(estimated_size / (1024 * 1024), 1)
                is_large = estimated_size > 1024 * 1024 * 1024  # > 1GB
            
            # Add warning for large files
            quality_display = f"{quality_id} (video + audio)"
            note = "Video will be merged with audio"
            
            if is_large:
                quality_display += " ⚠️"
                note += " - Large file, merging may take time"
            
            format_info = {
                'format_id': fmt.get('format_id'),
                'quality': quality_display,
                'height': height,
                'width': fmt.get('width') or 0,
                'fps': fps,
                'ext': 'mp4',
                'vcodec': fmt.get('vcodec', 'unknown'),
                'acodec': 'merged',
                'has_audio': False,
                'filesize': estimated_size,
                'filesize_mb': f"{round(estimated_size / (1024 * 1024), 1)} MB" if estimated_size else "Unknown",
                'category': self.get_quality_category(height),
                'note': note,
                'protocol': fmt.get('protocol', 'https'),
                'will_merge': True,
                'is_large': is_large,
            }
            
            processed_formats.append(format_info)
        
        # Add audio-only option
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            processed_formats.append({
                'format_id': best_audio.get('format_id'),
                'quality': 'Audio Only (MP3)',
                'height': 0,
                'width': 0,
                'fps': 0,
                'ext': 'mp3',
                'vcodec': 'none',
                'acodec': best_audio.get('acodec', 'unknown'),
                'has_audio': True,
                'filesize': best_audio.get('filesize'),
                'filesize_mb': f"{round(best_audio.get('filesize', 0) / (1024 * 1024), 1)} MB" if best_audio.get('filesize') else "Unknown",
                'category': 'Audio',
                'note': 'Audio only - converted to MP3',
                'protocol': best_audio.get('protocol', 'https'),
                'will_merge': False,
                'is_large': False,
            })
        
        return processed_formats
    
    def get_quality_category(self, height):
        """Categorize video quality based on height"""
        if height >= 2160:
            return '4K'
        elif height >= 1440:
            return '2K'
        elif height >= 1080:
            return 'Full HD'
        elif height >= 720:
            return 'HD'
        elif height >= 480:
            return 'SD'
        else:
            return 'Low'
    
    def download_video(self, url, format_id=None, quality=None, download_type='video'):
        """Download video with specified quality, with fallback for 403 errors."""
        
        logger.info(f"Download type received: {download_type}, Selected quality: {quality}, Selected format_id: {format_id}")
        
        # Define potential format selectors
        primary_format_selector = None
        fallback_format_selector = None

        if download_type == 'audio':
            primary_format_selector = 'bestaudio/best'
        elif format_id:
            primary_format_selector = f'{format_id}+bestaudio/best'
            # If a specific format_id is chosen, prepare a fallback to a general quality selector
            if quality and quality.endswith('p'):
                height_str = quality.split('p')[0].split(' ')[0]
                fallback_format_selector = f'bestvideo[height<={height_str}]+bestaudio/best[height<={height_str}]'
            else:
                fallback_format_selector = 'bestvideo+bestaudio/best' # Generic fallback
        elif quality == 'best':
            primary_format_selector = 'bestvideo+bestaudio/best'
        elif quality == 'worst':
            primary_format_selector = 'worstvideo+worstaudio/worst' 
        elif quality and quality.endswith('p'):
            height_str = quality.split('p')[0].split(' ')[0]
            primary_format_selector = f'bestvideo[height<={height_str}]+bestaudio/best[height<={height_str}]'
        else:
            primary_format_selector = 'bestvideo+bestaudio/best'
        
        # List of format selectors to try, in order of preference
        format_selectors_to_try = [primary_format_selector]
        if fallback_format_selector and primary_format_selector != fallback_format_selector:
            format_selectors_to_try.append(fallback_format_selector)
        
        final_error_message = "Download failed after multiple attempts."

        for current_format_selector in format_selectors_to_try:
            logger.info(f"Attempting download with format selector: {current_format_selector}")
            
            temp_dir = tempfile.mkdtemp()
            
            ydl_opts = {
                'format': current_format_selector,
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'restrictfilenames': True,
                'noplaylist': True,
                'extract_flat': False,
                'writethumbnail': False,
                'writeinfojson': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'extractor_retries': 3,
                'fragment_retries': 5,
                'skip_unavailable_fragments': True,
                'ignoreerrors': False,
                'no_warnings': False,
                'retries': 3,
                'http_chunk_size': 10485760,  # 10MB chunks
                'merge_output_format': 'mp4',
                'socket_timeout': 300,  # 5 minutes
            }
            
            if download_type == 'audio':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                ydl_opts['postprocessor_args'] = {
                    'ffmpeg': [
                        '-c', 'copy',
                        '-avoid_negative_ts', 'make_zero',
                        '-fflags', '+genpts',
                        '-movflags', '+faststart'
                    ]
                }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'video')
                    
                    ydl.download([url])
                    
                    downloaded_files = os.listdir(temp_dir)
                    if downloaded_files:
                        downloaded_file = os.path.join(temp_dir, downloaded_files[0])
                        if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                            return True, downloaded_file, title
                        else:
                            final_error_message = "Downloaded file is empty or corrupted."
                            logger.error(final_error_message)
                            # Clean up temp dir and try next format selector if available
                            self._cleanup_temp_dir(temp_dir)
                            continue 
                    else:
                        final_error_message = "No file was downloaded."
                        logger.error(final_error_message)
                        self._cleanup_temp_dir(temp_dir)
                        continue
                        
            except yt_dlp.DownloadError as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "merge" in error_msg.lower():
                    final_error_message = "Download timed out during merging. Try a smaller file size or audio-only option."
                    logger.error(final_error_message)
                    return False, final_error_message, None # This is a critical error, no point in retrying with other formats
                elif "http error 403" in error_msg.lower() or "requested format is not available" in error_msg.lower():
                    final_error_message = f"Format unavailable or restricted: {error_msg}. Trying next available format if possible."
                    logger.warning(final_error_message)
                    self._cleanup_temp_dir(temp_dir)
                    continue # Try next format selector
                else:
                    final_error_message = f"Download failed: {error_msg}"
                    logger.error(final_error_message)
                    self._cleanup_temp_dir(temp_dir)
                    return False, final_error_message, None # Other download errors are likely fatal for all formats
            except Exception as e:
                final_error_message = f"An unexpected error occurred: {str(e)}"
                logger.error(final_error_message)
                self._cleanup_temp_dir(temp_dir)
                return False, final_error_message, None
            finally:
                # Ensure temp directory is cleaned up even if an unexpected error occurs
                self._cleanup_temp_dir(temp_dir)
        
        return False, final_error_message, None # If all attempts fail

# Initialize service
downloader_service = VideoDownloaderService()

def index(request):
    """Main page view"""
    return render(request, 'index.html')

def youtube_downloader(request):
    """YouTube downloader view with quality selection"""
    if request.method == 'POST':
        url = request.POST.get('urlLink', '').strip()
        selected_format = request.POST.get('format_id')
        selected_quality = request.POST.get('quality')
        action = request.POST.get('action', 'get_info')
        
        # Validate URL
        is_valid, validation_message = downloader_service.validate_url(url)
        if not is_valid:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': validation_message
                })
            else:
                messages.error(request, validation_message)
                return render(request, 'index.html')
        
        if action == 'get_info':
            # Extract video information and available formats
            success, video_info = downloader_service.extract_video_info(url)
            
            if success:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'video_info': video_info
                    })
                else:
                    context = {
                        'video_info': video_info,
                        'url': url,
                        'show_formats': True
                    }
                    return render(request, 'index.html', context)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': video_info
                    })
                else:
                    messages.error(request, f"Failed to get video info: {video_info}")
                    return render(request, 'index.html')
        
        elif action == 'download':
            # Determine download_type based on selected_quality for explicit passing
            effective_download_type = 'video'
            if selected_quality == 'Audio Only (MP3)':
                effective_download_type = 'audio'
            
            logger.info(f"Attempting download. URL: {url}, Format ID: {selected_format}, Quality: {selected_quality}, Effective Download Type: {effective_download_type}")

            # Download with selected quality
            success, result, title = downloader_service.download_video(
                url, 
                format_id=selected_format, 
                quality=selected_quality,
                download_type=effective_download_type # Pass the determined type explicitly
            )
            
            if success:
                # Serve the file for download
                try:
                    with open(result, 'rb') as file:
                        response = HttpResponse(
                            file.read(),
                            content_type='application/octet-stream'
                        )
                        filename = os.path.basename(result)
                        response['Content-Disposition'] = f'attachment; filename="{filename}"'
                        
                        # Clean up temp file after serving
                        try:
                            os.remove(result)
                            os.rmdir(os.path.dirname(result))
                        except:
                            pass
                            
                        return response
                except Exception as e:
                    messages.error(request, f"Failed to serve download: {str(e)}")
                    return render(request, 'index.html')
            else:
                messages.error(request, result)
                return render(request, 'index.html')
    
    return render(request, 'index.html')

def facebook_downloader(request):
    """Facebook video downloader"""
    if request.method == 'POST':
        url = request.POST.get('urlLink', '').strip()
        
        # Validate URL
        is_valid, validation_message = downloader_service.validate_url(url)
        if not is_valid:
            messages.error(request, validation_message)
            return render(request, 'facebook.html')
        
        # Check if it's a format selection request
        if request.POST.get('action') == 'get_info':
            success, video_info = downloader_service.extract_video_info(url)
            if success:
                context = {
                    'video_info': video_info,
                    'url': url,
                    'show_formats': True
                }
                return render(request, 'facebook.html', context)
            else:
                messages.error(request, f"Failed to get video info: {video_info}")
                return render(request, 'facebook.html')
        
        # Download with selected quality
        selected_format = request.POST.get('format_id')
        selected_quality = request.POST.get('quality', 'best')
        
        # Determine download_type based on selected_quality for explicit passing
        effective_download_type = 'video'
        if selected_quality == 'Audio Only (MP3)':
            effective_download_type = 'audio'

        success, result, title = downloader_service.download_video(
            url, 
            format_id=selected_format, 
            quality=selected_quality,
            download_type=effective_download_type
        )
        
        if success:
            try:
                with open(result, 'rb') as file:
                    response = HttpResponse(
                        file.read(),
                        content_type='application/octet-stream'
                    )
                    filename = os.path.basename(result)
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    # Clean up
                    try:
                        os.remove(result)
                        os.rmdir(os.path.dirname(result))
                    except:
                        pass
                        
                    return response
            except Exception as e:
                messages.error(request, f"Failed to serve download: {str(e)}")
                return render(request, 'facebook.html')
        else:
            messages.error(request, result)
            return render(request, 'facebook.html')
    
    return render(request, 'facebook.html')

def instagram_downloader(request):
    """Instagram video downloader"""
    if request.method == 'POST':
        url = request.POST.get('urlLink', '').strip()
        
        is_valid, validation_message = downloader_service.validate_url(url)
        if not is_valid:
            messages.error(request, validation_message)
            return render(request, 'instagram.html')
        
        if request.POST.get('action') == 'get_info':
            success, video_info = downloader_service.extract_video_info(url)
            if success:
                context = {
                    'video_info': video_info,
                    'url': url,
                    'show_formats': True
                }
                return render(request, 'instagram.html', context)
            else:
                messages.error(request, f"Failed to get video info: {video_info}")
                return render(request, 'instagram.html')
        
        selected_format = request.POST.get('format_id')
        selected_quality = request.POST.get('quality', 'best')
        
        # Determine download_type based on selected_quality for explicit passing
        effective_download_type = 'video'
        if selected_quality == 'Audio Only (MP3)':
            effective_download_type = 'audio'

        success, result, title = downloader_service.download_video(
            url, 
            format_id=selected_format, 
            quality=selected_quality,
            download_type=effective_download_type
        )
        
        if success:
            try:
                with open(result, 'rb') as file:
                    response = HttpResponse(
                        file.read(),
                        content_type='application/octet-stream'
                    )
                    filename = os.path.basename(result)
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    # Clean up
                    try:
                        os.remove(result)
                        os.rmdir(os.path.dirname(result))
                    except:
                        pass
                        
                    return response
            except Exception as e:
                messages.error(request, f"Failed to serve download: {str(e)}")
                return render(request, 'instagram.html')
        else:
            messages.error(request, result)
            return render(request, 'instagram.html')
    
    return render(request, 'instagram.html')

def twitter_downloader(request):
    """Twitter video downloader"""
    if request.method == 'POST':
        url = request.POST.get('urlLink', '').strip()
        
        is_valid, validation_message = downloader_service.validate_url(url)
        if not is_valid:
            messages.error(request, validation_message)
            return render(request, 'twitter.html')
        
        if request.POST.get('action') == 'get_info':
            success, video_info = downloader_service.extract_video_info(url)
            if success:
                context = {
                    'video_info': video_info,
                    'url': url,
                    'show_formats': True
                }
                return render(request, 'twitter.html', context)
            else:
                messages.error(request, f"Failed to get video info: {video_info}")
                return render(request, 'twitter.html')
        
        selected_format = request.POST.get('format_id')
        selected_quality = request.POST.get('quality', 'best')
        
        # Determine download_type based on selected_quality for explicit passing
        effective_download_type = 'video'
        if selected_quality == 'Audio Only (MP3)':
            effective_download_type = 'audio'

        success, result, title = downloader_service.download_video(
            url, 
            format_id=selected_format, 
            quality=selected_quality,
            download_type=effective_download_type
        )
        
        if success:
            try:
                with open(result, 'rb') as file:
                    response = HttpResponse(
                        file.read(),
                        content_type='application/octet-stream'
                    )
                    filename = os.path.basename(result)
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    # Clean up
                    try:
                        os.remove(result)
                        os.rmdir(os.path.dirname(result))
                    except:
                        pass
                        
                    return response
            except Exception as e:
                messages.error(request, f"Failed to serve download: {str(e)}")
                return render(request, 'twitter.html')
        else:
            messages.error(request, result)
            return render(request, 'twitter.html')
    
    return render(request, 'twitter.html')

@csrf_exempt
def get_video_info_ajax(request):
    """AJAX endpoint to get video information"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get('url', '').strip()
            
            is_valid, validation_message = downloader_service.validate_url(url)
            if not is_valid:
                return JsonResponse({
                    'success': False,
                    'error': validation_message
                })
            
            success, video_info = downloader_service.extract_video_info(url)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'video_info': video_info
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': video_info
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

def download_progress(request):
    """WebSocket or long-polling endpoint for download progress"""
    # This would require additional setup for real-time progress
    # For now, return a simple JSON response
    return JsonResponse({
        'status': 'in_progress',
        'progress': 50,  # This would be dynamic in a real implementation
        'message': 'Downloading...'
    })
