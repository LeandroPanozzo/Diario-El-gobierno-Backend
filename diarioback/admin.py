from django.contrib import admin
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from .models import Rol, Trabajador, Usuario, Noticia, EstadoPublicacion, Imagen, Publicidad, Comentario

# --- Restricciones de permisos para User y Group ---

class UserAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

class GroupAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# Desregistrar los modelos por defecto y registrarlos con las restricciones
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

# --- Administración de los modelos personalizados ---

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre_rol', 'puede_publicar', 'puede_editar', 'puede_eliminar', 'puede_asignar_roles', 'puede_dejar_comentarios')
    search_fields = ('nombre_rol',)

from django import forms
from .models import Trabajador

class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = ['nombre', 'apellido', 'rol', 'user', 'foto_perfil', 'foto_perfil_local']

    def save(self, commit=True):
        trabajador = super().save(commit=False)
        trabajador.correo = trabajador.user.email
        trabajador.contraseña = trabajador.user.password
        if commit:
            trabajador.save()
        return trabajador


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    form = TrabajadorForm  # Usar el formulario personalizado

    list_display = (
        'correo', 'nombre', 'apellido', 'rol', 'user_link', 'mostrar_foto_perfil'
    )
    search_fields = ('correo', 'nombre', 'apellido', 'user__username', 'user__email')
    list_filter = ('rol',)

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user}</a>')

    user_link.short_description = 'Usuario'

    # Método para mostrar la foto de perfil
    def mostrar_foto_perfil(self, obj):
        if obj.foto_perfil:
            return format_html('<img src="{}" style="max-height: 100px;">', obj.foto_perfil)
        elif obj.foto_perfil_local:
            return format_html('<img src="{}" style="max-height: 100px;">', obj.foto_perfil_local)
        return "No tiene foto de perfil"

    mostrar_foto_perfil.short_description = 'Foto de Perfil'

    # Sobrescribir el método save_model para asignar correo y contraseña automáticamente
    def save_model(self, request, obj, form, change):
        obj.correo = obj.user.email
        obj.contraseña = obj.user.password
        super().save_model(request, obj, form, change)

    # Sobrescribir los permisos de cambio
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and request.user == obj.user:
            return True
        return False



@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('correo', 'nombre_usuario', 'esta_subscrito')
    search_fields = ('correo', 'nombre_usuario')
    list_filter = ('esta_subscrito',)

class ComentarioInline(admin.StackedInline):
    model = Comentario
    extra = 1
    readonly_fields = ('autor', 'fecha_creacion')
    fields = ('contenido', 'fecha_creacion', 'respuesta', 'fecha_respuesta')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.autor = request.user
        obj.save()

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'trabajador') and request.user.trabajador.rol.puede_dejar_comentarios:
            return True
        return False

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_noticia', 
        'autor_link', 
        'editor_en_jefe_link',  
        'fecha_publicacion', 
        'display_categorias',  # Change this line
        'solo_para_subscriptores', 
        'estado', 
        'contador_visitas',
        'visitas_ultimas_24h',
        'icono_comentarios'
    )
    
    list_filter = (
        'autor', 
        'fecha_publicacion', 
        'solo_para_subscriptores', 
        'estado'
    )

    def display_categorias(self, obj):
        return obj.categorias
    display_categorias.short_description = 'Categorías'
    
    search_fields = ('nombre_noticia', 'Palabras_clave')
    date_hierarchy = 'fecha_publicacion'
    
    fieldsets = (
        ('Información Principal', {
            'fields': (
                'nombre_noticia', 
                'subtitulo', 
                'contenido', 
                'Palabras_clave'
            )
        }),
        ('Metadatos', {
            'fields': (
                'autor', 
                'editor_en_jefe', 
                'fecha_publicacion', 
                'categoria', 
                'estado'
            )
        }),
        ('Imágenes', {
            'fields': (
                'imagen_cabecera', 
                'imagen_1', 
                'imagen_2', 
                'imagen_3', 
                'imagen_4', 
                'imagen_5', 
                'imagen_6'
            )
        }),
        ('Opciones Avanzadas', {
            'fields': (
                'solo_para_subscriptores', 
                'tiene_comentarios', 
                'url'
            )
        })
    )
    
    readonly_fields = ('url', 'contador_visitas', 'visitas_ultimas_24h')
    
    inlines = [ComentarioInline]

    def visitas_ultimas_24h(self, obj):
        return obj.visitas_ultimas_24h
    visitas_ultimas_24h.short_description = 'Visitas (24h)'

    def editor_en_jefe_link(self, obj):
        if obj.editor_en_jefe:
            url = reverse('admin:auth_user_change', args=[obj.editor_en_jefe.user.id])
            return format_html(f'<a href="{url}">{obj.editor_en_jefe}</a>')
        return "No asignado"
    
    editor_en_jefe_link.short_description = 'Editor en Jefe'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def icono_comentarios(self, obj):
        if obj.tiene_comentarios:
            return format_html('<img src="/static/admin/img/icon-yes.svg" alt="Tiene comentarios">')
        return format_html('<img src="/static/admin/img/icon-no.svg" alt="No tiene comentarios">')
    
    icono_comentarios.short_description = 'Comentarios'

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and request.user == obj.autor.user:
            return True
        return False
    
    def autor_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.autor.user.id])
        return format_html(f'<a href="{url}">{obj.autor}</a>')

    autor_link.short_description = 'Autor'


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('noticia', 'autor', 'fecha_creacion', 'tiene_respuesta')
    list_filter = ('noticia', 'autor', 'fecha_creacion')
    search_fields = ('noticia__nombre_noticia', 'autor__username', 'contenido')
    readonly_fields = ('noticia', 'autor', 'contenido', 'fecha_creacion')

    def tiene_respuesta(self, obj):
        return bool(obj.respuesta)
    
    tiene_respuesta.boolean = True
    tiene_respuesta.short_description = 'Respondido'

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        try:
            trabajador = Trabajador.objects.get(user=request.user)
            return trabajador.rol.puede_dejar_comentarios
        except Trabajador.DoesNotExist:
            return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and request.user == obj.noticia.autor.user:
            return True
        return False

@admin.register(EstadoPublicacion)
class EstadoPublicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre_estado',)
    search_fields = ('nombre_estado',)

@admin.register(Imagen)
class ImagenAdmin(admin.ModelAdmin):
    list_display = ('nombre_imagen', 'noticia')
    search_fields = ('nombre_imagen',)
    list_filter = ('noticia',)

@admin.register(Publicidad)
class PublicidadAdmin(admin.ModelAdmin):
    list_display = ('tipo_anuncio', 'fecha_inicio', 'fecha_fin', 'noticia', 'impresiones', 'clics')
    search_fields = ('tipo_anuncio', 'noticia__nombre_noticia')
    list_filter = ('fecha_inicio', 'fecha_fin')
