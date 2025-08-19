from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, StoreUserMapViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'store-user-maps', StoreUserMapViewSet, basename='storeusermap')

urlpatterns = [
    path('', include(router.urls)),
] 