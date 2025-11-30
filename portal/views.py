from io import BytesIO
import json
import mimetypes
import os
import uuid
from django.utils.text import slugify
import re
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from supabase import create_client, Client
from django.db.models import Q, Count

from portal.models import AnuncioPractica, PerfilEmpresa, PerfilPostulante, Postulacion, FichaCapacitacion 
from decimal import Decimal
from .forms import EmailLoginForm, PerfilEmpresaForm, PerfilPostulanteForm, FichaCapacitacionForm, RegistroEvaluacionForm
from .forms import CustomUserCreationForm, AnuncioPracticaForm

def index(request):
    return render(request, 'portal/index.html')

def login_view(request):
    if request.method == "POST":
        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Verificar si la cuenta está habilitada (no aplica para staff/superuser)
            if not user.is_staff and not user.is_superuser and not user.habilitado:
                messages.error(request, "Tu cuenta está pendiente de verificación por el administrador. Por favor, espera la aprobación.")
                return redirect("login")
            
            login(request, user)
            messages.success(request, "Has iniciado sesión correctamente.", extra_tags='from_login')

            # Si es staff o superuser, redirigir a admin analytics
            if user.is_staff or user.is_superuser:
                return redirect("admin_analytics")

            # Redirección según el rol del usuario
            if hasattr(user, "role"):
                if user.role == "empresa":
                    return redirect("portal_empresas")
                elif user.role == "alumno":
                    return redirect("portal_practicantes")
                elif user.role == "capacitador":
                    return redirect("portal_empresas")
            
            # Si no tiene rol definido (por seguridad)
            messages.warning(request, "Tu cuenta no tiene rol asignado. Contacta al administrador.")
            return redirect("index")

        else:
            messages.error(request, "Correo o contraseña incorrectos.")
    else:
        form = EmailLoginForm()
    
    return render(request, "portal/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

def registro_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Mensaje diferenciado según el rol
            if user.role in ['empresa', 'capacitador']:
                messages.success(request, "Cuenta creada con éxito. Tu cuenta está pendiente de verificación por el administrador. Serás notificado cuando puedas acceder.")
            else:
                messages.success(request, "Cuenta creada con éxito. Ahora puedes iniciar sesión.")
            
            return redirect("login")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, "portal/registro.html", {"form": form})

#def portal_empresas(request):
    #return render(request, 'portal/portal_empresas.html')

def portal_practicantes(request):
    return render(request, 'portal/portal_practicantes.html')


@login_required(login_url='login')
def publicar_anuncio(request):
    # Validar que el usuario sea empresa
    if request.user.role != "empresa":
        messages.error(request, "No tienes permisos para publicar anuncios. Solo las empresas pueden hacerlo.")
        return redirect("login")  # lo manda al inicio o a otra página que quieras
    
    if request.method == "POST":
        form = AnuncioPracticaForm(request.POST)
        if form.is_valid():
            anuncio = form.save(commit=False)
            anuncio.empresa = request.user  # asigna el usuario empresa como dueño del anuncio
            anuncio.save()
            messages.success(request, "¡Anuncio publicado exitosamente!")
            return redirect("portal_empresas")
    else:
        form = AnuncioPracticaForm()

    return render(request, "portal/publicar_anuncio.html", {"form": form})

@login_required(login_url='login')
def portal_empresas(request):
    # Permitir acceso a 'empresa' y 'capacitador'
    if not hasattr(request.user, "role") or request.user.role not in ("empresa", "capacitador"):
        messages.error(request, "Acceso denegado. Solo las empresas y capacitadores pueden entrar aquí.")
        return redirect("index")

    # Formulario vacío
    form = AnuncioPracticaForm()

    # Listado de anuncios: si es empresa, los suyos; si es capacitador, los de su empresa asignada
    if request.user.role == "empresa":
        anuncios = AnuncioPractica.objects.filter(empresa=request.user)
    else:  # capacitador
        anuncios = AnuncioPractica.objects.filter(empresa=getattr(request.user, "company", None))

    return render(request, 'portal/portal_empresas.html', {
        "form": form,
        "anuncios": anuncios
    })

