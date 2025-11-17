from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Rol, Trabajador, UserProfile, Usuario, Noticia, Comentario, EstadoPublicacion, Imagen, Publicidad
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from .serializers import UserProfileSerializer, UserRegistrationSerializer, LoginSerializer
from django.core.files.storage import default_storage
import uuid
from .imgur_utils import upload_to_imgur, delete_from_imgur
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
import os
from django.conf import settings
from rest_framework import generics
from rest_framework.exceptions import NotFound
from django.shortcuts import redirect
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import User
from .serializers import UserSerializer
from django.utils import timezone  # Añade esta importación
from datetime import timedelta     # Añade esta importación
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .serializers import (
    RolSerializer, TrabajadorSerializer, UsuarioSerializer, NoticiaSerializer,
    ComentarioSerializer, EstadoPublicacionSerializer, ImagenSerializer, PublicidadSerializer
)

BASE_QUERYSET = User.objects.all()

class UserrViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Permite el acceso sin autenticación

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer

class TrabajadorViewSet(viewsets.ModelViewSet):
    queryset = Trabajador.objects.all()
    serializer_class = TrabajadorSerializer
    

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class EstadoPublicacionViewSet(viewsets.ModelViewSet):
    queryset = EstadoPublicacion.objects.all()
    serializer_class = EstadoPublicacionSerializer

class ImagenViewSet(viewsets.ModelViewSet):
    queryset = Imagen.objects.all()
    serializer_class = ImagenSerializer

class ComentarioViewSet(viewsets.ModelViewSet):
    queryset = Comentario.objects.all()
    serializer_class = ComentarioSerializer

    def get_queryset(self):
        noticia_id = self.kwargs['noticia_id']
        return self.queryset.filter(noticia_id=noticia_id)

    def destroy(self, request, noticia_id, comment_id):
        try:
            comentario = self.get_queryset().get(id=comment_id)
            comentario.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Comentario.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error deleting comment: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CommentDeleteView(APIView):
    def delete(self, request, noticia_id, comment_id):
        try:
            comment = Comentario.objects.get(id=comment_id, noticia_id=noticia_id)
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Comentario.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ComentarioListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ComentarioSerializer

    def get_queryset(self):
        noticia_id = self.kwargs['noticia_id']
        return Comentario.objects.filter(noticia_id=noticia_id)

    def perform_create(self, serializer):
        noticia_id = self.kwargs['noticia_id']
        serializer.save(noticia_id=noticia_id)

class PublicidadViewSet(viewsets.ModelViewSet):
    queryset = Publicidad.objects.all()
    serializer_class = PublicidadSerializer

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from .models import Noticia, Trabajador
from .serializers import NoticiaSerializer
from django.shortcuts import get_object_or_404

def upload_to_imgur(image):
    # Implementación del servicio de subida a Imgur
    pass
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count, Prefetch
from django.shortcuts import get_object_or_404
from .models import Noticia, Trabajador, EstadoPublicacion, NoticiaVisita
from .serializers import NoticiaSerializer
from .imgur_utils import upload_to_imgur

