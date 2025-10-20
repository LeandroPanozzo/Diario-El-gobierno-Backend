from rest_framework.routers import DefaultRouter
from django.urls import path, include, re_path
from . import views
from .views import (
    DonacionViewSet,
    RolViewSet,
    TrabajadorViewSet,
    UsuarioViewSet,
    NoticiaViewSet,
    ComentarioViewSet,
    EstadoPublicacionViewSet,
    ImagenViewSet,
    PublicidadViewSet,
    AdminViewSet,
    UserrViewSet,
    redirect_to_home,
    CurrentUserView,
    ComentarioListCreateAPIView,
    CommentDeleteView,
    RegisterView,
    LoginView,
    RequestPasswordResetView,
    ResetPasswordView,
    UserProfileView,
    EstadoPublicacionList,
    TrabajadorList,
    VerifyTokenView,
    upload_image
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Crear un router y registrar todos los viewsets
router = DefaultRouter()
router.register(r'roles', RolViewSet)
router.register(r'users', UserrViewSet, basename='user')
router.register(r'admin', AdminViewSet, basename='admin')
router.register(r'trabajadores', TrabajadorViewSet)
router.register(r'usuarios', UsuarioViewSet)
router.register(r'estados', EstadoPublicacionViewSet)
router.register(r'comentarios', ComentarioViewSet)
router.register(r'imagenes', ImagenViewSet)
router.register(r'publicidades', PublicidadViewSet)
router.register(r'noticias', NoticiaViewSet, basename='noticias')
router.register(r'donaciones', DonacionViewSet, basename='donaciones')

urlpatterns = [
    path('', redirect_to_home, name='redirect_to_home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('estados-publicacion/', EstadoPublicacionList.as_view(), name='estado-publicacion-list'),
    path('trabajadores/', TrabajadorList.as_view(), name='trabajador-list'),
    path('upload_image/', NoticiaViewSet.as_view({'post': 'upload_image'}), name='upload_image'),
    
    # ===== RUTAS DE NOTICIAS - ORDEN CRÍTICO =====
    # IMPORTANTE: Las rutas más específicas DEBEN ir ANTES de las rutas con parámetros
    
    # 1. Rutas de acción (sin parámetros numéricos)
    path('noticias/buscar/', NoticiaViewSet.as_view({'get': 'buscar'}), name='noticias-buscar'),
    path('noticias/mas-vistas/', NoticiaViewSet.as_view({'get': 'mas_vistas'}), name='noticias-mas-vistas'),
    path('noticias/mas-leidas/', NoticiaViewSet.as_view({'get': 'mas_leidas'}), name='noticias-mas-leidas'),
    path('noticias/populares-semana/', NoticiaViewSet.as_view({'get': 'populares_semana'}), name='noticias-populares-semana'),
    path('noticias/populares-historico/', NoticiaViewSet.as_view({'get': 'populares_historico'}), name='noticias-populares-historico'),
    path('noticias/estadisticas-visitas/', NoticiaViewSet.as_view({'get': 'estadisticas_visitas'}), name='noticias-estadisticas-visitas'),
    path('noticias/recientes/', NoticiaViewSet.as_view({'get': 'recientes'}), name='noticias-recientes'),
    path('noticias/destacadas/', NoticiaViewSet.as_view({'get': 'destacadas'}), name='noticias-destacadas'),
    path('noticias/politica/', NoticiaViewSet.as_view({'get': 'politica'}), name='noticias-politica'),
    path('noticias/cultura/', NoticiaViewSet.as_view({'get': 'cultura'}), name='noticias-cultura'),
    path('noticias/economia/', NoticiaViewSet.as_view({'get': 'economia'}), name='noticias-economia'),
    path('noticias/mundo/', NoticiaViewSet.as_view({'get': 'mundo'}), name='noticias-mundo'),
    path('noticias/tipos-notas/', NoticiaViewSet.as_view({'get': 'tipos_notas'}), name='noticias-tipos-notas'),
    path('noticias/por-categoria/', NoticiaViewSet.as_view({'get': 'por_categoria'}), name='noticias-por-categoria'),
    
    # 2. Rutas con parámetros de ID y acciones específicas
    path('noticias/<int:noticia_id>/comentarios/', ComentarioViewSet.as_view({'get': 'list', 'post': 'create'}), name='comentarios'),
    path('noticias/<int:noticia_id>/comentarios/<int:comment_id>/', ComentarioViewSet.as_view({'delete': 'destroy'}), name='delete_comentario'),
    path('noticias/<int:id>/reacciones/', views.reacciones_noticia, name='reacciones_noticia'),
    path('noticias/<int:id>/mi-reaccion/', views.mi_reaccion, name='mi_reaccion'),
    
    # 3. Rutas de detalle con slug (más específicas primero)
    re_path(r'^noticias/(?P<pk>\d+)-(?P<slug>[\w-]+)/$', 
        NoticiaViewSet.as_view({'get': 'retrieve'}), 
        name='noticia-detail'),
    
    # 4. Ruta de detalle solo con ID (al final)
    path('noticias/<int:pk>/', NoticiaViewSet.as_view({'get': 'retrieve'}), name='noticia-detail-id-only'),
    
    # ===== FIN DE RUTAS DE NOTICIAS =====
    
    path('upload/', upload_image, name='upload_image'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('current-user/', CurrentUserView.as_view(), name='current-user'),
    path('password/reset/request/', RequestPasswordResetView.as_view(), name='password-reset-request'),
    path('password/reset/verify/', VerifyTokenView.as_view(), name='password-reset-verify'),
    path('password/reset/confirm/', ResetPasswordView.as_view(), name='password-reset-confirm'),
    
    # El router debe ir al final para que no interfiera con las rutas específicas
    path('', include(router.urls)),
]