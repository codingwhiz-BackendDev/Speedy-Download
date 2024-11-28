from django.shortcuts import render 
import os 
from django.http import HttpResponse
import yt_dlp
from django.contrib import messages

# View to handle YouTube video download
def index(request):
    if request.method == 'POST':
        url = request.POST.get('youTubeLink')
        if url:
             
            messages.info(request, "Download in progress. Please wait...")
            try:

                # Download options
                ydl_opts = {
                    'format': 'bestvideo[height=360]+bestaudio/best',  # Download the best quality
                    'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save location
                    'restrictfilenames': True,  # Use safe filenames
                    'verbose': True,  # Enable detailed logs
                    'noplaylist': True,
                }

                # Create the downloads directory if it doesn't exist
                os.makedirs('downloads', exist_ok=True)

                 
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                 
                messages.success(request, "Video downloaded successfully!")
                return render(request, 'youtube.html')

            except Exception as e:
                # Display error message
                messages.error(request, f"Error: {e}")
                return render(request, 'youtube.html')

        else:
            # Display error message if no URL provided
            messages.error(request, "Error: No URL provided.")
            return render(request, 'youtube.html')
    return render(request, 'youtube.html')


def facebook(request):
    if request.method == 'POST':
        url = request.POST.get('facebookLink')  # Get the Facebook video URL from the form
        if url:
            # Display "Downloading..." message to the user
            messages.info(request, "Download in progress. Please wait...")
            try:
                # Define download options
                ydl_opts = {
                    'format': 'bestvideo[height=360]+bestaudio/best',  # Download the best quality available
                    'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save location
                    'restrictfilenames': True,  # Use safe filenames
                    'verbose': True,  # Enable detailed logs
                    'noplaylist': True,  # Ensure single video downloads (if URL is part of a playlist)
                }

                # Create the downloads directory if it doesn't exist
                os.makedirs('downloads', exist_ok=True)

                # Use yt-dlp to download the Facebook video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Display success message
                messages.success(request, "Facebook video downloaded successfully!")
                return render(request, 'facebook.html')

            except Exception as e:
                # Display error message
                messages.error(request, f"Error: {e}")
                return render(request, 'facebook.html')

        else:
            # Display error message if no URL is provided
            messages.error(request, "Error: No URL provided.")
            return render(request, 'facebook.html')

    return render(request, 'facebook.html')

def instagram(request):     
    if request.method == 'POST':
        url = request.POST.get('instagramLink')  # Get the Instagram video URL from the form
        if url:
            # Inform the user about the download process
            messages.info(request, "Download in progress. Please wait...")
            try:
                # Define download options
                ydl_opts = {
                    'format': 'bestvideo[height=360]+bestaudio/best',  # Download the best available quality
                    'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save to 'downloads' folder
                    'restrictfilenames': True,  # Use safe filenames
                    'verbose': True,  # Enable detailed logs
                }

                # Create the downloads directory if it doesn't exist
                os.makedirs('downloads', exist_ok=True)

                # Use yt-dlp to download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Inform the user of successful download
                messages.success(request, "Instagram video downloaded successfully!")
                return render(request, 'instagram.html')

            except Exception as e:
                # Inform the user of any error
                messages.error(request, f"Error: {e}")
                return render(request, 'instagram.html')
        else:
            # Handle the case where no URL is provided
            messages.error(request, "Error: No URL provided.")
            return render(request, 'instagram.html')

    # Render the Twitter download page
    return render(request, 'instagram.html')

def twitter(request):      
    if request.method == 'POST':
        url = request.POST.get('twitterLink')  # Get the Twitter video URL from the form
        if url:
            # Inform the user about the download process
            messages.info(request, "Download in progress. Please wait...")
            try:
                # Define download options
                ydl_opts = {
                    'format': 'bestvideo[height=360]+bestaudio/best',  # Download the best available quality
                    'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save to 'downloads' folder
                    'restrictfilenames': True,  # Use safe filenames
                    'verbose': True,  # Enable detailed logs
                }

                # Create the downloads directory if it doesn't exist
                os.makedirs('downloads', exist_ok=True)

                # Use yt-dlp to download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Inform the user of successful download
                messages.success(request, "Twitter video downloaded successfully!")
                return render(request, 'twitter.html')

            except Exception as e:
                # Inform the user of any error
                messages.error(request, f"Error: {e}")
                return render(request, 'twitter.html')
        else:
            # Handle the case where no URL is provided
            messages.error(request, "Error: No URL provided.")
            return render(request, 'twitter.html')

    # Render the Twitter download page
    return render(request, 'twitter.html')


 