class NoticiasPagination(PageNumberPagination):
    """Paginación optimizada para noticias"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class NoticiaViewSet(viewsets.ModelViewSet):
    serializer_class = NoticiaSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_publicacion', 'contador_visitas']
    ordering = ['-fecha_publicacion']
    lookup_field = 'pk'
    lookup_value_regex = r'[0-9]+(?:-[a-zA-Z0-9-_]+)?'
    pagination_class = NoticiasPagination
    
    def get_queryset(self):
        """
        ✅ OPTIMIZACIÓN CRÍTICA: Usa select_related y prefetch_related
        para evitar queries N+1
        """
        queryset = Noticia.objects.select_related(
            'autor',      # ForeignKey - Una query JOIN
            'estado'      # ForeignKey - Una query JOIN
        ).prefetch_related(
            'editores_en_jefe'  # ManyToMany - Una query separada optimizada
        )
        
        # Filtrar por autor si se especifica
        autor = self.request.query_params.get('autor')
        if autor:
            queryset = queryset.filter(autor=autor)
        
        # Filtrar por estado (publication status)
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtrar por categoría (una o múltiples categorías)
        categoria = self.request.query_params.get('categoria')
        if categoria:
            categorias = categoria.split(',')
            if len(categorias) > 1:
                category_query = Q()
                for cat in categorias:
                    category_query |= Q(categorias__contains=cat.strip())
                queryset = queryset.filter(category_query)
            else:
                queryset = queryset.filter(categorias__contains=categoria)
        
        # Filtrar por rango de fechas
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha_publicacion__gte=fecha_desde)
            
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha_publicacion__lte=fecha_hasta)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """
        ✅ OPTIMIZACIÓN: Usa paginación real del backend
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Si se solicita sin paginación (limit específico)
        limit = self.request.query_params.get('limit')
        if limit and limit.isdigit():
            queryset = queryset[:int(limit)]
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        # Con paginación estándar
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Optimizado con prefetch y contador de visitas"""
        instance = self.get_object()
        
        # Obtiene la IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        # Incrementa el contador de visitas
        instance.incrementar_visitas(ip_address=ip)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """
        Búsqueda avanzada de noticias con múltiples criterios
        Uso: /api/noticias/buscar/?q=texto&type=all&limit=20
        """
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'all')
        
        if not query:
            return Response(
                {"error": "Se requiere el parámetro 'q' para la búsqueda"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get parameters
        limit = request.query_params.get('limit', 20)
        try:
            limit = int(limit)
        except ValueError:
            limit = 20
            
        estado = request.query_params.get('estado', 3)
        categoria = request.query_params.get('categoria')
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')
        
        # Base queryset optimizado
        queryset = self.get_queryset().filter(estado=estado)
        
        # Build search query based on search type
        search_query = Q()
        
        if search_type == 'all' or search_type == 'title':
            search_query |= Q(nombre_noticia__icontains=query)
        
        if search_type == 'all' or search_type == 'content':
            search_query |= Q(contenido__icontains=query)
            search_query |= Q(subtitulo__icontains=query)
        
        if search_type == 'all' or search_type == 'keywords':
            search_query |= Q(Palabras_clave__icontains=query)
        
        if search_type == 'all' or search_type == 'categories':
            search_query |= Q(categorias__icontains=query)
        
        # Apply search filter
        queryset = queryset.filter(search_query)
        
        # Additional filters
        if categoria:
            queryset = queryset.filter(categorias__contains=categoria)
        
        if fecha_desde:
            queryset = queryset.filter(fecha_publicacion__gte=fecha_desde)
            
        if fecha_hasta:
            queryset = queryset.filter(fecha_publicacion__lte=fecha_hasta)
        
        # Order by publication date (most recent first)
        queryset = queryset.order_by('-fecha_publicacion')
        
        # Get total count before limiting
        total_count = queryset.count()
        
        # Apply limit
        queryset = queryset[:limit]
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'query': query,
            'search_type': search_type,
            'results_count': total_count,
            'returned_count': len(serializer.data),
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def mas_vistas(self, request):
        """
        Noticias más vistas de la última semana
        Uso: /api/noticias/mas_vistas/?limit=10
        """
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
            
        hace_una_semana = timezone.now() - timedelta(days=7)
        
        noticias_mas_vistas = self.get_queryset().filter(
            estado=3,
            ultima_actualizacion_contador__gte=hace_una_semana
        ).order_by('-contador_visitas')[:limit]
        
        serializer = self.get_serializer(noticias_mas_vistas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def mas_leidas(self, request):
        """
        Noticias más leídas de todos los tiempos
        Uso: /api/noticias/mas_leidas/?limit=10
        """
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        
        noticias_mas_leidas = self.get_queryset().filter(
            estado=3
        ).order_by('-contador_visitas_total')[:limit]
        
        serializer = self.get_serializer(noticias_mas_leidas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def populares_semana(self, request):
        """Alias para mas_vistas"""
        return self.mas_vistas(request)

    @action(detail=False, methods=['get'])
    def populares_historico(self, request):
        """Alias para mas_leidas"""
        return self.mas_leidas(request)

    @action(detail=False, methods=['get'])
    def estadisticas_visitas(self, request):
        """
        Estadísticas generales de visitas
        Uso: /api/noticias/estadisticas_visitas/
        """
        from django.db.models import Sum, Avg, Max, Count
        
        stats = self.get_queryset().filter(estado=3).aggregate(
            total_visitas_semanales=Sum('contador_visitas'),
            total_visitas_historicas=Sum('contador_visitas_total'),
            promedio_visitas_semanales=Avg('contador_visitas'),
            promedio_visitas_historicas=Avg('contador_visitas_total'),
            max_visitas_semanales=Max('contador_visitas'),
            max_visitas_historicas=Max('contador_visitas_total'),
            total_noticias=Count('id')
        )
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def recientes(self, request):
        """
        Noticias más recientes
        Uso: /api/noticias/recientes/?limit=5
        """
        limit = request.query_params.get('limit', 5)
        try:
            limit = int(limit)
        except ValueError:
            limit = 5
            
        noticias_recientes = self.get_queryset().filter(
            estado=3
        ).order_by('-fecha_publicacion')[:limit]
        
        serializer = self.get_serializer(noticias_recientes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def destacadas(self, request):
        """
        Noticias destacadas para el carousel
        Uso: /api/noticias/destacadas/?limit=12
        """
        limit = request.query_params.get('limit', 12)
        try:
            limit = int(limit)
        except ValueError:
            limit = 12
            
        noticias_destacadas = self.get_queryset().filter(
            estado=3
        ).order_by('-fecha_publicacion')[:limit]
        
        serializer = self.get_serializer(noticias_destacadas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_trabajador(self, request):
        """
        ✅ NUEVO ENDPOINT OPTIMIZADO para cargar noticias de un trabajador específico
        Filtra por autor O editor en jefe
        Uso: /api/noticias/por_trabajador/?trabajador_id=6&page=1&page_size=20
        """
        trabajador_id = request.query_params.get('trabajador_id')
        
        if not trabajador_id:
            return Response(
                {"error": "Se requiere trabajador_id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            trabajador_id = int(trabajador_id)
        except ValueError:
            return Response(
                {"error": "trabajador_id debe ser un número"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filtrar por autor O editor
        queryset = self.get_queryset().filter(
            Q(autor_id=trabajador_id) | Q(editores_en_jefe__id=trabajador_id)
        ).distinct()
        
        # Usar paginación
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def politica(self, request):
        """Noticias de la sección Política"""
        politica_categories = [
            'nacion', 'legislativos', 'policiales', 
            'elecciones', 'gobierno', 'provincias', 'capital'
        ]
        return self._get_section_news(request, politica_categories)

    @action(detail=False, methods=['get'])
    def cultura(self, request):
        """Noticias de la sección Cultura"""
        cultura_categories = [
            'cine', 'literatura', 'salud', 'tecnologia', 
            'eventos', 'educacion', 'efemerides', 'deporte'
        ]
        return self._get_section_news(request, cultura_categories)

    @action(detail=False, methods=['get'])
    def economia(self, request):
        """Noticias de la sección Economía"""
        economia_categories = [
            'finanzas', 'comercio_internacional', 'politica_economica', 
            'dolar', 'pobreza_e_inflacion'
        ]
        return self._get_section_news(request, economia_categories)

    @action(detail=False, methods=['get'])
    def mundo(self, request):
        """Noticias de la sección Mundo"""
        mundo_categories = [
            'estados_unidos', 'asia', 'medio_oriente', 
            'internacional', 'latinoamerica'
        ]
        return self._get_section_news(request, mundo_categories)

    @action(detail=False, methods=['get'])
    def tipos_notas(self, request):
        """Noticias por tipo de nota"""
        tipos_categories = [
            'de_analisis', 'de_opinion', 'informativas', 'entrevistas'
        ]
        return self._get_section_news(request, tipos_categories)

    def _get_section_news(self, request, categories):
        """
        Helper method optimizado para obtener noticias por sección
        """
        limit = request.query_params.get('limit', 7)
        try:
            limit = int(limit)
        except ValueError:
            limit = 7
            
        category_query = Q()
        for cat in categories:
            category_query |= Q(categorias__contains=cat)
            
        section_news = self.get_queryset().filter(
            category_query,
            estado=3
        ).order_by('-fecha_publicacion')[:limit]
        
        serializer = self.get_serializer(section_news, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """
        🚀 OPTIMIZADO: Noticias filtradas por categorías con carga eficiente
        Uso: /api/noticias/por-categoria/?categoria=cine,literatura&limit=60
        """
        categoria = request.query_params.get('categoria')
        if not categoria:
            return Response(
                {"error": "Se requiere el parámetro 'categoria'"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        categorias = [cat.strip() for cat in categoria.split(',') if cat.strip()]
        estado = request.query_params.get('estado', 3)
        limit = request.query_params.get('limit', 60)
        
        try:
            limit = int(limit)
        except ValueError:
            limit = 60
        
        # 🚀 OPTIMIZACIÓN 1: Usar select_related para cargar autor en una sola query
        queryset = Noticia.objects.select_related(
            'autor',
            'estado'
        ).prefetch_related(
            'editores_en_jefe'
        ).filter(estado=estado)
        
        # 🚀 OPTIMIZACIÓN 2: Filtrar con Q objects de forma eficiente
        if len(categorias) > 1:
            from django.db.models import Q
            category_query = Q()
            for cat in categorias:
                category_query |= Q(categorias__icontains=cat)
            queryset = queryset.filter(category_query)
        else:
            queryset = queryset.filter(categorias__icontains=categoria)
        
        # 🚀 OPTIMIZACIÓN 3: Ordenar y limitar en la base de datos
        queryset = queryset.order_by('-fecha_publicacion')[:limit]
        
        # 🚀 OPTIMIZACIÓN 4: Serializar con context optimizado
        serializer = self.get_serializer(queryset, many=True, context={
            'request': request,
            'include_autor': True  # Incluir datos del autor directamente
        })
        
        return Response(serializer.data)

    @method_decorator(cache_page(60 * 5))  # Cache de 5 minutos
    @action(detail=False, methods=['get'])
    def por_categoria_cached(self, request):
        """
        Versión con cache para secciones populares
        Uso: /api/noticias/por-categoria-cached/?categoria=politica
        """
        return self.por_categoria(request)

    @action(detail=True, methods=['post'])
    def agregar_editor(self, request, pk=None):
        """Agregar un editor a una noticia"""
        noticia = self.get_object()
        editor_id = request.data.get('editor_id')
        
        if not editor_id:
            return Response(
                {'error': 'Se requiere un ID de editor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            editor = Trabajador.objects.get(pk=editor_id)
            noticia.editores_en_jefe.add(editor)
            return Response({'success': True})
        except Trabajador.DoesNotExist:
            return Response(
                {'error': 'Editor no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def eliminar_editor(self, request, pk=None):
        """Eliminar un editor de una noticia"""
        noticia = self.get_object()
        editor_id = request.data.get('editor_id')
        
        if not editor_id:
            return Response(
                {'error': 'Se requiere un ID de editor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            editor = Trabajador.objects.get(pk=editor_id)
            noticia.editores_en_jefe.remove(editor)
            return Response({'success': True})
        except Trabajador.DoesNotExist:
            return Response(
                {'error': 'Editor no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def get_object(self):
        """
        Obtener objeto con soporte para pk o pk-slug en la URL
        Maneja slugs largos correctamente
        """
        pk_value = self.kwargs.get(self.lookup_field)
        pk_str = str(pk_value) if pk_value is not None else ''
        
        if pk_str and '-' in pk_str:
            pk = pk_str.split('-', 1)[0]
        else:
            pk = pk_value
        
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj
            
    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        """
        Subir imagen a Imgur
        Uso: POST /api/noticias/upload_image/ con form-data: image=<archivo>
        """
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        image = request.FILES['image']
        
        if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return Response({
                'error': 'Tipo de archivo no soportado. Use PNG, JPG, JPEG o GIF.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        uploaded_url = upload_to_imgur(image)
            
        if uploaded_url:
            return Response({
                'success': True, 
                'url': uploaded_url,
                'message': 'Imagen subida exitosamente a Imgur'
            })
        else:
            return Response({
                'error': 'Error al subir la imagen a Imgur'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
User = get_user_model()

# Vista para el registro de usuarios
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def redirect_to_home(request):
    return redirect('/home/')

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("Usuario no autenticado.")
        
        # Intentar obtener el perfil del usuario
        try:
            # Primero buscamos en UserProfile
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            # Si no existe, verificamos si es un trabajador
            try:
                trabajador = Trabajador.objects.get(user=user)
                # Si es un trabajador, creamos un UserProfile asociado
                profile = UserProfile.objects.create(
                    user=user,
                    nombre=trabajador.nombre,
                    apellido=trabajador.apellido,
                    foto_perfil=trabajador.foto_perfil,
                    descripcion_usuario=trabajador.descripcion_usuario,
                    es_trabajador=True
                )
                return profile
            except Trabajador.DoesNotExist:
                # Si no es un trabajador, creamos un perfil vacío
                profile = UserProfile.objects.create(
                    user=user,
                    nombre=user.first_name,
                    apellido=user.last_name,
                    es_trabajador=False
                )
                return profile

    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vista para el inicio de sesión de usuarios
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Add debugging to see what's being received
        print(f"Login attempt with data: {request.data}")
        
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Please provide both username and password'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({'error': 'Invalid credentials'}, 
                            status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Check if user is a worker (Trabajador)
        try:
            from .models import Trabajador
            trabajador = Trabajador.objects.get(user=user)
            from .serializers import TrabajadorSerializer
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'trabajador': TrabajadorSerializer(trabajador).data
            })
        except Exception as e:
            # Regular user or error occurred
            print(f"Error fetching trabajador: {e}")
            from .serializers import UserSerializer
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user is a worker
        try:
            trabajador = Trabajador.objects.get(user=user)
            return Response({
                'isWorker': True,
                **TrabajadorSerializer(trabajador).data
            })
        except Trabajador.DoesNotExist:
            # Regular user
            return Response({
                'isWorker': False,
                **UserSerializer(user).data
            })

class AdminViewSet(viewsets.ModelViewSet):
    queryset = BASE_QUERYSET.filter(is_staff=True)
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        # Add logic for admin dashboard data
        total_users = User.objects.count()
        total_noticias = Noticia.objects.count()
        # Add more statistics as needed
        return Response({
            'total_users': total_users,
            'total_noticias': total_noticias,
            # Add more data as needed
        })
class EstadoPublicacionList(generics.ListAPIView):
    queryset = EstadoPublicacion.objects.all()
    serializer_class = EstadoPublicacionSerializer

class TrabajadorList(generics.ListAPIView):
    queryset = Trabajador.objects.all()
    serializer_class = TrabajadorSerializer

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    def perform_update(self, serializer):
        serializer.save()


@api_view(['POST'])
def upload_image(request):
    if 'image' not in request.FILES:
        return Response({'error': 'No image file found'}, status=status.HTTP_400_BAD_REQUEST)

    image = request.FILES['image']

    # Verificar tipo de archivo
    if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return Response({
            'error': 'Tipo de archivo no soportado. Por favor suba una imagen PNG, JPG, JPEG o GIF.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Subir directamente a Imgur
    uploaded_url = upload_to_imgur(image)

    if uploaded_url:
        return Response({
            'success': True, 
            'url': uploaded_url,
            'message': 'Imagen subida exitosamente a Imgur'
        })
    else:
        return Response({
            'error': 'Error al subir la imagen a Imgur'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
def update_trabajador(request, pk):
    try:
        trabajador = Trabajador.objects.get(pk=pk)
    except Trabajador.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = TrabajadorSerializer(trabajador, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['PUT'])
def update_user_profile(request):
    trabajador = request.user.trabajador  # Obtener el trabajador asociado al usuario
    
    # Obtener los datos enviados en la solicitud
    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    foto_perfil_url = request.data.get('foto_perfil')  # URL de la imagen
    foto_perfil_file = request.FILES.get('foto_perfil_local')  # Imagen local

    # Actualizar los campos básicos si están presentes
    if nombre:
        trabajador.nombre = nombre
    if apellido:
        trabajador.apellido = apellido

    # Manejo de la imagen de perfil
    if foto_perfil_file:
        # Si se envía una imagen local, se guarda en el servidor
        try:
            file_name = default_storage.save(f'perfil/{foto_perfil_file.name}', ContentFile(foto_perfil_file.read()))
            trabajador.foto_perfil_local = file_name
            trabajador.foto_perfil = None  # Limpiar el campo de URL si se sube una imagen local
        except Exception as e:
            return Response({'error': f'Error uploading file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif foto_perfil_url:
        # Si se envía una URL de la imagen, actualizamos el campo
        trabajador.foto_perfil = foto_perfil_url
        trabajador.foto_perfil_local = None  # Limpiar el campo de archivo local si se proporciona una URL

    # Guardar los cambios en el perfil del trabajador
    trabajador.save()

    # Devolver una respuesta con los datos actualizados del trabajador
    return Response({
        'nombre': trabajador.nombre,
        'apellido': trabajador.apellido,
        'foto_perfil': trabajador.get_foto_perfil(),  # Método que devuelve la URL o el archivo local
    }, status=status.HTTP_200_OK)


#para las reacciones de las noticias:


# views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Noticia, ReaccionNoticia
from .serializers import ReaccionNoticiaSerializer

@api_view(['GET', 'POST', 'DELETE'])
def reacciones_noticia(request, id):
    try:
        noticia = Noticia.objects.get(pk=id)
    except Noticia.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Cualquier usuario puede ver el conteo
        return Response(noticia.get_conteo_reacciones())

    # Para POST y DELETE requerimos autenticación
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Debes iniciar sesión para realizar esta acción'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == 'POST':
        tipo_reaccion = request.data.get('tipo_reaccion')
        if not tipo_reaccion:
            return Response(
                {'error': 'tipo_reaccion es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        reaccion, created = ReaccionNoticia.objects.update_or_create(
            noticia=noticia,
            usuario=request.user,
            defaults={'tipo_reaccion': tipo_reaccion}
        )
        
        serializer = ReaccionNoticiaSerializer(reaccion)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    elif request.method == 'DELETE':
        ReaccionNoticia.objects.filter(
            noticia=noticia,
            usuario=request.user
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mi_reaccion(request, id):
    try:
        noticia = Noticia.objects.get(pk=id)
        reaccion = ReaccionNoticia.objects.get(
            noticia=noticia,
            usuario=request.user
        )
        serializer = ReaccionNoticiaSerializer(reaccion)
        return Response(serializer.data)
    except Noticia.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except ReaccionNoticia.DoesNotExist:
        return Response({'tipo_reaccion': None})
    

# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import PasswordResetToken
from .serializers import RequestPasswordResetSerializer, VerifyTokenSerializer, ResetPasswordSerializer
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

class RequestPasswordResetView(APIView):
    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Crear token de recuperación
            token_obj = PasswordResetToken.objects.create(user=user)
            
            # Enviar correo con el token
            subject = "Recuperación de contraseña"
            message = f"""
            Hola {user.username},
            
            Recibimos una solicitud para restablecer tu contraseña.
            
            Tu código de recuperación es: {token_obj.token}
            
            Este código es válido por 24 horas.
            
            Si no solicitaste este cambio, puedes ignorar este correo.
            
            Saludos,
            El equipo de [Nombre de tu aplicación]
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response({"message": "Se ha enviado un correo con instrucciones para recuperar tu contraseña."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyTokenView(APIView):
    def post(self, request):
        serializer = VerifyTokenSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Token válido."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password = serializer.validated_data['password']
            
            # Buscar el token
            token_obj = PasswordResetToken.objects.get(token=token)
            
            # Cambiar la contraseña del usuario
            user = token_obj.user
            user.set_password(password)
            user.save()
            
            # Marcar el token como usado
            token_obj.used = True
            token_obj.save()
            
            return Response({"message": "Contraseña actualizada exitosamente."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Donacion
from .serializers import DonacionSerializer

class DonacionViewSet(viewsets.ModelViewSet):
    queryset = Donacion.objects.all()
    serializer_class = DonacionSerializer
    permission_classes = [AllowAny]  # Cualquiera puede hacer una donación
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            donacion = serializer.save()
            return Response({
                'success': True,
                'message': 'Donación registrada exitosamente. Te hemos enviado un correo de confirmación.',
                'donacion': DonacionSerializer(donacion).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_permissions(self):
        # Solo admin puede ver lista y detalles
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        # Cualquiera puede crear
        return [AllowAny()]
    

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import MensajeGlobal, RespuestaMensajeGlobal, Trabajador
from .serializers import MensajeGlobalSerializer, RespuestaMensajeGlobalSerializer


class MensajeGlobalViewSet(viewsets.ModelViewSet):
    serializer_class = MensajeGlobalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Retorna solo mensajes activos y no expirados.
        Limpia mensajes expirados automáticamente.
        """
        # Primero, marcar como inactivos los mensajes expirados
        MensajeGlobal.objects.filter(
            fecha_expiracion__lte=timezone.now(),
            activo=True
        ).update(activo=False)
        
        # Opcional: Eliminar mensajes expirados hace más de 1 día
        fecha_limite = timezone.now() - timedelta(days=1)
        MensajeGlobal.objects.filter(
            fecha_expiracion__lte=fecha_limite,
            activo=False
        ).delete()
        
        # Retornar solo mensajes activos
        return MensajeGlobal.objects.filter(activo=True).prefetch_related('respuestas')
    
    def perform_create(self, serializer):
        """Asigna automáticamente el trabajador del usuario autenticado"""
        try:
            trabajador = Trabajador.objects.get(user=self.request.user)
            serializer.save(trabajador=trabajador)
        except Trabajador.DoesNotExist:
            raise PermissionDenied("Solo los trabajadores pueden crear mensajes globales.")
    
    def create(self, request, *args, **kwargs):
        """Valida que el usuario sea un trabajador antes de crear"""
        try:
            trabajador = Trabajador.objects.get(user=request.user)
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "Solo los trabajadores pueden crear mensajes globales."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Solo el autor puede eliminar su mensaje"""
        mensaje = self.get_object()
        
        try:
            trabajador = Trabajador.objects.get(user=request.user)
            
            # Verificar que el trabajador sea el autor
            if mensaje.trabajador != trabajador:
                return Response(
                    {"error": "Solo puedes eliminar tus propios mensajes."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            mensaje.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "Usuario no autorizado."},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=True, methods=['post'])
    def responder(self, request, pk=None):
        """Permite a un trabajador responder a un mensaje global"""
        mensaje = self.get_object()
        
        # Verificar que el mensaje no esté expirado
        if mensaje.esta_expirado():
            return Response(
                {"error": "No puedes responder a un mensaje expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            trabajador = Trabajador.objects.get(user=request.user)
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "Solo los trabajadores pueden responder."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar que la respuesta no esté vacía
        respuesta_texto = request.data.get('respuesta', '').strip()
        if not respuesta_texto:
            return Response(
                {"error": "La respuesta no puede estar vacía."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear la respuesta
        respuesta = RespuestaMensajeGlobal.objects.create(
            mensaje_global=mensaje,
            trabajador=trabajador,
            respuesta=respuesta_texto
        )
        
        serializer = RespuestaMensajeGlobalSerializer(respuesta)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def eliminar_respuesta(self, request, pk=None):
        """Permite eliminar una respuesta propia"""
        respuesta_id = request.data.get('respuesta_id')
        
        if not respuesta_id:
            return Response(
                {"error": "Se requiere el ID de la respuesta."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            trabajador = Trabajador.objects.get(user=request.user)
            respuesta = RespuestaMensajeGlobal.objects.get(
                id=respuesta_id,
                mensaje_global_id=pk
            )
            
            # Verificar que el trabajador sea el autor de la respuesta
            if respuesta.trabajador != trabajador:
                return Response(
                    {"error": "Solo puedes eliminar tus propias respuestas."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            respuesta.delete()
            return Response(
                {"message": "Respuesta eliminada exitosamente."},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "Usuario no autorizado."},
                status=status.HTTP_403_FORBIDDEN
            )
        except RespuestaMensajeGlobal.DoesNotExist:
            return Response(
                {"error": "Respuesta no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def mis_mensajes(self, request):
        """Retorna solo los mensajes del trabajador autenticado"""
        try:
            trabajador = Trabajador.objects.get(user=request.user)
            mensajes = self.get_queryset().filter(trabajador=trabajador)
            serializer = self.get_serializer(mensajes, many=True)
            return Response(serializer.data)
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "Usuario no autorizado."},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['post'])
    def limpiar_expirados(self, request):
        """Limpia manualmente todos los mensajes expirados (solo para testing)"""
        try:
            trabajador = Trabajador.objects.get(user=request.user)
            
            # Marcar como inactivos
            actualizados = MensajeGlobal.objects.filter(
                fecha_expiracion__lte=timezone.now(),
                activo=True
            ).update(activo=False)
            
            # Eliminar los muy antiguos
            fecha_limite = timezone.now() - timedelta(days=1)
            eliminados = MensajeGlobal.objects.filter(
                fecha_expiracion__lte=fecha_limite,
                activo=False
            ).delete()
            
            return Response({
                "message": "Limpieza completada",
                "mensajes_desactivados": actualizados,
                "mensajes_eliminados": eliminados[0]
            })
            
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "Usuario no autorizado."},
                status=status.HTTP_403_FORBIDDEN
            )