from django.urls import path
from . import views

urlpatterns = [
    path('routes/', views.RoutesView.as_view()),
]
