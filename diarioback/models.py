from django.db import models
from django.contrib.auth.models import User
import requests
import os
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from datetime import timedelta

from django.core.exceptions import ValidationError

def validate_positive(value):
    if value <= 0:
        raise ValidationError('El valor debe ser positivo.')


class Rol(models.Model):
    nombre_rol = models.CharField(max_length=50)
    puede_publicar = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)
    puede_asignar_roles = models.BooleanField(default=False)
    puede_dejar_comentarios = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_rol


import os

import os


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=True, blank=True)  # Cambio aquí
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    foto_perfil = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    descripcion_usuario = models.TextField(blank=True, null=True)
    es_trabajador = models.BooleanField(default=False)

class Trabajador(models.Model):
    DEFAULT_FOTO_PERFIL_URL = 'https://example.com/default-profile.png'
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    id = models.AutoField(primary_key=True)
    correo = models.EmailField(unique=False)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    foto_perfil = models.URLField(blank=True, null=True)
    foto_perfil_local = models.ImageField(upload_to='perfil/', blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.ForeignKey('Rol', on_delete=models.CASCADE, related_name='trabajadores', null=False)

    @property
    def descripcion_usuario(self):
        if self.user_profile:
            return self.user_profile.descripcion_usuario
        return None

    @descripcion_usuario.setter
    def descripcion_usuario(self, value):
        if self.user_profile:
            self.user_profile.descripcion_usuario = value
            self.user_profile.save()

    def save(self, *args, **kwargs):
        # Obtener la instancia anterior si existe
        old_instance = None
        if self.pk:  # Solo si ya existe una instancia guardada previamente
            try:
                old_instance = Trabajador.objects.get(pk=self.pk)
            except Trabajador.DoesNotExist:
                pass

        # Crear un nuevo UserProfile si no existe
        if not self.user_profile:
            self.user_profile = UserProfile.objects.create(
                nombre=self.nombre,
                apellido=self.apellido
            )

        # Manejar la imagen de perfil (local o URL)
        self._handle_image('foto_perfil', 'foto_perfil_local')

        # Si no hay imagen local ni URL, asignar la imagen por defecto
        if not self.foto_perfil and not self.foto_perfil_local:
            self.foto_perfil = self.DEFAULT_FOTO_PERFIL_URL

        # Llamar a la versión original del método `save`
        super().save(*args, **kwargs)

        # Eliminar la imagen anterior de Imgur si ha sido reemplazada
        if old_instance:
            self._delete_old_image(old_instance, 'foto_perfil')

    def _handle_image(self, image_field, image_local_field):
        image_local = getattr(self, image_local_field)
        image_url = getattr(self, image_field)

        # Si es una imagen local, subirla a Imgur
        if image_local and os.path.exists(image_local.path):
            uploaded_image_url = upload_to_imgur(image_local.path)
            setattr(self, image_field, uploaded_image_url)
        elif image_url:
            # Si hay una URL proporcionada, la usamos
            setattr(self, image_field, image_url)
        else:
            # Si no hay imagen ni URL, usar el valor por defecto
            setattr(self, image_field, self.DEFAULT_FOTO_PERFIL_URL)

    def _delete_old_image(self, old_instance, field_name):
        old_image_url = getattr(old_instance, field_name)
        new_image_url = getattr(self, field_name)
        if old_image_url and old_image_url != new_image_url:
            delete_from_imgur(old_image_url)

    def get_foto_perfil(self):
        return self.foto_perfil_local.url if self.foto_perfil_local else self.foto_perfil or self.DEFAULT_FOTO_PERFIL_URL

    def __str__(self):
        return f'{self.nombre} {self.apellido}'



import requests
import time
import os
from django.core.files.uploadedfile import InMemoryUploadedFile

# Constantes de Imgur
IMGUR_CLIENT_ID = '8e1f77de3869736'  # Tu Client ID actual
IMGUR_UPLOAD_URL = 'https://api.imgur.com/3/image'

def upload_to_imgur(image):
    """
    Sube una imagen a Imgur y devuelve la URL
    
    Args:
        image: Puede ser un objeto InMemoryUploadedFile, una ruta a un archivo,
               o un archivo abierto en modo binario
    
    Returns:
        str: URL de la imagen en Imgur, o None si falló la subida
    """
    headers = {
        'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'
    }
    
    try:
        # Prepara los datos según el tipo de entrada
        if isinstance(image, InMemoryUploadedFile):
            # Si es un archivo subido en memoria (desde un formulario)
            image_data = image.read()
            files = {'image': image_data}
        elif isinstance(image, str) and os.path.isfile(image):
            # Si es una ruta a un archivo
            with open(image, 'rb') as image_file:
                image_data = image_file.read()
                files = {'image': image_data}
        elif hasattr(image, 'path') and os.path.isfile(image.path):
            # Si es un campo ImageField de Django
            with open(image.path, 'rb') as image_file:
                image_data = image_file.read()
                files = {'image': image_data}
        else:
            # Si es un archivo ya abierto o cualquier otro objeto que pueda ser leído
            image_data = image.read() if hasattr(image, 'read') else image
            files = {'image': image_data}
        
        # Intentar subir la imagen a Imgur
        response = requests.post(
            IMGUR_UPLOAD_URL,
            headers=headers,
            files=files
        )
        
        # Manejar límites de peticiones
        if response.status_code == 429:  # Too Many Requests
            print("Error 429: Demasiadas solicitudes, esperando antes de reintentar...")
            time.sleep(60)  # Esperar 60 segundos antes de reintentar
            return upload_to_imgur(image)  # Reintentar la carga
        
        # Verificar respuesta
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                return response_data['data']['link']
            else:
                print(f"Error al subir imagen a Imgur: {response_data.get('data', {}).get('error')}")
        else:
            print(f"Error HTTP {response.status_code} al subir imagen a Imgur")
        
    except Exception as e:
        print(f"Excepción al subir imagen a Imgur: {str(e)}")
    
    return None

# Implementación mejorada para eliminar imágenes de Imgur
def delete_from_imgur(image_url):
    """
    Elimina una imagen de Imgur usando su URL o hash
    
    Args:
        image_url: URL de la imagen o hash de Imgur
    
    Returns:
        bool: True si se eliminó correctamente, False en caso contrario
    """
    # Extrae el hash de la imagen desde la URL
    # Las URLs de Imgur suelen tener el formato: https://i.imgur.com/abcdefg.jpg
    try:
        if not image_url:
            return False
            
        # Extrae el hash de la URL
        image_hash = None
        if '/' in image_url:
            # Obtener la última parte de la URL (el nombre del archivo)
            filename = image_url.split('/')[-1]
            # Quitar la extensión si existe
            image_hash = filename.split('.')[0] if '.' in filename else filename
        else:
            # Si solo es un hash
            image_hash = image_url
            
        if not image_hash:
            return False
            
        # URL para eliminar la imagen
        delete_url = f'https://api.imgur.com/3/image/{image_hash}'
        
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'
        }
        
        response = requests.delete(delete_url, headers=headers)
        
        if response.status_code == 200:
            return True
        else:
            print(f"Error al eliminar imagen de Imgur: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error al eliminar imagen de Imgur: {str(e)}")
        return False

