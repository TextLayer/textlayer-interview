from flask import make_response, request

from app.middlewares.auth_middleware import get_current_user
from app.middlewares.logger_middleware import log_request_info, log_response_info
from app.routes.frontend_routes import frontend_routes
from app.routes.thread_routes import thread_routes
from app.utils.messages import Error
from app.utils.response import Response

blueprints = {
    '/threads': thread_routes,
}


def init_routes(app):

    # Custom middleware that excludes static files
    @app.before_request
    def before_request_handler():
        if not request.path.startswith('/static'):
            get_current_user()
            log_request_info()

    @app.after_request
    def after_request_handler(response):
        if not request.path.startswith('/static'):
            log_response_info(response)
        return response

    # Register frontend routes first (no URL prefix for main routes)
    app.register_blueprint(frontend_routes)

    # Register API blueprints with v1 prefix
    for path in blueprints:
        app.register_blueprint(blueprints[path], url_prefix='/v1' + path)

    @app.get("/api")
    def api_info():
        return Response(
            {'api_version': 'v1.0', 'api_description': 'TextLayer Core API'},
            Response.HTTP_SUCCESS
        ).build()

    @app.get("/v1/health")
    def health():
        return Response({'status': 'online'}, Response.HTTP_SUCCESS).build()

    @app.errorhandler(404)
    def not_found_error(error):
        return make_response(Error.NOT_FOUND, Response.HTTP_NOT_FOUND)

    @app.errorhandler(401)
    def unauthorized_error(error):
        return make_response(Error.UNAUTHORIZED, Response.HTTP_UNAUTHORIZED)

    @app.errorhandler(400)
    def bad_request_error(error):
        return make_response(Error.BAD_REQUEST, Response.HTTP_BAD_REQUEST)