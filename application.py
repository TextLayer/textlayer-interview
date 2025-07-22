import os

import click
from dotenv import load_dotenv

from app import create_app

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

app = create_app(os.getenv('FLASK_CONFIG') or 'DEV')


@app.cli.command()
@click.option(
    "--coverage/--no-coverage",
    default=False,
    help="Run tests under code coverage.",
)
@click.argument("test_names", nargs=-1)
def test(coverage, test_names):
    """Run the unit tests."""
    from app.cli import run_tests

    test_results = run_tests(coverage, test_names)

    if test_results.wasSuccessful():
        exit(0)

    exit(1)


if __name__ == '__main__':
    # Port 5000 is often used by AirPlay on macOS, so use 5001
    port = int(os.environ.get('PORT', 5001))
    app.run(host='127.0.0.1', port=port, debug=True)