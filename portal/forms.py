from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from .models import CustomUser, AnuncioPractica, PerfilEmpresa, PerfilPostulante, FichaCapacitacion, RegistroEvaluacion
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

class CustomUserCreationForm(UserCreationForm):
    # Para capacitador, permitir seleccionar una empresa existente
    company = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        label="Empresa a la que perteneces",
        help_text="Selecciona la empresa con la que trabajas",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "tu@correo.com"}),
        validators=[EmailValidator(message="Ingresa un correo válido.")],
    )

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "role",
            "company_name",  # solo para empresas
            "company",       # solo para capacitadores
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # limitar el queryset a usuarios con rol empresa
        self.fields["company"].queryset = CustomUser.objects.filter(role="empresa").order_by("company_name", "username")
        # mostrar company_name en el select (si no hay, usar username)
        self.fields["company"].label_from_instance = lambda obj: (obj.company_name or obj.username)
        # placeholder amigable para el select
        self.fields["company"].empty_label = "Selecciona una empresa..."
        # estilo básico
        for name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        company_name = cleaned_data.get("company_name")
        company = cleaned_data.get("company")
        email = cleaned_data.get("email")

        if role == "empresa" and not company_name:
            self.add_error("company_name", "El nombre de la empresa es obligatorio para empresas.")

        if role == "capacitador":
            # Debe existir al menos una empresa y debe seleccionar una
            if CustomUser.objects.filter(role="empresa").count() == 0:
                raise forms.ValidationError("No es posible registrarse como capacitador porque no hay empresas registradas.")
            if not company:
                self.add_error("company", "Debes seleccionar la empresa a la que perteneces para el rol capacitador.")

        # Email válido y único (case-insensitive)
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            self.add_error("email", "Este correo ya está registrado.")

        return cleaned_data

class AnuncioPracticaForm(forms.ModelForm):
    duracion_meses = forms.ChoiceField(
        choices=[(i, f"{i} meses") for i in range(2, 7)],
        label="Duración (meses)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cantidad_horas = forms.IntegerField(
        min_value=1,
        label="Cantidad de horas",
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "Ej: 180"}),
    )
    class Meta:
        model = AnuncioPractica
        fields = [
            "titulo",
            "descripcion",
            "requisitos",
            "tipo_practica",
            "duracion_meses",
            "cantidad_horas",
            "jornada",
            "ubicacion",
            "modalidad",
            "cupos",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: Desarrollador Backend Django"
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Describe las responsabilidades, objetivos y tareas principales..."
            }),
            "requisitos": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "Indica las habilidades o conocimientos requeridos (ej: Python, SQL, trabajo en equipo...)"
            }),
            "tipo_practica": forms.Select(attrs={
                "class": "form-select"
            }),
            "jornada": forms.Select(attrs={
                "class": "form-select"
            }),
            "ubicacion": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: Santiago, Chile"
            }),
            "modalidad": forms.Select(attrs={
                "class": "form-select"
            }),
            "cupos": forms.NumberInput(attrs={
                "class": "form-input",
                "min": 1,
                "value": 1
            }),
        }

        

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo"})
    )

class PerfilEmpresaForm(forms.ModelForm):
    class Meta:
        model = PerfilEmpresa
        fields = ["rubro", "direccion", "telefono", "email_contacto"]
        widgets = {
            "rubro": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email_contacto": forms.EmailInput(attrs={"class": "form-control"}),
        }


