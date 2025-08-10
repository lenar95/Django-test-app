from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.ProfileListView.as_view(), name='list'),
    path('add/', views.ProfileCreateView.as_view(), name='add'),
]