@login_required(login_url='login')
def gestionar_publicaciones(request):
    # Empresas y capacitadores pueden acceder (capacitador en modo solo lectura)
    if request.user.role not in ("empresa", "capacitador"):
        messages.error(request, "Acceso denegado. Solo las empresas y capacitadores pueden gestionar publicaciones.")
        return redirect("index")

    # Trae los anuncios de la empresa (si es capacitador, de su empresa asignada)
    if request.user.role == "empresa":
        anuncios = AnuncioPractica.objects.filter(empresa=request.user)
    else:
        anuncios = AnuncioPractica.objects.filter(empresa=getattr(request.user, "company", None))

    return render(request, "portal/gestionar_publicaciones.html", {"anuncios": anuncios})


@login_required(login_url='login')
def editar_publicacion(request, anuncio_id):
    # Permitir GET a capacitadores si el anuncio pertenece a su empresa; POST solo empresa
    if request.user.role == "capacitador":
        anuncio = get_object_or_404(AnuncioPractica, id=anuncio_id, empresa=getattr(request.user, "company", None))
        readonly = True
    else:
        anuncio = get_object_or_404(AnuncioPractica, id=anuncio_id, empresa=request.user)
        readonly = False

    if request.method == "POST":
        if request.user.role != "empresa":
            messages.error(request, "No tienes permisos para editar este anuncio.")
            return redirect("gestionar_publicaciones")
        form = AnuncioPracticaForm(request.POST, instance=anuncio)
        if form.is_valid():
            form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            messages.success(request, "Anuncio actualizado correctamente.")
            return redirect("gestionar_publicaciones")
    else:
        form = AnuncioPracticaForm(instance=anuncio)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html_form = render_to_string("portal/editar_publicacion.html", {"form": form, "anuncio": anuncio, "readonly": readonly}, request=request)
        return JsonResponse({"success": False, "html_form": html_form})

    return render(request, "portal/editar_publicacion.html", {"form": form, "anuncio": anuncio, "readonly": readonly})


@login_required(login_url='login')
def eliminar_publicacion(request, anuncio_id):
    anuncio = get_object_or_404(AnuncioPractica, id=anuncio_id, empresa=request.user)
    anuncio.delete()
    messages.success(request, "Publicación eliminada correctamente.")
    return redirect("gestionar_publicaciones")


@login_required(login_url='login')
def perfil_empresa(request):
    # Validar tipo
    if request.user.role != "empresa":
        messages.error(request, "Solo las empresas pueden acceder a este perfil.")
        return redirect("index")

    perfil, created = PerfilEmpresa.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = PerfilEmpresaForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("portal_empresas")
    else:
        form = PerfilEmpresaForm(instance=perfil)

    return render(request, "portal/perfil_empresa.html", {"form": form})

# views.py
import os, re, time
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from portal.forms import PerfilPostulanteForm
from portal.models import PerfilPostulante

#def _safe_filename(name: str) -> str:
    #base, ext = os.path.splitext(name)
    #base = re.sub(r'[^a-zA-Z0-9._-]+', '_', base)[:60]
    #return f"{base}{ext if ext.lower()=='.pdf' else '.pdf'}"

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.text import slugify
import os, uuid
from .models import PerfilPostulante
from .forms import PerfilPostulanteForm
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.text import slugify
import os, uuid
from .models import PerfilPostulante
from .forms import PerfilPostulanteForm
from django.conf import settings


