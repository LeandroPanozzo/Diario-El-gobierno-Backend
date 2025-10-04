from django.contrib import admin
from django.urls import reverse
from django.contrib.auth.models import User, Group, Permission
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType
from .models import Donacion, Rol, Trabajador, Usuario, Noticia, EstadoPublicacion, Imagen, Publicidad, Comentario, UserProfile
# --- Función helper para verificar permisos de admin ---
def es_admin_completo(user):
    """Verifica si el usuario tiene permisos de administración completos"""
    return user.is_superuser or user.is_staff

# --- Signal para asignar permisos automáticamente a usuarios staff ---
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def asignar_permisos_staff(sender, instance, **kwargs):
    """Asigna todos los permisos a usuarios con is_staff=True"""
    if instance.is_staff and not instance.is_superuser:
        # Obtener todos los permisos disponibles
        all_permissions = Permission.objects.all()
        # Asignar todos los permisos al usuario
        instance.user_permissions.set(all_permissions)
        print(f"Permisos asignados a {instance.username}")

# --- Clase base para todos los ModelAdmin con permisos de staff ---
class StaffPermissionMixin:
    """Mixin que otorga todos los permisos a usuarios staff"""
    
    def has_module_permission(self, request):
        return es_admin_completo(request.user)
    
    def has_view_permission(self, request, obj=None):
        return es_admin_completo(request.user)
    
    def has_add_permission(self, request):
        return es_admin_completo(request.user)

    def has_change_permission(self, request, obj=None):
        return es_admin_completo(request.user)

    def has_delete_permission(self, request, obj=None):
        return es_admin_completo(request.user)

# --- Restricciones de permisos para User y Group ---
class UserAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Asignar permisos si es staff pero no superuser
        if obj.is_staff and not obj.is_superuser:
            all_permissions = Permission.objects.all()
            obj.user_permissions.set(all_permissions)

class GroupAdmin(StaffPermissionMixin, admin.ModelAdmin):
    pass

# Desregistrar los modelos por defecto y registrarlos con las restricciones
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

# --- Administración de los modelos personalizados ---

@admin.register(Rol)
class RolAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('nombre_rol', 'puede_publicar', 'puede_editar', 'puede_eliminar', 'puede_asignar_roles', 'puede_dejar_comentarios')
    search_fields = ('nombre_rol',)

from django import forms
from .models import Trabajador

from django import forms
from .models import Trabajador, UserProfile
from django.core.files.uploadedfile import InMemoryUploadedFile

class TrabajadorForm(forms.ModelForm):
    foto_perfil_temp = forms.ImageField(
        required=False, 
        label="Foto de Perfil",
        help_text="La imagen será subida automáticamente a Imgur"
    )
    
    class Meta:
        model = Trabajador
        fields = ['nombre', 'apellido', 'rol', 'user', 'foto_perfil_temp']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and instance.foto_perfil:
            self.fields['foto_perfil_temp'].help_text += f"<br>Imagen actual: <a href='{instance.foto_perfil}' target='_blank'>{instance.foto_perfil}</a>"

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if not instance.user_profile:
            instance.user_profile = UserProfile.objects.create(
                nombre=instance.nombre,
                apellido=instance.apellido,
                es_trabajador=True
            )
        else:
            if not instance.user_profile.es_trabajador:
                instance.user_profile.es_trabajador = True
                instance.user_profile.save()

        foto_temp = self.cleaned_data.get('foto_perfil_temp')
        if foto_temp:
            instance.foto_perfil_temp = foto_temp

        if commit:
            instance.save()
            
        return instance

