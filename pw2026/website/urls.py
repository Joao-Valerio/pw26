from django.urls import path
from .views import Index, Sobre, Contato

urlpatterns = [
    # path("admin/", admin.site.urls),

    path("inicio/", Index.as_view(), name="pagina_inicial"),
    path("sobre/", Sobre.as_view(), name="sobre"),
    path("contato/", Contato.as_view(), name="contato"),
]