@login_required(login_url='login')
def perfil_postulante(request):
    # ✅ Solo usuarios con rol "alumno" pueden acceder
    if request.user.role != "alumno":
        messages.error(request, "Solo los postulantes pueden acceder a este perfil.")
        return redirect("index")

    perfil, creado = PerfilPostulante.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = PerfilPostulanteForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            perfil = form.save(commit=False)

            file_obj = request.FILES.get("cv_file")
            if file_obj:
                # ✅ Nombre fijo por usuario (evita duplicados)
                key_path = f"{request.user.id}/cv.pdf"

                # ✅ Leer archivo binario
                file_bytes = file_obj.read()

                # ✅ Validación mínima: comprobar cabecera y cierre PDF
                if not file_bytes or not file_bytes.startswith(b"%PDF-"):
                    messages.error(request, "El archivo no parece ser un PDF válido (cabecera %PDF- no encontrada). Guarda como PDF e inténtalo de nuevo.")
                    return redirect("perfil_postulante")
                # buscar %%EOF en los últimos 1024 bytes (algunos visores lo requieren)
                tail = file_bytes[-1024:] if len(file_bytes) > 1024 else file_bytes
                if b"%%EOF" not in tail:
                    messages.error(request, "El PDF parece estar incompleto o corrupto (falta marcador %%EOF al final). Exporta de nuevo como PDF e inténtalo.")
                    return redirect("perfil_postulante")

                # ✅ Forzar content-type PDF (evitamos depender de la extensión)
                content_type = "application/pdf"

                # ✅ Subir y sobrescribir el archivo con opciones explícitas
                try:
                    result = settings.SUPABASE.storage.from_(settings.SUPABASE_BUCKET).upload(
                        path=key_path,
                        file=file_bytes,
                        file_options={
                            # incluir ambas variantes de claves por compatibilidad del SDK
                            "contentType": content_type,
                            "content_type": content_type,
                            "upsert": "true",
                            "cacheControl": "3600",
                            "cache_control": "3600",
                            "contentDisposition": "inline",
                            "content_disposition": "inline"
                        }
                    )
                    # La lib puede devolver dict con 'error' o 'message' en fallos
                    if isinstance(result, dict) and result.get("error"):
                        raise Exception(result.get("error"))
                except Exception as e:
                    messages.error(request, f"Error al subir el archivo a almacenamiento: {e}")
                    return redirect("perfil_postulante")

                # ✅ Actualizar URL pública en BD
                public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{key_path}"
                perfil.cv = public_url
                messages.success(request, "CV actualizado correctamente.")
            else:
                messages.info(request, "Perfil guardado sin cambiar el CV.")

            perfil.save()

            # Sincronizar correo con CustomUser si cambió
            try:
                nuevo_correo = (perfil.correo or '').strip()
                if nuevo_correo and nuevo_correo != (request.user.email or '').strip():
                    request.user.email = nuevo_correo
                    request.user.save(update_fields=["email"])
            except Exception:
                # Evitar que un fallo aquí bloquee el guardado del perfil
                pass
            return redirect("perfil_postulante")

    else:
        # Prefill: si el perfil no tiene correo aún, mostrar el del usuario como valor por defecto
        if not (perfil.correo and perfil.correo.strip()) and (request.user.email or '').strip():
            perfil.correo = request.user.email
        form = PerfilPostulanteForm(instance=perfil)

    cv_url = perfil.cv if perfil.cv and perfil.cv.startswith("http") else (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{perfil.cv}"
        if perfil.cv else None
    )

    return render(request, "portal/perfil_postulante.html", {"form": form, "cv_url": cv_url})



def _extraer_ruta_relativa(url_publica: str, bucket: str) -> str:
    """
    Recibe una URL pública como:
      https://<proj>.supabase.co/storage/v1/object/public/cvs/1/archivo.pdf
    y devuelve la ruta relativa:  cvs/1/archivo.pdf
    Si ya recibe una ruta relativa, la devuelve tal cual.
    """
    if not url_publica:
        return ""
    marker = f"/object/public/{bucket}/"
    if marker in url_publica:
        return url_publica.split(marker, 1)[1]
    return url_publica  # ya es relativa