class PerfilPostulanteForm(forms.ModelForm):
    # Campo de subida de archivo (no vinculado directamente al modelo)
    cv_file = forms.FileField(
        required=False,
        label="CV",
        widget=forms.FileInput(attrs={"class": "form-control"})
    )
    # Restringir longitudes y caracteres permitidos en nombres (solo letras y espacios)
    nombre = forms.CharField(
        max_length=25,
        label="Nombre",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "maxlength": "25",
            "pattern": r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,25}$",
            "title": "Solo letras (sin espacios, máx. 25 caracteres)"
        }),
    )
    apellido_pat = forms.CharField(
        max_length=25,
        label="Apellido paterno",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "maxlength": "25",
            "pattern": r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,25}$",
            "title": "Solo letras (sin espacios, máx. 25 caracteres)"
        }),
    )
    apellido_mat = forms.CharField(
        max_length=25,
        required=False,
        label="Apellido materno",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "maxlength": "25",
            "pattern": r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,25}$",
            "title": "Solo letras (sin espacios, máx. 25 caracteres)"
        }),
    )

    class Meta:
        model = PerfilPostulante
        fields = ["rut", "nombre", "apellido_pat", "apellido_mat", "correo", "telefono", "institucion"]
        widgets = {
            # RUT sin puntos ni guión. Último carácter puede ser número o K/k. Largo total 8 o 9.
            "rut": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 12345678K",
                "inputmode": "numeric",
                "pattern": r"^[0-9]{7,8}[0-9Kk]$",
                "title": "Ingresa 8 o 9 caracteres: solo números y opcional K/k al final (sin puntos ni guión)"
            }),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "maxlength": "9",
                "pattern": r"^[0-9]{1,9}$",
                "placeholder": "Ej: 912345678",
                "title": "Solo dígitos (máximo 9). No incluyas código de país (+56)."
            }),
            "institucion": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mensaje de ayuda para el usuario
        self.fields["rut"].help_text = "Sin puntos ni guión. 8–9 caracteres: números y, si corresponde, 'K' al final."
        # Placeholder amigable en el selector de institución (al ser ChoiceField, insertamos una opción vacía)
        if "institucion" in self.fields:
            choices = list(self.fields["institucion"].choices)
            # Evitar duplicar si ya existe una vacía
            if not choices or choices[0][0] != "":
                self.fields["institucion"].choices = [("", "Selecciona una institución...")] + choices

    # (Revertido) validación estricta de CV eliminada a solicitud.

    def clean_nombre(self):
        import re
        value = (self.cleaned_data.get("nombre") or "").strip()
        if not re.fullmatch(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,25}$", value):
            raise ValidationError("Nombre inválido. Usa solo letras, sin espacios (máx. 25).")
        return value

    def clean_apellido_pat(self):
        import re
        value = (self.cleaned_data.get("apellido_pat") or "").strip()
        if not re.fullmatch(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,25}$", value):
            raise ValidationError("Apellido paterno inválido. Usa solo letras, sin espacios (máx. 25).")
        return value

    def clean_apellido_mat(self):
        import re
        value = (self.cleaned_data.get("apellido_mat") or "").strip()
        if value and not re.fullmatch(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,25}$", value):
            raise ValidationError("Apellido materno inválido. Usa solo letras, sin espacios (máx. 25).")
        return value

    def clean_telefono(self):
        value = (self.cleaned_data.get("telefono") or "").strip()
        if not value:
            return value
        if not value.isdigit():
            raise ValidationError("El teléfono debe contener solo dígitos, sin + ni espacios.")
        if len(value) > 9:
            raise ValidationError("El teléfono no debe superar 9 dígitos. No incluyas código de país (+56).")
        return value

    def clean_rut(self):
        rut = (self.cleaned_data.get("rut") or "").strip()
        if not rut:
            return rut
        # Normalizar: sin espacios, sin puntos/guiones (se asume vienen sin ellos por el input), a mayúscula para DV
        rut = rut.upper()
        # Validar formato: 8 o 9 caracteres, último 0-9 o K (sin cálculo de DV)
        import re
        if not re.fullmatch(r"^[0-9]{7,8}[0-9K]$", rut):
            raise ValidationError("Formato inválido. Usa solo números y K al final (8 o 9 caracteres, sin puntos ni guión).")
        return rut


# -------------------------------
#   FORMULARIOS CAPACITACIÓN
# -------------------------------

class FichaCapacitacionForm(forms.ModelForm):
    class Meta:
        model = FichaCapacitacion
        fields = [
            "nombre_capacitacion",
            "tipo_capacitacion",
            "fecha_inicio",
            "fecha_termino",
        ]
        widgets = {
            "nombre_capacitacion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Onboarding TI"}),
            "tipo_capacitacion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Técnica / Soft skills"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_termino": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def clean_fecha_inicio(self):
        fecha_inicio = self.cleaned_data.get("fecha_inicio")
        if fecha_inicio is None:
            return fecha_inicio
        hoy = timezone.localdate()
        # No permitir fechas pasadas ni el mismo día
        if fecha_inicio <= hoy:
            raise ValidationError("La fecha de inicio debe ser posterior al día de hoy.")
        return fecha_inicio

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get("fecha_inicio")
        ft = cleaned.get("fecha_termino")
        if fi and ft and ft < fi:
            self.add_error("fecha_termino", "La fecha de término no puede ser anterior a la fecha de inicio.")
        return cleaned

class RegistroEvaluacionForm(forms.ModelForm):
    class Meta:
        model = RegistroEvaluacion
        fields = [
            "fecha_evaluacion",
            "tipo_evaluacion",
            "nota_final",
        ]
        widgets = {
            "fecha_evaluacion": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "tipo_evaluacion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Prueba, Entrevista, Taller"}),
            "nota_final": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "1", "max": "7"}),
        }