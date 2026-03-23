from .models import VisitaSite


class RegistrarVisitaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Ignorar arquivos estáticos, media e admin
        path = request.path
        if path.startswith(("/static/", "/media/", "/admin/", "/favicon")):
            return response

        # Ignorar requisições que não são GET ou com status != 200
        if request.method != "GET" or response.status_code != 200:
            return response

        try:
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            if not ip:
                ip = request.META.get("REMOTE_ADDR", "0.0.0.0")

            usuario = request.user if request.user.is_authenticated else None

            VisitaSite.objects.create(
                ip=ip,
                pagina=path,
                usuario=usuario,
            )
        except Exception:
            pass

        return response