class NoticiaVisita(models.Model):
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE, related_name='visitas')
    fecha = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['noticia']),
        ]

from django.utils.text import slugify

class Noticia(models.Model):
    CATEGORIAS = [
        ('Portada', 'portada'),
        ('Politica', (
            ('legislativos', 'Legislativos'),
            ('policiales', 'Policiales'),
            ('elecciones', 'Elecciones'),
            ('gobierno', 'Gobierno'),
            ('provincias', 'Provincias'),
            ('capital', 'Capital'),
            ('nacion', 'Nacion'),
            
        )),
        ('Cultura', (
            ('cine', 'Cine'),
            ('literatura', 'Literatura'),
            ('salud', 'Salud'),
            ('tecnologia', 'Tecnologia'),
            ('eventos', 'Eventos'),
            ('educacion', 'Educacion'),
            ('efemerides', 'Efemerides'),
            ('deporte', 'Deporte'),
        )),
        ('Economia', (
            ('finanzas', 'Finanzas'),
            ('comercio_internacional', 'Comercio internacional'),
            ('politica_economica', 'Politica economica'),
            ('pobreza_e_inflacion', 'Pobreza e inflacion'),
            ('dolar', 'Dolar')
        )),
        ('Mundo', (
            ('estados_unidos', 'Estados Unidos'),
            ('asia', 'Asia'),
            ('medio_oriente', 'Medio Oriente'),
            ('internacional', 'Internacional'),
            ('latinoamerica', 'Latinoamerica'),
        )),
        ('Tipos de notas', (
            ('de_analisis', 'De analisis'),
            ('de_opinion', 'De opinion'),
            ('informativas', 'Informativas'),
            ('entrevistas', 'Entrevistas'),
            
        )),

    ]

    # Fixed flattening of categories
    FLAT_CATEGORIAS = []
    for category in CATEGORIAS:
        if isinstance(category[1], tuple):
            FLAT_CATEGORIAS.extend(subcat[0] for subcat in category[1])
        else:
            FLAT_CATEGORIAS.append(category[0])
    # Helper method to validate categories
    def validate_categorias(value):
        """Standalone validator function for categorias field"""
        if not value:
            return ''
        categories = value.split(',')
        categories = [cat.strip() for cat in categories if cat.strip()]
        invalid_cats = [cat for cat in categories if cat not in Noticia.FLAT_CATEGORIAS]
        if invalid_cats:
            raise ValidationError(f'Invalid categories: {", ".join(invalid_cats)}')
        return ','.join(categories)

    # Add the categorias field with the fixed validator
    categorias = models.TextField(
        validators=[validate_categorias],
        blank=True,
        null=True
    )

    # Other fields...
    autor = models.ForeignKey('Trabajador', on_delete=models.CASCADE, related_name='noticias', null=False)
    editores_en_jefe = models.ManyToManyField(
        'Trabajador', 
        related_name='noticias_supervisadas',
        blank=True,
        verbose_name="Editores en jefe"
    )
    nombre_noticia = models.CharField(max_length=500)
    fecha_publicacion = models.DateField()
    url = models.URLField(max_length=200, blank=True, null=True)
    # Modificar la definición del slug para permitir slugs más largos (300 caracteres)
    slug = models.SlugField(max_length=300, unique=True, blank=True, editable=False)
    # CONTADORES DE VISITAS - NUEVOS CAMPOS
    contador_visitas = models.PositiveIntegerField(default=0, help_text="Contador semanal que se reinicia")
    contador_visitas_total = models.PositiveIntegerField(default=0, help_text="Contador permanente total")
    ultima_actualizacion_contador = models.DateTimeField(default=timezone.now)
    ultima_actualizacion_contador = models.DateTimeField(default=timezone.now)
    Palabras_clave = models.CharField(max_length=200)
    imagen_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_1 = models.URLField(blank=True, null=True)
    imagen_1_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_2 = models.URLField(blank=True, null=True)
    imagen_2_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_3 = models.URLField(blank=True, null=True)
    imagen_3_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_4 = models.URLField(blank=True, null=True)
    imagen_4_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_5 = models.URLField(blank=True, null=True)
    imagen_5_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_6 = models.URLField(blank=True, null=True)
    imagen_6_local = models.ImageField(upload_to='images/', blank=True, null=True)
    estado = models.ForeignKey('EstadoPublicacion', on_delete=models.SET_NULL, null=True)
    solo_para_subscriptores = models.BooleanField(default=False)
    contenido = models.TextField(default='default content')
    subtitulo = models.TextField(default='default content')
    tiene_comentarios = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Validate categorias before saving
        if self.categorias:
            self.categorias = Noticia.validate_categorias(self.categorias)
        
        # Verificar si el objeto existe y si el título ha cambiado
        if self.pk:
            try:
                old_instance = Noticia.objects.get(pk=self.pk)
                if old_instance.nombre_noticia != self.nombre_noticia:
                    # El título ha cambiado, actualizar el slug
                    # Ya no truncamos el título a 100 caracteres
                    self.slug = slugify(self.nombre_noticia)
                    original_slug = self.slug
                    count = 1
                    while Noticia.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                        self.slug = f"{original_slug}-{count}"
                        count += 1
            except Noticia.DoesNotExist:
                pass
        else:
            # Es un objeto nuevo, generar el slug
            # Ya no truncamos el título a 100 caracteres
            self.slug = slugify(self.nombre_noticia)
            original_slug = self.slug
            count = 1
            while Noticia.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1

        # Guarda primero para obtener un ID si es objeto nuevo
        super().save(*args, **kwargs)
        
        # Procesar imágenes y subir a Imgur
        images_updated = self._process_images(old_instance if 'old_instance' in locals() else None)
        
        # Solo guardar nuevamente si se actualizaron las imágenes
        if images_updated:
            super().save()
    
    def _process_images(self, old_instance=None):
        """Procesa todas las imágenes, sube a Imgur y actualiza URLs"""
        images_updated = False
        
        # Procesar imágenes adicionales (1-6)
        for i in range(1, 7):
            local_field_name = f'imagen_{i}_local'
            url_field_name = f'imagen_{i}'
            
            local_field = getattr(self, local_field_name)
            if local_field and hasattr(local_field, 'file'):
                # Subir la imagen a Imgur
                imgur_url = upload_to_imgur(local_field)
                if imgur_url:
                    # Si la subida fue exitosa, actualizar la URL
                    setattr(self, url_field_name, imgur_url)
                    # Limpiar el campo local después de subir
                    setattr(self, local_field_name, None)
                    images_updated = True
                    
                    # Para depuración
                    print(f"Imagen {i} subida a Imgur: {imgur_url}")
        
        # Eliminar imágenes antiguas de Imgur si fueron reemplazadas
        if old_instance:
            self._delete_old_images(old_instance)
        
        return images_updated
    
    def _delete_old_images(self, old_instance):
        """Elimina las imágenes antiguas de Imgur si han sido reemplazadas"""
        fields_to_check =  [f'imagen_{i}' for i in range(1, 7)]
        
        for field_name in fields_to_check:
            old_url = getattr(old_instance, field_name)
            new_url = getattr(self, field_name)
            
            # Si la URL ha cambiado y la antigua URL existe, eliminarla de Imgur
            if old_url and old_url != new_url and old_url.startswith('https://i.imgur.com/'):
                delete_from_imgur(old_url)
    def get_categorias(self):
        return self.categorias.split(',') if self.categorias else []

    def __str__(self):
        return f'{self.nombre_noticia} - {self.categorias}'

    def __str__(self):
        return f'{self.nombre_noticia} - {self.estado}'

    def get_absolute_url(self):
        return f'/noticias/{self.pk}-{self.slug}/'

    def get_image_urls(self):
        """Retorna una lista de todas las URLs de imágenes disponibles."""
        image_urls = []
       
        for i in range(1, 7):
            image_field = getattr(self, f'imagen_{i}')
            if image_field:
                image_urls.append(image_field)
        return image_urls

    def get_conteo_reacciones(self):
        return {
            'interesa': self.reacciones.filter(tipo_reaccion='interesa').count(),
            'divierte': self.reacciones.filter(tipo_reaccion='divierte').count(),
            'entristece': self.reacciones.filter(tipo_reaccion='entristece').count(),
            'enoja': self.reacciones.filter(tipo_reaccion='enoja').count(),
        }

    def incrementar_visitas(self, ip_address=None):
        from datetime import timedelta
        from django.utils import timezone
        
        # Verifica si ha pasado una semana desde la última actualización
        if timezone.now() - self.ultima_actualizacion_contador > timedelta(days=7):
            self.contador_visitas = 0
            self.ultima_actualizacion_contador = timezone.now()
            self.save()

        # NUEVO: Evitar incrementos duplicados por IP en un período corto
        if ip_address:
            # Verificar si esta IP ya visitó en los últimos 5 minutos
            hace_5_minutos = timezone.now() - timedelta(minutes=5)
            visita_reciente = NoticiaVisita.objects.filter(
                noticia=self,
                ip_address=ip_address,
                fecha__gte=hace_5_minutos
            ).exists()
            
            if visita_reciente:
                # No incrementar si ya visitó recientemente
                return False

        # Registra la visita
        NoticiaVisita.objects.create(
            noticia=self,
            ip_address=ip_address
        )
        
        # Incrementa ambos contadores
        self.contador_visitas += 1
        self.contador_visitas_total += 1
        self.save(update_fields=['contador_visitas', 'contador_visitas_total'])
        
        return True

    # Agrega una propiedad para obtener las visitas de la última semana
    @property
    def visitas_ultima_semana(self):
        hace_una_semana = timezone.now() - timedelta(days=7)
        return self.visitas.filter(fecha__gte=hace_una_semana).count()

    class Meta:
        ordering = ['-contador_visitas']  # Ordena por defecto por número de visitas

    @staticmethod
    def validate_categorias(value):
        """Standalone validator function for categorias field"""
        if not value:
            return []
        categories = value.split(',')
        invalid_cats = [cat for cat in categories if cat not in Noticia.FLAT_CATEGORIAS]
        if invalid_cats:
            raise ValidationError(f'Invalid categories: {", ".join(invalid_cats)}')
        return value
    
    @staticmethod
    def validate_categorias(value):
        """Temporary validator function that allows 'argentina' during transition"""
        if not value:
            return []
        categories = value.split(',')
        
        # Lista temporal de categorías permitidas durante la transición
        temp_allowed = ['argentina']  # Categorías obsoletas pero que aún existen en DB
        
        # Verificar solo categorías que no estén en la lista temporal
        invalid_cats = [cat for cat in categories if cat not in Noticia.FLAT_CATEGORIAS and cat not in temp_allowed]
        
        if invalid_cats:
            raise ValidationError(f'Invalid categories: {", ".join(invalid_cats)}')
        return value

    
