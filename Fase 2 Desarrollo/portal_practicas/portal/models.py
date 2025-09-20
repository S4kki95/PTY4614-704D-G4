from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('empresa', 'Empresa'),
        ('practicante', 'Practicante'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='practicante')



class AnuncioPractica(models.Model):
    empresa = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    ubicacion = models.CharField(max_length=150)
    modalidad = models.CharField(
        max_length=50,
        choices=[("remoto", "Remoto"), ("presencial", "Presencial"), ("mixto", "Mixto")],
        default="presencial"
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    cupos = models.PositiveIntegerField(default=1)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.empresa.username}"