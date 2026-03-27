from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("lock/sync/", views.lock_sync, name="lock_sync"),
    path("lock/<int:lock_id>/passcode/", views.passcode_add, name="passcode_add"),
]