@login_required(login_url='login')
def descargar_cv(request):
    perfil = get_object_or_404(PerfilPostulante, user=request.user)
    if not perfil.cv:
        messages.error(request, "Aún no has subido un CV.")
        return redirect("perfil_postulante")

    # 1) Tomamos la ruta relativa dentro del bucket
    rel_path = _extraer_ruta_relativa(perfil.cv, settings.SUPABASE_BUCKET)
    filename = os.path.basename(rel_path) or "cv.pdf"

    # ---- Variante A: generar enlace firmado que fuerza descarga ----
    try:
        # 60 segundos de validez (ajusta si quieres)
        signed = settings.SUPABASE.storage.from_(settings.SUPABASE_BUCKET).create_signed_url(
            rel_path,
            60,
            {"download": filename}   # fuerza Content-Disposition: attachment; filename=...
        )
        # La clave puede llamarse "signedURL", "signed_url" o venir dentro de "data"
        url = (
            signed.get("signedURL")
            or signed.get("signed_url")
            or (signed.get("data") or {}).get("signedURL")
            or (signed.get("data") or {}).get("signed_url")
        )
        if url:
            return redirect(url)
    except Exception as e:
        # Si falla, seguimos a Variante B (stream) como fallback
        pass

    # ---- Variante B (fallback): descargar bytes y servirlos desde Django ----
    try:
        file_bytes = settings.SUPABASE.storage.from_(settings.SUPABASE_BUCKET).download(rel_path)
        resp = HttpResponse(file_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        messages.error(request, f"No se pudo descargar el CV: {e}")
        return redirect("perfil_postulante")


def _stream_cv(cv_url: str, inline: bool = True):
    """Descarga bytes desde Supabase Storage y los sirve como PDF inline o attachment."""
    if not cv_url:
        return HttpResponse("Sin CV", status=404)
    rel_path = _extraer_ruta_relativa(cv_url, settings.SUPABASE_BUCKET)
    try:
        file_bytes = settings.SUPABASE.storage.from_(settings.SUPABASE_BUCKET).download(rel_path)
        resp = HttpResponse(file_bytes, content_type="application/pdf")
        filename = os.path.basename(rel_path) or "cv.pdf"
        disp = "inline" if inline else "attachment"
        resp["Content-Disposition"] = f"{disp}; filename=\"{filename}\""
        resp["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        return HttpResponse(f"No se pudo obtener el CV: {e}", status=500)


@login_required(login_url='login')
def ver_cv_propio(request):
    """Muestra el CV del postulante logueado en el visor del navegador (inline)."""
    if request.user.role != "alumno":
        return HttpResponse(status=403)
    perfil = get_object_or_404(PerfilPostulante, user=request.user)
    return _stream_cv(perfil.cv, inline=True)


@login_required(login_url='login')
def ver_cv_postulacion(request, postulacion_id: int):
    """Muestra el CV del postulante de una Postulación (inline) para empresa/capacitador autorizado."""
    post = get_object_or_404(Postulacion, id=postulacion_id)
    # Permisos
    if request.user.role == 'empresa':
        if getattr(post.anuncio, 'empresa_id', None) != request.user.id:
            return HttpResponse(status=403)
    elif request.user.role == 'capacitador':
        if getattr(request.user, 'company_id', None) != getattr(post.anuncio, 'empresa_id', None):
            return HttpResponse(status=403)
    else:
        return HttpResponse(status=403)
    download = request.GET.get("download") == "1"
    return _stream_cv(getattr(post.postulante, 'cv', None), inline=not download)






@login_required(login_url='login')
def listar_publicaciones(request):
    if request.user.role != "alumno":
        messages.error(request, "Solo los postulantes pueden acceder a las publicaciones.")
        return redirect("index")

    # Verifica que el perfil exista y esté mínimamente completo
    perfil = PerfilPostulante.objects.filter(user=request.user).first()
    if not perfil or not perfil.nombre or not perfil.apellido_pat or not perfil.correo:
        messages.warning(request, "completa tus datos en el apartado perfil para desbloquear esta funcion")
        return redirect("perfil_postulante")

    # Búsqueda por palabra clave (?q=...)
    q = (request.GET.get('q') or '').strip()
    publicaciones_qs = AnuncioPractica.objects.all()
    if q:
        publicaciones_qs = publicaciones_qs.filter(
            Q(titulo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(requisitos__icontains=q)
            | Q(ubicacion__icontains=q)
            | Q(modalidad__icontains=q)
            | Q(jornada__icontains=q)
            | Q(tipo_practica__icontains=q)
            | Q(empresa__company_name__icontains=q)
            | Q(empresa__username__icontains=q)
        )
    publicaciones_qs = publicaciones_qs.order_by('-creado_en')
    
    # Paginación: 10 publicaciones por página
    paginator = Paginator(publicaciones_qs, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        publicaciones_page = paginator.page(page_number)
    except PageNotAnInteger:
        publicaciones_page = paginator.page(1)
    except EmptyPage:
        publicaciones_page = paginator.page(paginator.num_pages)
    
    postulaciones = list(
        Postulacion.objects.filter(postulante=perfil).values_list('anuncio_id', flat=True)
    )

    # 🟦 Convertir publicaciones a JSON para el JS del template
    publicaciones_json = json.dumps([
        {
            "id": p.id,
            "titulo": p.titulo,
            "empresa": getattr(p.empresa, "company_name", p.empresa.username),
            "ubicacion": p.ubicacion,
            "modalidad": p.modalidad,
            "descripcion": p.descripcion,
            "requisitos": p.requisitos,
            "tipo_practica": p.tipo_practica,
            "duracion_meses": p.duracion_meses,
            "jornada": p.jornada,
            "cupos": p.cupos,
            "creado_en": p.creado_en.strftime("%d-%m-%Y"),
        }
        for p in publicaciones_page
    ], cls=DjangoJSONEncoder)

    return render(request, "portal/publicaciones.html", {
        "publicaciones": publicaciones_page,
        "publicaciones_json": publicaciones_json,
        "postulaciones": postulaciones,
        "q": q,
    })




@login_required(login_url='login')
def postular_practica(request, anuncio_id):
    if request.user.role != "alumno":
        messages.error(request, "Solo los postulantes pueden postular a prácticas.")
        return redirect("index")

    perfil = get_object_or_404(PerfilPostulante, user=request.user)
    anuncio = get_object_or_404(AnuncioPractica, id=anuncio_id)

    # Verificar si ya está postulado
    if Postulacion.objects.filter(postulante=perfil, anuncio=anuncio).exists():
        messages.warning(request, "Ya te has postulado a esta práctica.")
        return redirect("listar_publicaciones")

    # Crear la postulación
    Postulacion.objects.create(
        postulante=perfil,
        anuncio=anuncio,
        estado="pendiente"
    )

    messages.success(request, "Tu postulación ha sido enviada correctamente.")
    return redirect("listar_publicaciones")


@login_required(login_url='login')
def mis_postulaciones(request):
    if request.user.role != "alumno":
        messages.error(request, "Solo los postulantes pueden acceder a sus postulaciones.")
        return redirect("index")

    perfil = PerfilPostulante.objects.get(user=request.user)
    postulaciones = Postulacion.objects.filter(postulante=perfil).select_related("anuncio", "anuncio__empresa")

    return render(request, "portal/mis_postulaciones.html", {
        "postulaciones": postulaciones
    })


@login_required(login_url='login')
def mis_capacitaciones(request):
    """Vista para alumnos: ver sus capacitaciones agendadas y evaluaciones."""
    if request.user.role != "alumno":
        messages.error(request, "Solo los postulantes pueden ver esta sección.")
        return redirect("index")

    perfil = get_object_or_404(PerfilPostulante, user=request.user)
    fichas = (
        FichaCapacitacion.objects
        .filter(postulante=perfil)
        .prefetch_related("evaluaciones")
        .order_by("-fecha_inicio")
    )

    return render(request, "portal/mis_capacitaciones.html", {"fichas": fichas})


@login_required(login_url='login')
def ver_postulaciones_empresa(request):
    if request.user.role != "empresa":
        messages.error(request, "Solo las empresas pueden acceder a este módulo.")
        return redirect("index")

    # Buscar todas las postulaciones asociadas a los anuncios de esta empresa
    postulaciones = Postulacion.objects.filter(
        anuncio__empresa=request.user
    ).select_related("postulante", "anuncio")

    return render(request, "portal/postulaciones_empresa.html", {
        "postulaciones": postulaciones
    })


# ===============================
#   CAPACITACIONES (CAPACITADOR)
# ===============================
@login_required(login_url='login')
def capacitaciones(request):
    """Vista principal del capacitador: ver postulaciones aceptadas de su empresa y gestionar capacitaciones/evaluaciones."""
    if request.user.role not in ("capacitador", "empresa"):
        messages.error(request, "Acceso denegado.")
        return redirect("index")

    # Alcance: si es capacitador, ver aceptados de su empresa; si es empresa, de sí misma
    empresa_id = request.user.id if request.user.role == "empresa" else getattr(request.user, "company_id", None)
    if not empresa_id:
        messages.warning(request, "No tienes empresa asociada.")
        aceptados = Postulacion.objects.none()
    else:
        aceptados = (
            Postulacion.objects
            .filter(anuncio__empresa_id=empresa_id, estado="aceptado")
            .select_related("postulante", "anuncio")
            .order_by("-fecha_postulacion")
        )

    # Formularios vacíos para crear (se completan por POST)
    ficha_form = FichaCapacitacionForm()

    # Traer fichas existentes para estas postulaciones y enviarlas como JSON agrupado por postulacion
    from collections import defaultdict
    by_postulacion = defaultdict(list)
    postulacion_ids = list(aceptados.values_list("id", flat=True))
    if postulacion_ids:
        fichas = (
            FichaCapacitacion.objects
            .filter(postulacion_id__in=postulacion_ids, empresa_id=empresa_id)
            .order_by("-fecha_inicio")
        )
        for f in fichas:
            by_postulacion[f.postulacion_id].append({
                "id": f.id,
                "nombre": f.nombre_capacitacion,
                "tipo": f.tipo_capacitacion,
                "inicio": f.fecha_inicio.strftime("%d-%m-%Y"),
                "inicio_iso": f.fecha_inicio.strftime("%Y-%m-%d"),
                "termino": f.fecha_termino.strftime("%d-%m-%Y"),
                "termino_iso": f.fecha_termino.strftime("%Y-%m-%d"),
                "estado": f.estado,
            })
    fichas_por_postulante_json = json.dumps(by_postulacion, cls=DjangoJSONEncoder)

    return render(request, "portal/capacitaciones.html", {
        "postulaciones": aceptados,
        "ficha_form": ficha_form,
        "fichas_por_postulante_json": fichas_por_postulante_json,
    })


@login_required(login_url='login')
def agendar_capacitacion(request, postulacion_id):
    if request.user.role not in ("capacitador", "empresa"):
        return HttpResponse(status=403)
    post = get_object_or_404(Postulacion, id=postulacion_id, estado="aceptado")
    empresa_id = request.user.id if request.user.role == "empresa" else getattr(request.user, "company_id", None)
    if getattr(post.anuncio, "empresa_id", None) != empresa_id:
        return HttpResponse(status=403)

    if request.method == "POST":
        form = FichaCapacitacionForm(request.POST)
        if form.is_valid():
            ficha = form.save(commit=False)
            ficha.postulante = post.postulante
            # asignar empresa que agenda (empresa o la empresa del capacitador)
            ficha.empresa_id = empresa_id
            # asociar a la postulacion específica para no compartir entre anuncios
            ficha.postulacion = post
            ficha.save()
            # Responder según sea AJAX o navegación normal
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "ficha": {
                        "id": ficha.id,
                        "nombre": ficha.nombre_capacitacion,
                        "tipo": ficha.tipo_capacitacion,
                        "inicio": ficha.fecha_inicio.strftime("%d-%m-%Y"),
                        "inicio_iso": ficha.fecha_inicio.strftime("%Y-%m-%d"),
                        "termino": ficha.fecha_termino.strftime("%d-%m-%Y"),
                        "termino_iso": ficha.fecha_termino.strftime("%Y-%m-%d"),
                        "estado": ficha.estado,
                        "postulante_id": ficha.postulante_id,
                    }
                })
            messages.success(request, "Capacitación agendada.")
        else:
            # Construir mensajes de error legibles
            errores = []
            for campo, lista in form.errors.items():
                for err in lista:
                    errores.append(f"{campo}: {err}")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "errors": errores or ["Datos inválidos."]}, status=400)
            if errores:
                messages.error(request, "No se pudo agendar: " + "; ".join(errores))
            else:
                messages.error(request, "Revisa los datos del formulario de capacitación.")
    return redirect("capacitaciones")