class Comentario(models.Model):
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    respuesta = models.TextField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.autor:
            try:
                trabajador = Trabajador.objects.get(user=self.autor)
                if not trabajador.rol.puede_dejar_comentarios:
                    raise ValueError("No tienes habilitada la opción de comentar.")
            except Trabajador.DoesNotExist:
                raise ValueError("El autor no tiene un trabajador asociado.")
        super().save(*args, **kwargs)


class EstadoPublicacion(models.Model):
    BORRADOR = 'borrador'
    EN_PAPELERA = 'en_papelera'
    PUBLICADO = 'publicado'
    LISTO_PARA_EDITAR = 'listo_para_editar'

    ESTADO_CHOICES = [
        (BORRADOR, 'Borrador'),
        (EN_PAPELERA, 'En Papelera'),
        (PUBLICADO, 'Publicado'),
        (LISTO_PARA_EDITAR, 'Listo para editar'),
    ]

    nombre_estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=BORRADOR,
    )

    def __str__(self):
        return self.get_nombre_estado_display()



class Imagen(models.Model):
    nombre_imagen = models.CharField(max_length=100)
    imagen = models.URLField(null=True, blank=True)  # URL de la imagen en Imgur
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='imagenes')

    def save(self, *args, **kwargs):
        # Verifica si imagen es una URL o una ruta local
        if not self.imagen.startswith(('http://', 'https://')):
            # Si es una ruta local, sube la imagen a Imgur
            self.imagen = upload_to_imgur(self.imagen)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_imagen


