"""
Middleware personalizado para manejar URLs no encontradas
"""
from django.shortcuts import redirect
from django.urls import resolve
from django.urls.exceptions import Resolver404


class Custom404Middleware:
    """Middleware que redirige URLs no válidas según el estado de autenticación"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            resolve(request.path_info)
        except Resolver404:
            # URL no encontrada, redirigir según usuario
            if request.user.is_authenticated:
                # Si es admin/staff, redirigir a analytics
                if request.user.is_staff or request.user.is_superuser:
                    return redirect('admin_analytics')
                
                if hasattr(request.user, 'role'):
                    if request.user.role in ['empresa', 'capacitador']:
                        return redirect('portal_empresas')
                    elif request.user.role == 'alumno':
                        return redirect('portal_practicantes')
            return redirect('index')
        
        response = self.get_response(request)
        return response
