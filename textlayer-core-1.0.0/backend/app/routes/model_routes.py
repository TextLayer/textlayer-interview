from flask import Blueprint

from app.controllers.model_controller import ModelController
from app.decorators import handle_exceptions
from app.utils.response import Response

model_routes = Blueprint("model_routes", __name__)
model_controller = ModelController()


@model_routes.get("/")
@handle_exceptions
def get_models():
    """Retrieves the list of available models."""
    response = model_controller.get_models()
    return Response.make(response, Response.HTTP_SUCCESS)
