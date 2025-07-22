import os
import tempfile

from flask import Blueprint, abort, render_template, send_file

frontend_routes = Blueprint("frontend_routes", __name__)


@frontend_routes.route("/")
def index():
    """Serve the main chat interface."""
    return render_template("chat.html")


@frontend_routes.route("/chat")
def chat_page():
    """Alternative route for the chat interface."""
    return render_template("chat.html")


@frontend_routes.route('/download/<filename>')
def download_file(filename):
    """Serve downloadable files (SQL scripts, CSV data)"""
    try:
        # Security: Only serve files from temp directory with expected patterns
        if not (filename.startswith('sql_query_') or
                filename.startswith('query_results_')):
            abort(404)

        if not (filename.endswith('.sql') or filename.endswith('.csv')):
            abort(404)

        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)

        if not os.path.exists(file_path):
            abort(404)

        # Set appropriate MIME type
        mimetype = 'text/plain' if filename.endswith('.sql') else 'text/csv'

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )

    except Exception as e:
        print(f"Error serving download file: {e}")
        abort(404)


@frontend_routes.route('/error')
def error():
    """Error page"""
    return render_template('error.html')