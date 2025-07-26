from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name = 'index'),
    path('youtube', views.youtube_downloader, name = 'youtube'),
    path('facebook', views.facebook_downloader, name = 'facebook'),
    path('instagram', views.instagram_downloader, name = 'instagram'),
    path('twitter', views.twitter_downloader, name = 'twitter'), 
]