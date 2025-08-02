import json
import os

from app import create_app, logger


def sample_handler(event, context):
    app = create_app(os.getenv("FLASK_CONFIG") or "DEV")

    try:
        # Store event_body but don't assign if not being used
        json.loads(event["Records"][0]["body"])  # Validate the JSON is parseable
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing event: {e}")
        return False

    with app.app_context():
        logger.debug("Sample handler executed successfully.")

    return True
