import json

from tests import BaseTest
from tests.utils.assertion import contains, is_instance, is_true


class TestThreadRoutes(BaseTest):
    """Test the thread routes functionality."""

    def test_chat_endpoint(self):
        """Test the /chat endpoint for processing chat messages."""
        client = self.app.test_client()

        data = {"messages": [{"role": "user", "content": "say hello!"}]}

        response = client.post("/v1/threads/chat", data=json.dumps(data), content_type="application/json")

        is_true(response.status_code in [200, 400, 500])

        response_data = json.loads(response.data)

        if response.status_code == 200:
            contains(response_data, "payload")
            is_instance(response_data["payload"], list)
            contains(response_data["payload"][0], "role")
            assert len(response_data["payload"]) >= 1

            # The second response may be either assistant or tool
            contains(["assistant", "tool"], response_data["payload"][0]["role"])

            contains(response_data["payload"][0], "content")
        else:
            contains(response_data, "correlation_id")
            contains(response_data, "payload")
            contains(response_data, "status")
            is_true(response_data["status"] in [400, 500])
