from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #path('login/', views.login, name='login'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('registro/', views.registro_view, name='registro'),
    path('portal_practicantes/', views.portal_practicantes, name='portal_practicantes'),
    path('portal_empresas/', views.portal_empresas, name='portal_empresas'),
    path('publicar_anuncio/', views.publicar_anuncio, name='publicar_anuncio'), 
    path('gestionar_publicaciones/', views.gestionar_publicaciones, name='gestionar_publicaciones'),
    path("gestionar_publicaciones/<int:anuncio_id>/editar/", views.editar_publicacion, name="editar_publicacion"),
    path("gestionar_publicaciones/<int:anuncio_id>/eliminar/", views.eliminar_publicacion, name="eliminar_publicacion"),
    path("editar_publicacion/<int:anuncio_id>/", views.editar_publicacion, name="editar_publicacion"),
    path('perfil/empresa/', views.perfil_empresa, name='perfil_empresa'),
    path('perfil/postulante/', views.perfil_postulante, name='perfil_postulante'),
    path("publicaciones/", views.listar_publicaciones, name="listar_publicaciones"),
    path("publicaciones/postular/<int:anuncio_id>/", views.postular_practica, name="postular_practica"),
    path("mis_postulaciones/", views.mis_postulaciones, name="mis_postulaciones"),
    path("mis_capacitaciones/", views.mis_capacitaciones, name="mis_capacitaciones"),
    path("empresa/postulaciones/", views.ver_postulaciones_empresa, name="ver_postulaciones_empresa"),
    # Colocar ver-cv antes de la ruta genérica de estado y hacer la ruta de estado más específica para evitar colisiones
    path("empresa/postulaciones/<int:postulacion_id>/ver-cv/", views.ver_cv_postulacion, name="ver_cv_postulacion"),
    path("empresa/postulaciones/<int:postulacion_id>/estado/<str:nuevo_estado>/", views.cambiar_estado_postulacion, name="cambiar_estado_postulacion"),
    path("portal/perfil/descargar-cv/", views.descargar_cv, name="descargar_cv"),
    path("portal/perfil/ver-cv/", views.ver_cv_propio, name="ver_cv_propio"),
    # Capacitaciones (capacitador/empresa)
    path("capacitaciones/", views.capacitaciones, name="capacitaciones"),
    path("capacitaciones/<int:postulacion_id>/agendar/", views.agendar_capacitacion, name="agendar_capacitacion"),
    path("capacitaciones/ficha/<int:ficha_id>/evaluar/", views.evaluar_capacitacion, name="evaluar_capacitacion"),
    # Admin analytics (staff)
    path("admin/analytics/", views.admin_analytics, name="admin_analytics"),
    # Friendly alias to avoid confusion with Django Admin at /admin/
    path("analytics/", views.admin_analytics, name="analytics"),
]
