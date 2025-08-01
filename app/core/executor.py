class Executor:
    __instance = None

    @staticmethod
    def getInstance():
        if not Executor.__instance:
            Executor()
        return Executor.__instance

    def __init__(self):
        if Executor.__instance:
            raise Exception("This class is a singleton!")
        else:
            Executor.__instance = self

    @staticmethod
    def execute_write(command):
        return command.execute()

    @staticmethod
    def execute_read(command):
        return command.execute()
