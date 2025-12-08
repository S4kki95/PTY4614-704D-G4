from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import pre_save


# ===============================
#   USUARIO BASE
# ===============================
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("alumno", "Alumno"),
        ("empresa", "Empresa"),
        ("capacitador", "Capacitador"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="alumno")
    company_name = models.CharField(max_length=255, blank=True, null=True)  # Solo para empresas
    # Si el usuario es "capacitador", debe estar ligado a una empresa existente
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="capacitadores",
        limit_choices_to={"role": "empresa"},
    )
    habilitado = models.BooleanField(
        default=True,
        help_text="Determina si la cuenta puede acceder al sistema. Empresas y capacitadores requieren verificación por admin."
    )

    def save(self, *args, **kwargs):
        # Si es una cuenta nueva de empresa o capacitador, establecer habilitado=False
        if not self.pk and self.role in ['empresa', 'capacitador']:
            self.habilitado = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"


# ===============================
#   PERFILES
# ===============================

class PerfilEmpresa(models.Model):
    """Información adicional para usuarios con rol Empresa"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_empresa")
    rubro = models.CharField(max_length=200, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email_contacto = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"Perfil Empresa: {self.user.username}"


class PerfilPostulante(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_postulante")
    rut = models.CharField(max_length=10, blank=True, null=True)
    nombre = models.CharField(max_length=200)
    apellido_pat = models.CharField(max_length=200)
    apellido_mat = models.CharField(max_length=200, blank=True, null=True)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    INSTITUCION_CHOICES = (
        ("DUOC UC", "DUOC UC"),
        ("INACAP", "INACAP"),
        ("Universidad de Chile", "Universidad de Chile"),
        ("Pontificia Universidad Católica de Chile", "Pontificia Universidad Católica de Chile"),
        ("Universidad Técnica Federico Santa María", "Universidad Técnica Federico Santa María"),
        ("Universidad de Santiago de Chile", "Universidad de Santiago de Chile"),
        ("Universidad de Concepción", "Universidad de Concepción"),
        ("Universidad Adolfo Ibáñez", "Universidad Adolfo Ibáñez"),
        ("Universidad Austral de Chile", "Universidad Austral de Chile"),
        ("Universidad Diego Portales", "Universidad Diego Portales"),
    )
    institucion = models.CharField(
        max_length=100,
        choices=INSTITUCION_CHOICES,
        blank=True,
        null=True,
        help_text="Casa de estudios del postulante"
    )
    cv = models.URLField(blank=True, null=True)  # 🔁 cambiado de FileField a URLField

    def __str__(self):
        return f"{self.nombre} {self.apellido_pat}"


# ===============================
#   PUBLICACIÓN DE PRÁCTICAS
# ===============================
class AnuncioPractica(models.Model):
    empresa = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="anuncios"
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    requisitos = models.TextField(
        default="No se especifican requisitos."
    )
    tipo_practica = models.CharField(
        max_length=50,
        choices=[
            ("Profesional", "Profesional"),
            ("Laboral", "Laboral"),
        ],
        default="Profesional"
    )
    duracion_meses = models.PositiveIntegerField(
        default=2,
    )
    cantidad_horas = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad total de horas de la práctica"
    )
    jornada = models.CharField(
        max_length=50,
        choices=[
            ("tiempo completo", "Tiempo Completo"),
            ("medio tiempo", "Medio Tiempo"),
            ("flexible", "Flexible"),
        ],
        default="tiempo completo"
    )
    ubicacion = models.CharField(max_length=150)
    modalidad = models.CharField(
        max_length=50,
        choices=[
            ("remoto", "Remoto"),
            ("presencial", "Presencial"),
            ("híbrido", "Híbrido"),
        ],
        default="presencial"
    )
    cupos = models.PositiveIntegerField(default=1)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.empresa.username}"


# ===============================
#   POSTULACIONES
# ===============================
class Postulacion(models.Model):
    postulante = models.ForeignKey(
        PerfilPostulante,
        on_delete=models.CASCADE,
        related_name="postulaciones"
    )
    anuncio = models.ForeignKey(
        AnuncioPractica,
        on_delete=models.CASCADE,
        related_name="postulaciones"
    )
    fecha_postulacion = models.DateField(auto_now_add=True)
    estado = models.CharField(
        max_length=50,
        choices=[
            ("pendiente", "Pendiente"),
            ("aceptado", "Aceptado"),
            ("rechazado", "Rechazado"),
        ],
        default="pendiente"
    )
    documentos = models.FileField(upload_to="postulaciones/", blank=True, null=True)

    def __str__(self):
        return f"{self.postulante.nombre} → {self.anuncio.titulo}"


# ===============================
#   CAPACITACIONES
# ===============================
class FichaCapacitacion(models.Model):
    empresa = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fichas_capacitacion",
        null=True,
        blank=True,
        help_text="Empresa que agenda la capacitación"
    )
    postulacion = models.ForeignKey(
        'Postulacion',
        on_delete=models.CASCADE,
        related_name='fichas',
        null=True,
        blank=True,
        help_text="Postulación específica a la que pertenece esta capacitación"
    )
    postulante = models.ForeignKey(
        PerfilPostulante,
        on_delete=models.CASCADE,
        related_name="capacitaciones"
    )
    nombre_capacitacion = models.CharField(max_length=200)
    tipo_capacitacion = models.CharField(max_length=200)
    detalle = models.TextField(
        max_length=250,
        blank=True,
        null=True,
        help_text="Detalles adicionales: horario, contacto, ubicación, etc. (máx. 250 caracteres)"
    )
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    estado = models.CharField(
        max_length=50,
        choices=[
            ("pendiente", "Pendiente"),
            ("completada", "Completada"),
            ("cancelada", "Cancelada"),
        ],
        default="pendiente"
    )

    def __str__(self):
        return f"{self.nombre_capacitacion} - {self.postulante.nombre}"


# ===============================
#   EVALUACIONES
# ===============================
class RegistroEvaluacion(models.Model):
    capacitacion = models.ForeignKey(
        FichaCapacitacion,
        on_delete=models.CASCADE,
        related_name="evaluaciones"
    )
    fecha_evaluacion = models.DateField()
    tipo_evaluacion = models.CharField(max_length=200)
    nota_final = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f"Evaluación {self.capacitacion.nombre_capacitacion} ({self.nota_final})"


# ===============================
#   LOGS DE POSTULACIONES
# ===============================
class PostulacionLog(models.Model):
    ACCION_CHOICES = (
        ("creada", "Creada"),
        ("estado_cambiado", "Estado cambiado"),
    )

    postulacion = models.ForeignKey('Postulacion', on_delete=models.CASCADE, related_name='logs')
    postulante = models.ForeignKey(PerfilPostulante, on_delete=models.SET_NULL, null=True, blank=True)
    anuncio = models.ForeignKey(AnuncioPractica, on_delete=models.SET_NULL, null=True, blank=True)
    empresa = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='postulacion_logs')
    institucion = models.CharField(max_length=100, blank=True, null=True)
    accion = models.CharField(max_length=50, choices=ACCION_CHOICES)
    old_estado = models.CharField(max_length=50, blank=True, null=True)
    new_estado = models.CharField(max_length=50, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.get_accion_display()} — {self.postulacion_id} ({self.creado_en:%Y-%m-%d %H:%M})"


# ===============================
#   SINCRONIZACIÓN CORREO ALUMNO
# ===============================
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_actualizar_perfil_postulante(sender, instance, created, **kwargs):
    """Mantiene sincronizado el correo entre CustomUser y PerfilPostulante y crea el perfil si no existe para alumnos.
    - Al crear un usuario 'alumno', crea PerfilPostulante si no existe y copia el email.
    - Cuando se actualiza el usuario, si es alumno y el correo del perfil está vacío, lo rellena.
    """
    try:
        if getattr(instance, 'role', None) == 'alumno':
            perfil, _ = PerfilPostulante.objects.get_or_create(user=instance)
            # Si el perfil no tiene correo, copiar el del usuario
            if (not perfil.correo) and instance.email:
                perfil.correo = instance.email
                perfil.save(update_fields=['correo'])
    except Exception:
        # No bloquear el flujo si algo falla aquí
        pass


# ===============
# LOGGING signals
# ===============

@receiver(pre_save, sender=Postulacion)
def _postulacion_presave_capturar_estado(sender, instance: Postulacion, **kwargs):
    # Guarda el estado anterior en memoria para compararlo en post_save
    if instance.pk:
        try:
            old = Postulacion.objects.get(pk=instance.pk)
            instance._old_estado = old.estado
        except Postulacion.DoesNotExist:
            instance._old_estado = None
    else:
        instance._old_estado = None


@receiver(post_save, sender=Postulacion)
def _postulacion_crear_log(sender, instance: Postulacion, created, **kwargs):
    try:
        if created:
            PostulacionLog.objects.create(
                postulacion=instance,
                postulante=instance.postulante,
                anuncio=instance.anuncio,
                empresa=getattr(instance.anuncio, 'empresa', None),
                institucion=instance.postulante.institucion,
                accion='creada',
                new_estado=instance.estado,
            )
        else:
            old_estado = getattr(instance, '_old_estado', None)
            if old_estado is not None and old_estado != instance.estado:
                PostulacionLog.objects.create(
                    postulacion=instance,
                    postulante=instance.postulante,
                    anuncio=instance.anuncio,
                    empresa=getattr(instance.anuncio, 'empresa', None),
                    institucion=instance.postulante.institucion,
                    accion='estado_cambiado',
                    old_estado=old_estado,
                    new_estado=instance.estado,
                )
    except Exception:
        # No bloquear operaciones si falla el logging
        pass
