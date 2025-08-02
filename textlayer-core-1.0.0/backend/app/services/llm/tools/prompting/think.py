from langfuse.decorators import observe
from vaul import tool_call


@tool_call
@observe
def think(thought: str) -> str:
    """Use the tool to think about something. It will not obtain new information or change the
    database, but just append the thought to the log. Use it when complex reasoning or some cache
    memory is needed.
    Args:
        thought: A thought to think about.
    """

    return thought
