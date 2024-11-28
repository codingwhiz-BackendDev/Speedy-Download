from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name = 'index'),
    path('facebook', views.facebook, name = 'facebook'),
    path('instagram', views.instagram, name = 'instagram'),
    path('twitter', views.twitter, name = 'twitter'), 
]