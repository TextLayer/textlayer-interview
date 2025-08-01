class ReadCommand:
    """
    Abstract base class for read-only operations in the command pattern.

    ReadCommand is part of the application's command processing architecture,
    specifically for operations that retrieve data without modifying the system state.
    This pattern provides a clean separation of concerns by isolating business logic
    from request handling.

    Concrete implementations should override the execute method to implement specific
    read functionality. This approach ensures that business logic is organized in
    distinct command modules for better maintainability.

    Example:
        class GetUserCommand(ReadCommand):
            def __init__(self, user_id):
                self.user_id = user_id

            def execute(self):
                # Implementation to fetch user from database
                return {"id": self.user_id, "name": "Example User"}
    """

    def execute(self):
        """
        Execute the read command and return the result.

        This method must be implemented by all concrete command classes.

        Returns:
            The result of the read operation, which can be of any type depending on
            the specific command implementation.

        Raises:
            NotImplementedError: If the concrete class does not implement this method.
        """
        raise NotImplementedError


class WriteCommand:
    """
    Abstract base class for write operations in the command pattern.

    WriteCommand is part of the application's command processing architecture,
    specifically for operations that modify the system state. This pattern ensures
    a clean separation of concerns, with business logic organized in command handlers
    separate from API controllers.

    Concrete implementations should override the execute method to implement specific
    write functionality. This modular design promotes maintainability and testability
    of business logic.

    Example:
        class CreateUserCommand(WriteCommand):
            def __init__(self, user_data):
                self.user_data = user_data

            def execute(self):
                # Implementation to create user in database
                return {"id": "new_id", "status": "created"}
    """

    def execute(self):
        """
        Execute the write command and return the result.

        This method must be implemented by all concrete command classes.

        Returns:
            The result of the write operation, which can be of any type depending on
            the specific command implementation.

        Raises:
            NotImplementedError: If the concrete class does not implement this method.
        """
        raise NotImplementedError
