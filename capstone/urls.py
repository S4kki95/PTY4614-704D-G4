"""
URL configuration for capstone project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include 
from django.http import HttpResponse
from django.shortcuts import redirect


def redirect_to_portal(request):
    return redirect('index')  # Redirige a la vista 'index' definida en portal/urls.py

def handler404_redirect(request, exception=None):
    """Redirige URLs no encontradas según el estado de autenticación del usuario"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'role'):
            if request.user.role in ['empresa', 'capacitador']:
                return redirect('portal_empresas')
            elif request.user.role == 'alumno':
                return redirect('portal_practicantes')
    return redirect('index')

urlpatterns = [
    path("admin/", admin.site.urls),
    path('portal/', include('portal.urls')),
    path("", redirect_to_portal),  # Página principal redirige a portal
]

# Handler para URLs no encontradas (404)
handler404 = 'capstone.urls.handler404_redirect'