@login_required(login_url='login')
def evaluar_capacitacion(request, ficha_id):
    if request.user.role not in ("capacitador", "empresa"):
        return HttpResponse(status=403)
    empresa_id = request.user.id if request.user.role == "empresa" else getattr(request.user, "company_id", None)
    ficha = get_object_or_404(FichaCapacitacion, id=ficha_id)
    # Debe pertenecer a la misma empresa que agenda
    if ficha.empresa_id != empresa_id:
        return HttpResponse(status=403)

    if request.method == "POST":
        form = RegistroEvaluacionForm(request.POST)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.capacitacion = ficha
            ev.save()
            # Actualizar estado de la capacitación según la nota
            try:
                nota = ev.nota_final if ev.nota_final is not None else None
                if nota is not None:
                    # Si nota >= 4.0 -> completada; si nota < 4.0 -> cancelada
                    if Decimal(nota) >= Decimal("4.0"):
                        nuevo_estado = "completada"
                    else:
                        nuevo_estado = "cancelada"
                    if ficha.estado != nuevo_estado:
                        ficha.estado = nuevo_estado
                        ficha.save(update_fields=["estado"])
            except Exception:
                # No bloquear por errores de casteo u otros; ya registramos la evaluación
                pass

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "ficha": {
                        "id": ficha.id,
                        "estado": ficha.estado,
                    }
                })
            messages.success(request, "Evaluación registrada.")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                errores = []
                for campo, lista in form.errors.items():
                    for err in lista:
                        errores.append(f"{campo}: {err}")
                return JsonResponse({"success": False, "errors": errores or ["Datos inválidos."]}, status=400)
            messages.error(request, "Revisa los datos de la evaluación.")
    return redirect("capacitaciones")


