from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from .forms import CustomUserCreationForm, AnuncioPracticaForm
def index(request):
    return render(request, 'portal/index.html')

def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    return render(request, "portal/login.html")

def registro_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # inicia sesión después de registrarse
            return redirect("index")
        else:
            messages.error(request, "Error en el registro. Revisa los datos.")
    else:
        form = CustomUserCreationForm()
    return render(request, "portal/registro.html", {"form": form})

def portal_empresas(request):
    return render(request, 'portal/portal_empresas.html')

def portal_practicantes(request):
    return render(request, 'portal/portal_practicantes.html')


#@login_required
def publicar_anuncio(request):
    if request.method == "POST":
        form = AnuncioPracticaForm(request.POST)
        if form.is_valid():
            anuncio = form.save(commit=False)
            anuncio.empresa = request.user  # asignamos la empresa que publica
            anuncio.save()
            return redirect("index")  # redirige al inicio o lista de anuncios
    else:
        form = AnuncioPracticaForm()
    return render(request, "portal/publicar_anuncio.html", {"form": form})
