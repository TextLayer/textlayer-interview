from typing import Any, Dict, Generator, List, Optional, Union

from app.commands.threads.process_chat_message import ProcessChatMessageCommand
from app.controllers.controller import Controller


class ThreadController(Controller):
    def process_chat_message(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        model: Optional[str] = None,
    ) -> Union[List[Dict[str, Any]], Generator[str, None, None]]:
        return self.executor.execute_write(ProcessChatMessageCommand(messages, stream, model))
