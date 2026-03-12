from django.views.generic import TemplateView

class Index(TemplateView):
    template_name = "website/inicio.html"

class Sobre(TemplateView):
    template_name = "website/sobre.html"

class Contato(TemplateView):
    template_name = "website/contato.html"  
    
class Login(TemplateView):
    template_name = "website/login.html"
    
class Cadastro(TemplateView):
    template_name = "website/singup.html"
    