@admin.register(Trabajador)
class TrabajadorAdmin(StaffPermissionMixin, admin.ModelAdmin):
    form = TrabajadorForm
    
    list_display = (
        'correo', 'nombre', 'apellido', 'rol', 'user_link', 'mostrar_foto_perfil'
    )
    search_fields = ('correo', 'nombre', 'apellido', 'user__username', 'user__email')
    list_filter = ('rol',)
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'apellido', 'user', 'rol')
        }),
        ('Foto de Perfil', {
            'fields': ('foto_perfil_temp',),
            'description': 'La imagen se subirá automáticamente a Imgur al guardar'
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user}</a>')
    
    user_link.short_description = 'Usuario'

    def mostrar_foto_perfil(self, obj):
        if obj.foto_perfil:
            return format_html('<img src="{}" style="max-height: 100px;">', obj.foto_perfil)
        elif obj.foto_perfil_local:
            return format_html('<img src="{}" style="max-height: 100px;">', obj.foto_perfil_local)
        return "No tiene foto de perfil"
    
    mostrar_foto_perfil.short_description = 'Foto de Perfil'

    def save_model(self, request, obj, form, change):
        obj.correo = obj.user.email
        obj.contraseña = obj.user.password
        super().save_model(request, obj, form, change)

@admin.register(Usuario)
class UsuarioAdmin(StaffPermissionMixin, admin.ModelAdmin):
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
        if es_admin_completo(request.user):
            return True
        if hasattr(request.user, 'trabajador') and request.user.trabajador.rol.puede_dejar_comentarios:
            return True
        return False

@admin.register(Noticia)
class NoticiaAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = (
        'visitas_totales',
        'nombre_noticia', 
        'autor_link', 
        'editores_en_jefe_links',
        'fecha_publicacion', 
        'display_categorias',
        'solo_para_subscriptores', 
        'estado', 
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
    
    def visitas_totales(self, obj):
        return obj.contador_visitas_total
    visitas_totales.short_description = 'Visitas Total'
    visitas_totales.admin_order_field = 'contador_visitas_total'
    
    search_fields = ('nombre_noticia', 'Palabras_clave')
    date_hierarchy = 'fecha_publicacion'
    ordering = ['-contador_visitas_total']
    
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
                'editores_en_jefe',
                'fecha_publicacion', 
                'categorias',
                'estado'
            )
        }),
        ('Estadísticas de Visitas', {
            'fields': (
                'contador_visitas_total',
            ),
            'classes': ('collapse',)
        }),
        ('Imágenes', {
            'fields': (
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
    
    readonly_fields = (
        'url', 
        'contador_visitas_total',
    )
    
    inlines = [ComentarioInline]

    def editores_en_jefe_links(self, obj):
        links = []
        for editor in obj.editores_en_jefe.all():
            url = reverse('admin:auth_user_change', args=[editor.user.id])
            links.append(format_html(f'<a href="{url}">{editor}</a>'))
        
        if links:
            return format_html(', '.join(links))
        return "No asignados"
    
    editores_en_jefe_links.short_description = 'Editores en Jefe'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def icono_comentarios(self, obj):
        if obj.tiene_comentarios:
            return format_html('<img src="/static/admin/img/icon-yes.svg" alt="Tiene comentarios">')
        return format_html('<img src="/static/admin/img/icon-no.svg" alt="No tiene comentarios">')
    
    icono_comentarios.short_description = 'Comentarios'
    
    def autor_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.autor.user.id])
        return format_html(f'<a href="{url}">{obj.autor}</a>')

    autor_link.short_description = 'Autor'

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        
        if not es_admin_completo(request.user):
            readonly.extend(['contador_visitas_total'])
            
        return readonly

    actions = ['reset_total_counter']

    def reset_total_counter(self, request, queryset):
        if es_admin_completo(request.user):
            count = queryset.update(contador_visitas_total=0)
            self.message_user(
                request,
                f'Se resetearon los contadores totales de {count} noticias.'
            )
        else:
            self.message_user(
                request,
                'Solo los administradores pueden resetear contadores totales.',
                level='ERROR'
            )
    reset_total_counter.short_description = "Resetear contador total (Solo administradores)"

@admin.register(Comentario)
class ComentarioAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('noticia', 'autor', 'fecha_creacion', 'tiene_respuesta')
    list_filter = ('noticia', 'autor', 'fecha_creacion')
    search_fields = ('noticia__nombre_noticia', 'autor__username', 'contenido')
    readonly_fields = ('noticia', 'autor', 'contenido', 'fecha_creacion')

    def tiene_respuesta(self, obj):
        return bool(obj.respuesta)
    
    tiene_respuesta.boolean = True
    tiene_respuesta.short_description = 'Respondido'

@admin.register(EstadoPublicacion)
class EstadoPublicacionAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('nombre_estado',)
    search_fields = ('nombre_estado',)

@admin.register(Imagen)
class ImagenAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('nombre_imagen', 'noticia')
    search_fields = ('nombre_imagen',)
    list_filter = ('noticia',)

@admin.register(Publicidad)
class PublicidadAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('tipo_anuncio', 'fecha_inicio', 'fecha_fin', 'noticia', 'impresiones', 'clics')
    search_fields = ('tipo_anuncio', 'noticia__nombre_noticia')
    list_filter = ('fecha_inicio', 'fecha_fin')

# --- Comando de management para asignar permisos a usuarios staff existentes ---
# Crear archivo: management/commands/asignar_permisos_staff.py

"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission

class Command(BaseCommand):
    help = 'Asigna todos los permisos a usuarios con is_staff=True'

    def handle(self, *args, **options):
        staff_users = User.objects.filter(is_staff=True, is_superuser=False)
        all_permissions = Permission.objects.all()
        
        for user in staff_users:
            user.user_permissions.set(all_permissions)
            self.stdout.write(
                self.style.SUCCESS(f'Permisos asignados a {user.username}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Se procesaron {staff_users.count()} usuarios staff')
        )
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

# IMPORTANTE: Asegúrate de que este import funcione
try:
    from .models import Donacion
except ImportError:
    from diarioback.models import Donacion

# Si tienes StaffPermissionMixin en otro archivo, impórtalo
# from .mixins import StaffPermissionMixin
# Si NO lo tienes, NO uses el mixin (comentado abajo)


# Filtro personalizado por semana - DEBE IR ANTES de DonacionAdmin
class SemanaFilter(admin.SimpleListFilter):
    title = 'Semana'
    parameter_name = 'semana'

    def lookups(self, request, model_admin):
        """Genera las últimas 12 semanas como opciones"""
        opciones = []
        hoy = timezone.now()
        
        for i in range(12):
            fecha = hoy - timedelta(weeks=i)
            semana = fecha.isocalendar()[1]
            año = fecha.year
            
            # Calcular el inicio de la semana
            inicio_semana = fecha - timedelta(days=fecha.weekday())
            fin_semana = inicio_semana + timedelta(days=6)
            
            # Formato: "Semana 45 (Nov 6 - Nov 12)"
            label = f"Semana {semana} ({inicio_semana.strftime('%b %d')} - {fin_semana.strftime('%b %d, %Y')})"
            value = f"{año}-{semana}"
            opciones.append((value, label))
        
        return opciones

    def queryset(self, request, queryset):
        """Filtra el queryset por la semana seleccionada"""
        if self.value():
            try:
                año, semana = self.value().split('-')
                año = int(año)
                semana = int(semana)
                
                # Calcular el primer día de la semana
                primer_dia = timezone.datetime.strptime(f'{año}-W{semana}-1', "%Y-W%W-%w")
                primer_dia = timezone.make_aware(primer_dia)
                
                # Calcular el último día de la semana
                ultimo_dia = primer_dia + timedelta(days=7)
                
                return queryset.filter(
                    fecha_donacion__gte=primer_dia,
                    fecha_donacion__lt=ultimo_dia
                )
            except Exception as e:
                # En producción, es mejor no silenciar errores completamente
                print(f"Error en SemanaFilter: {e}")
                return queryset
        
        return queryset


@admin.register(Donacion)
class DonacionAdmin(admin.ModelAdmin):
    # Si necesitas StaffPermissionMixin, descoméntalo arriba y usa:
    # class DonacionAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = (
        'nombre', 
        'correo', 
        'monto', 
        'fecha_donacion_formateada',
        'semana_donacion',
        'mes_donacion',
        'ver_comprobante'
    )
    
    list_filter = (
        ('fecha_donacion', admin.DateFieldListFilter),
        SemanaFilter,  # Filtro personalizado por semana
    )
    
    search_fields = ('nombre', 'correo')
    
    readonly_fields = ('fecha_donacion', 'comprobante', 'comprobante_local', 'ver_comprobante_completo')
    
    fieldsets = (
        ('Información del Donante', {
            'fields': ('nombre', 'correo')
        }),
        ('Detalles de la Donación', {
            'fields': ('monto', 'mensaje', 'fecha_donacion')
        }),
        ('Comprobante', {
            'fields': ('ver_comprobante_completo', 'comprobante', 'comprobante_local')
        })
    )
    
    date_hierarchy = 'fecha_donacion'
    ordering = ['-fecha_donacion']
    
    def fecha_donacion_formateada(self, obj):
        """Formatea la fecha de donación"""
        if obj.fecha_donacion:
            return obj.fecha_donacion.strftime("%d/%m/%Y %H:%M")
        return "-"
    fecha_donacion_formateada.short_description = 'Fecha y Hora'
    fecha_donacion_formateada.admin_order_field = 'fecha_donacion'
    
    def semana_donacion(self, obj):
        """Muestra el número de semana del año"""
        if obj.fecha_donacion:
            semana = obj.fecha_donacion.isocalendar()[1]
            año = obj.fecha_donacion.year
            return f"Semana {semana} - {año}"
        return "-"
    semana_donacion.short_description = 'Semana'
    
    def mes_donacion(self, obj):
        """Muestra el mes de la donación"""
        if not obj.fecha_donacion:
            return "-"
            
        meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        mes_nombre = meses[obj.fecha_donacion.month]
        return f"{mes_nombre} {obj.fecha_donacion.year}"
    mes_donacion.short_description = 'Mes'
    
    def ver_comprobante(self, obj):
        """Muestra miniatura del comprobante"""
        # Priorizar comprobante (URL de Imgur)
        if obj.comprobante:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height: 50px;"/></a>',
                obj.comprobante, obj.comprobante
            )
        # Si no hay URL, intentar con comprobante_local
        elif obj.comprobante_local:
            try:
                return format_html(
                    '<a href="{}" target="_blank"><img src="{}" style="max-height: 50px;"/></a>',
                    obj.comprobante_local.url, obj.comprobante_local.url
                )
            except Exception:
                return "Error al cargar imagen local"
        return "Sin comprobante"
    ver_comprobante.short_description = 'Miniatura'
    
    def ver_comprobante_completo(self, obj):
        """Muestra comprobante completo"""
        # Priorizar comprobante (URL de Imgur)
        if obj.comprobante:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 500px; max-height: 500px;"/></a>',
                obj.comprobante, obj.comprobante
            )
        # Si no hay URL, intentar con comprobante_local
        elif obj.comprobante_local:
            try:
                return format_html(
                    '<a href="{}" target="_blank"><img src="{}" style="max-width: 500px; max-height: 500px;"/></a>',
                    obj.comprobante_local.url, obj.comprobante_local.url
                )
            except Exception:
                return "Error al cargar imagen local"
        return "Sin comprobante"
    ver_comprobante_completo.short_description = 'Comprobante'
    
    def has_add_permission(self, request):
        """Deshabilita agregar donaciones desde el admin"""
        return False