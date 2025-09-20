from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('portal_practicantes/', views.portal_practicantes, name='practicantes'),
    path('portal_empresas/', views.portal_empresas, name='empresas'),
    path('publicar_anuncio/', views.publicar_anuncio, name='publicar_anuncio'), 
]