@login_required(login_url='login')
def eliminar_capacitacion(request, ficha_id):
    """Permite al capacitador/empresa eliminar una capacitación"""
    if request.user.role not in ("capacitador", "empresa"):
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("index")
    
    empresa_id = request.user.id if request.user.role == "empresa" else getattr(request.user, "company_id", None)
    
    try:
        ficha = FichaCapacitacion.objects.get(id=ficha_id, empresa_id=empresa_id)
        nombre = ficha.nombre_capacitacion
        ficha.delete()
        messages.success(request, f"Capacitación '{nombre}' eliminada exitosamente.")
    except FichaCapacitacion.DoesNotExist:
        messages.error(request, "Capacitación no encontrada o no tienes permisos.")
    
    return redirect("capacitaciones")


@login_required(login_url='login')
def cambiar_estado_postulacion(request, postulacion_id, nuevo_estado):
    if request.user.role != "empresa":
        messages.error(request, "Solo las empresas pueden cambiar el estado de postulaciones.")
        return redirect("index")

    postulacion = get_object_or_404(Postulacion, id=postulacion_id, anuncio__empresa=request.user)

    if nuevo_estado not in ["pendiente", "aceptado", "rechazado"]:
        messages.error(request, "Estado no válido.")
        return redirect("ver_postulaciones_empresa")

    postulacion.estado = nuevo_estado
    postulacion.save()
    messages.success(request, f"El estado de la postulación fue cambiado a '{nuevo_estado}'.")
    return redirect("ver_postulaciones_empresa")


