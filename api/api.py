from django.conf import settings
from ninja import NinjaAPI
from ninja.parser import Parser

from api.routers.account import router as account_router
from api.routers.auth import router as auth_router
from api.routers.ladder import router as ladder_router
from api.routers.players import router as players_router
from ladder.services.result_entry import (
    ResultMutationError,
    ResultNotFoundError,
    ResultPermissionError,
)


class SafeEmptyBodyParser(Parser):
    """Treat empty or non-JSON bodies as {} so cookie-based auth calls work cleanly."""

    def parse_body(self, request):
        if not request.body or not request.body.strip():
            return {}
        if request.content_type and "json" not in request.content_type.lower():
            return {}
        return super().parse_body(request)


api = NinjaAPI(
    title="Highgate Competitions API",
    version="1.0.0",
    urls_namespace="api-v1",
    docs_url="/docs" if settings.DEBUG else None,
    parser=SafeEmptyBodyParser(),
)


@api.exception_handler(ResultNotFoundError)
def handle_result_not_found(request, exc: ResultNotFoundError):
    return api.create_response(request, {"detail": exc.message}, status=404)


@api.exception_handler(ResultPermissionError)
def handle_result_permission_denied(request, exc: ResultPermissionError):
    return api.create_response(request, {"detail": exc.message}, status=403)


@api.exception_handler(ResultMutationError)
def handle_result_mutation_error(request, exc: ResultMutationError):
    return api.create_response(request, {"detail": exc.message}, status=400)


api.add_router("/auth", auth_router, tags=["Auth"])
api.add_router("/account", account_router, tags=["Account"])
api.add_router("/players", players_router, tags=["Players"])
api.add_router("/ladder", ladder_router, tags=["Ladder"])
