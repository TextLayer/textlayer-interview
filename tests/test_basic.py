import unittest
from unittest.mock import patch, MagicMock
from app.commands.threads.process_chat_message import ProcessChatMessageCommand
from app.errors import ValidationException


class TestProcessChatMessageCommand(unittest.TestCase):

    def setUp(self):
        self.sql_question = {
            "role": "user",
            "content": "What is the total sales revenue by region?"
        }
        self.year_filter_question = {
            "role": "user",
            "content": "Show me the total sales revenue by region for the year 2023."
        }
        self.non_sql_question = {
            "role": "user",
            "content": "Tell me a joke."
        }

    @patch("app.services.llm.session.LLMSession.chat")
    @patch("app.commands.threads.process_chat_message.ProcessChatMessageCommand.execute_tool_call")
    def test_sql_query_with_tool_call(self, mock_execute_tool_call, mock_llm_chat):
        mock_llm_chat.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="SELECT region, SUM(sales) FROM sales_data GROUP BY region",
                        tool_calls=[MagicMock(
                            id="tool-call-1",
                            function=MagicMock(
                                name="text_to_sql",
                                arguments='{"query": "SELECT region, SUM(sales) FROM sales_data GROUP BY region"}'
                            )
                        )]
                    ),
                    finish_reason="tool_calls"
                )
            ]
        )

        mock_execute_tool_call.return_value = {
            "query": "SELECT region, SUM(sales) FROM sales_data GROUP BY region",
            "result": [
                {"region": "East", "sum": 1000},
                {"region": "West", "sum": 800},
            ],
        }

        command = ProcessChatMessageCommand(chat_messages=[self.sql_question])
        response_messages = command.execute()

        assistant_contents = [m["content"].lower() for m in response_messages if m["role"] == "assistant"]
        self.assertTrue(any("select" in content for content in assistant_contents))

    @patch("app.services.llm.session.LLMSession.chat")
    @patch("app.commands.threads.process_chat_message.ProcessChatMessageCommand.execute_tool_call")
    def test_year_filtering_query(self, mock_execute_tool_call, mock_llm_chat):
        mock_llm_chat.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="SELECT region, SUM(sales) FROM sales_data WHERE year = 2023 GROUP BY region",
                        tool_calls=[MagicMock(
                            id="tool-call-2",
                            function=MagicMock(
                                name="text_to_sql",
                                arguments='{"query": "SELECT region, SUM(sales) FROM sales_data WHERE year = 2023 GROUP BY region"}'
                            )
                        )]
                    ),
                    finish_reason="tool_calls"
                )
            ]
        )

        mock_execute_tool_call.return_value = {
            "query": "SELECT region, SUM(sales) FROM sales_data WHERE year = 2023 GROUP BY region",
            "result": [
                {"region": "East", "sum": 1200},
                {"region": "West", "sum": 900},
            ],
        }

        command = ProcessChatMessageCommand(chat_messages=[self.year_filter_question])
        response_messages = command.execute()

        assistant_contents = [m["content"].lower() for m in response_messages if m["role"] == "assistant"]
        self.assertTrue(any("select" in content for content in assistant_contents))

    def test_non_sql_question_refusal(self):
        command = ProcessChatMessageCommand(chat_messages=[self.non_sql_question])
        response_messages = command.execute()

        last_message = response_messages[-1]
        self.assertEqual(last_message["role"], "assistant")
        self.assertIn("only answer questions related to data queries and sql", last_message["content"].lower())

    @patch("app.services.llm.session.LLMSession.chat")
    def test_llm_judge_failure_handling(self, mock_llm_chat):
        mock_llm_chat.side_effect = [
            MagicMock(  # Assistant response
                choices=[MagicMock(
                    message=MagicMock(
                        content="SELECT * FROM sales_data",
                        tool_calls=None
                    ),
                    finish_reason="stop"
                )]
            ),
            Exception("Judge failed")  # Judge failure
        ]

        command = ProcessChatMessageCommand(chat_messages=[self.sql_question])
        response_messages = command.execute()

        judge_messages = [m for m in response_messages if m["role"] == "judge"]
        self.assertTrue(any("failed" in m["content"].lower() or "error" in m["content"].lower() for m in judge_messages))

    @patch("app.services.llm.session.LLMSession.chat")
    def test_llm_judge_success_handling(self, mock_llm_chat):
        mock_llm_chat.side_effect = [
            MagicMock(  # Assistant response
                choices=[MagicMock(
                    message=MagicMock(
                        content="SELECT * FROM sales_data",
                        tool_calls=None
                    ),
                    finish_reason="stop"
                )]
            ),
            MagicMock(  # Judge success
                choices=[MagicMock(
                    message=MagicMock(
                        content="The SQL and explanation look correct and clear.",
                    ),
                    finish_reason="stop"
                )]
            )
        ]

        command = ProcessChatMessageCommand(chat_messages=[self.sql_question])
        response_messages = command.execute()

        judge_messages = [m for m in response_messages if m["role"] == "judge"]
        self.assertTrue(any("correct" in m["content"].lower() for m in judge_messages))


if __name__ == "__main__":
    unittest.main()
