import json

from tests import BaseTest
from tests.utils.assertion import contains, is_equal, is_instance, is_true


class TestThreadSchema(BaseTest):
    """Test the thread schema validation."""

    def test_valid_chat_message_schema(self):
        """Test that a valid chat message schema passes validation."""
        client = self.app.test_client()

        data = {"messages": [{"role": "user", "content": "say hello!"}]}

        response = client.post("/v1/threads/chat", data=json.dumps(data), content_type="application/json")

        response_data = json.loads(response.data)

        if response.status_code == 200:
            contains(response_data, "payload")
            is_instance(response_data["payload"], list)
            is_true(len(response_data["payload"]) >= 1)
        else:
            contains(response_data, "correlation_id")
            contains(response_data, "payload")
            contains(response_data, "status")

    def test_missing_messages_field(self):
        """Test that missing messages field fails validation."""
        client = self.app.test_client()

        data = {}

        response = client.post("/v1/threads/chat", data=json.dumps(data), content_type="application/json")

        is_equal(response.status_code, 400)
        response_data = json.loads(response.data)
        contains(response_data, "correlation_id")
        contains(response_data, "payload")
        contains(response_data, "status")
        is_equal(response_data["status"], 400)
        contains(response_data["payload"], "messages")

    def test_empty_messages_list(self):
        """Test that empty messages list fails validation."""
        client = self.app.test_client()

        data = {"messages": []}

        response = client.post("/v1/threads/chat", data=json.dumps(data), content_type="application/json")

        is_equal(response.status_code, 400)
        response_data = json.loads(response.data)
        contains(response_data, "correlation_id")
        contains(response_data, "payload")
        contains(response_data, "status")
        is_equal(response_data["status"], 400)

    def test_missing_role_field(self):
        """Test that missing role field in a message fails validation."""
        client = self.app.test_client()

        data = {"messages": [{"content": "say hello!"}]}

        response = client.post("/v1/threads/chat", data=json.dumps(data), content_type="application/json")

        is_equal(response.status_code, 400)
        response_data = json.loads(response.data)
        contains(response_data, "correlation_id")
        contains(response_data, "payload")
        contains(response_data, "status")
        is_equal(response_data["status"], 400)
        contains(response_data["payload"], "messages")

    def test_missing_content_field(self):
        """Test that missing content field in a message fails validation."""
        client = self.app.test_client()

        data = {"messages": [{"role": "user"}]}

        response = client.post("/v1/threads/chat", data=json.dumps(data), content_type="application/json")

        is_equal(response.status_code, 400)
        response_data = json.loads(response.data)
        contains(response_data, "correlation_id")
        contains(response_data, "payload")
        contains(response_data, "status")
        is_equal(response_data["status"], 400)
        contains(response_data["payload"], "messages")