# ===============================
#   ADMIN ANALYTICS (staff)
# ===============================
@login_required(login_url='login')
def admin_analytics(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido al personal administrativo.")
        return redirect('index')

    # Filtros
    start = request.GET.get('start')
    end = request.GET.get('end')
    institucion = request.GET.get('institucion') or ''
    tipo = request.GET.get('tipo_practica') or ''
    estado = request.GET.get('estado') or ''

    # Base QS
    post_qs = Postulacion.objects.select_related('postulante', 'anuncio', 'anuncio__empresa')
    if start:
        post_qs = post_qs.filter(fecha_postulacion__gte=start)
    if end:
        post_qs = post_qs.filter(fecha_postulacion__lte=end)
    if institucion:
        post_qs = post_qs.filter(postulante__institucion=institucion)
    if tipo:
        post_qs = post_qs.filter(anuncio__tipo_practica=tipo)
    if estado:
        post_qs = post_qs.filter(estado=estado)

    # KPIs
    total_postulaciones = post_qs.count()
    total_rechazadas = post_qs.filter(estado='rechazado').count()
    total_aceptadas = post_qs.filter(estado='aceptado').count()

    # Cuentas creadas por institución (sobre usuarios alumno). Usamos date_joined para rango
    perfil_qs = PerfilPostulante.objects.select_related('user')
    if start:
        perfil_qs = perfil_qs.filter(user__date_joined__date__gte=start)
    if end:
        perfil_qs = perfil_qs.filter(user__date_joined__date__lte=end)
    cuentas_por_inst = (
        perfil_qs
        .values('institucion')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    # Postulaciones por institución
    posts_por_inst = (
        post_qs
        .values('postulante__institucion')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    # Rechazadas por institución
    rechazos_por_inst = (
        post_qs.filter(estado='rechazado')
        .values('postulante__institucion')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    # Tipos de práctica más postulados
    por_tipo = (
        post_qs
        .values('anuncio__tipo_practica')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    # Logs recientes (si existe el modelo)
    try:
        from .models import PostulacionLog
        logs = PostulacionLog.objects.select_related('postulacion', 'postulante', 'anuncio')
        if start:
            logs = logs.filter(creado_en__date__gte=start)
        if end:
            logs = logs.filter(creado_en__date__lte=end)
        if institucion:
            logs = logs.filter(institucion=institucion)
        logs = logs[:100]
    except Exception:
        logs = []

    # Opciones para selects
    instituciones = list(
        PerfilPostulante.objects.exclude(institucion__isnull=True).exclude(institucion='').values_list('institucion', flat=True).distinct()
    )
    tipos = list(AnuncioPractica.objects.values_list('tipo_practica', flat=True).distinct())

    # NUEVO: Obtener empresas con sus capacitadores
    from .models import CustomUser
    empresas = CustomUser.objects.filter(role='empresa').prefetch_related('capacitadores').order_by('-date_joined')
    
    # Crear estructura de datos: empresa con sus capacitadores
    empresas_con_capacitadores = []
    for empresa in empresas:
        capacitadores = empresa.capacitadores.all()
        empresas_con_capacitadores.append({
            'empresa': empresa,
            'capacitadores': capacitadores
        })

    return render(request, 'portal/admin_analytics.html', {
        'filters': {
            'start': start or '', 'end': end or '', 'institucion': institucion, 'tipo': tipo, 'estado': estado
        },
        'instituciones': instituciones,
        'tipos': tipos,
        'kpis': {
            'total_postulaciones': total_postulaciones,
            'total_aceptadas': total_aceptadas,
            'total_rechazadas': total_rechazadas,
        },
        'cuentas_por_inst': list(cuentas_por_inst),
        'posts_por_inst': list(posts_por_inst),
        'rechazos_por_inst': list(rechazos_por_inst),
        'por_tipo': list(por_tipo),
        'logs': logs,
        'empresas_con_capacitadores': empresas_con_capacitadores,
    })


@login_required
def cambiar_habilitacion_cuenta(request, user_id):
    """Permite al admin habilitar/deshabilitar cuentas de empresas y capacitadores"""
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect('index')
    
    from .models import CustomUser
    try:
        usuario = CustomUser.objects.get(id=user_id)
        
        # Solo permitir cambiar estado de empresas y capacitadores
        if usuario.role not in ['empresa', 'capacitador']:
            messages.error(request, "Solo se puede cambiar el estado de empresas y capacitadores.")
            return redirect('admin_analytics')
        
        # Cambiar el estado
        usuario.habilitado = not usuario.habilitado
        usuario.save()
        
        estado_texto = "habilitada" if usuario.habilitado else "deshabilitada"
        messages.success(request, f"Cuenta de {usuario.email} {estado_texto} exitosamente.")
        
    except CustomUser.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
    
    return redirect('admin_analytics')


@login_required
def eliminar_cuenta(request, user_id):
    """Permite al admin eliminar cuentas de empresas y capacitadores"""
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect('index')
    
    from .models import CustomUser
    try:
        usuario = CustomUser.objects.get(id=user_id)
        
        # Evitar que el admin se elimine a sí mismo
        if usuario.id == request.user.id:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
            return redirect('admin_analytics')
        
        # Evitar eliminar otros superusuarios
        if usuario.is_superuser:
            messages.error(request, "No se pueden eliminar cuentas de superusuarios.")
            return redirect('admin_analytics')
        
        email = usuario.email
        usuario.delete()
        messages.success(request, f"Cuenta de {email} eliminada exitosamente.")
        
    except CustomUser.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
    
    return redirect('admin_analytics')