class Usuario(models.Model):
    correo = models.EmailField(unique=True)
    nombre_usuario = models.CharField(max_length=100)
    contraseña = models.CharField(max_length=128)
    foto_perfil = models.URLField()  # URL de la foto de perfil en Imgur
    esta_subscrito = models.BooleanField(default=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre_usuario

class Publicidad(models.Model):
    tipo_anuncio = models.CharField(max_length=50)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    url_destino = models.URLField()
    impresiones = models.IntegerField()
    clics = models.IntegerField()
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='publicidades')

    def __str__(self):
        return f'{self.tipo_anuncio} - {self.fecha_inicio} a {self.fecha_fin}'

# models.py
from django.db import models
from django.contrib.auth.models import User

class ReaccionNoticia(models.Model):
    TIPOS_REACCION = [
        ('interesa', 'Me interesa'),
        ('divierte', 'Me divierte'),
        ('entristece', 'Me entristece'),
        ('enoja', 'Me enoja'),
    ]
    
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE, related_name='reacciones')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo_reaccion = models.CharField(max_length=20, choices=TIPOS_REACCION)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['noticia', 'usuario']  # Un usuario solo puede tener una reacción por noticia

# models.py
from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Generar token simple si no existe
        if not self.token:
            self.token = self.generate_token()
        
        # El token expira después de 24 horas
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
            
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at
    
    @staticmethod
    def generate_token():
        # Generar token numérico de 6 dígitos
        digits = string.digits
        token = ''.join(random.choice(digits) for _ in range(6))
        
        # Verificar que no exista ya
        while PasswordResetToken.objects.filter(token=token).exists():
            token = ''.join(random.choice(digits) for _ in range(6))
            
        return token

