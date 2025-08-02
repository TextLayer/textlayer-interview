from app.commands.models.get_models import GetModelsCommand
from app.controllers.controller import Controller


class ModelController(Controller):
    def get_models(self):
        return self.executor.execute_read(GetModelsCommand())
