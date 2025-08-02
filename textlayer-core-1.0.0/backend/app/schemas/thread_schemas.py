import json

from marshmallow import EXCLUDE, pre_dump, validate

from app import ma
from app.utils.models import CHAT_MODELS


class AttachmentSchema(ma.Schema):
    """Schema for message attachments like images or text files"""

    contentType = ma.String(required=True)
    url = ma.String(required=True)

    class Meta:
        unknown = EXCLUDE


class PartSchema(ma.Schema):
    """Schema for message parts"""

    type = ma.String(required=False, data_key="type")
    text = ma.String(required=False)
    image_url = ma.Dict(required=False)

    class Meta:
        unknown = EXCLUDE


class ToolInvocationSchema(ma.Schema):
    """Schema for tool invocations with results"""

    toolCallId = ma.String(required=True)
    toolName = ma.String(required=True)
    args = ma.Raw(required=True)  # Use Raw to accept any type including dict or string
    result = ma.Raw(required=False, allow_none=True)  # Use Raw instead of Dict

    class Meta:
        """Meta options for schema"""

        ordered = True
        unknown = EXCLUDE

    @pre_dump
    def process_input(self, data, **kwargs):
        """Pre-process args and result if they're JSON strings"""
        processed = dict(data)

        # Convert string args to dict if needed
        if isinstance(processed.get("args"), str):
            try:
                processed["args"] = json.loads(processed["args"])
            except json.JSONDecodeError:
                # If it fails to parse as JSON, keep as is
                pass

        # Convert string result to dict if needed
        if isinstance(processed.get("result"), str):
            try:
                processed["result"] = json.loads(processed["result"])
            except json.JSONDecodeError:
                # If it fails to parse as JSON, keep as is
                pass

        return processed


class ChatMessageSchema(ma.Schema):
    """Schema for chat messages with support for attachments and tool invocations"""

    role = ma.String(required=True)
    content = ma.String(required=True)
    id = ma.String(required=False, data_key="id", load_only=True)
    parts = ma.List(ma.Nested(PartSchema), required=False)
    experimental_attachments = ma.List(ma.Nested(AttachmentSchema), required=False)
    toolInvocations = ma.List(ma.Nested(ToolInvocationSchema), required=False)

    class Meta:
        """Meta options for schema"""

        ordered = True
        unknown = EXCLUDE


class ChatMessagesSchema(ma.Schema):
    """Schema for a list of chat messages"""

    id = ma.String(required=False, data_key="id")
    messages = ma.List(
        ma.Nested(ChatMessageSchema),
        required=True,
        validate=validate.Length(min=1),
    )
    model = ma.String(required=False, data_key="model", validate=validate.OneOf(CHAT_MODELS), missing=CHAT_MODELS[0])

    class Meta:
        unknown = EXCLUDE


chat_messages_schema = ChatMessagesSchema()
