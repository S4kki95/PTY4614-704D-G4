from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, AnuncioPractica

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2", "role")
        widgets = {
            "role": forms.Select(attrs={"class": "big-select"})
        }        

class AnuncioPracticaForm(forms.ModelForm):
    class Meta:
        model = AnuncioPractica
        fields = ["titulo", "descripcion", "ubicacion", "modalidad", "fecha_inicio", "fecha_fin", "cupos"]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej: Desarrollador Backend Django"}),
            "descripcion": forms.Textarea(attrs={"class": "form-textarea", "rows": 5, "placeholder": "Describe las tareas y requisitos..."}),
            "ubicacion": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ciudad o remoto"}),
            "modalidad": forms.Select(attrs={"class": "form-select"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "cupos": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
        }
