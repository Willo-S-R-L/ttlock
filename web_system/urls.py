from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("lock/sync/", views.sync_locks, name="sync_locks")
]
