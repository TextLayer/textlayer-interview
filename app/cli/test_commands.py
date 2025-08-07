"""
Test CLI Commands

Implements the 'flask test' command mentioned in README.md.
Provides test execution with coverage reporting and various options.

Commands:
    flask test          - Run all tests
    flask test --coverage - Run tests with coverage report
    flask test --verbose  - Run tests with verbose output
    flask test --pattern  - Run tests matching pattern
"""

import click
import sys
import subprocess
import os
from flask import current_app
from flask.cli import with_appcontext


@click.command()
@click.option('--coverage', is_flag=True, help='Run tests with coverage report')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--pattern', '-k', help='Run tests matching pattern')
@click.option('--html', is_flag=True, help='Generate HTML coverage report')
@click.option('--fail-fast', '-x', is_flag=True, help='Stop on first failure')
@with_appcontext
def test(coverage, verbose, pattern, html, fail_fast):
    """
    Run the test suite.
    
    This command runs pytest with various options for comprehensive testing.
    Supports coverage reporting, pattern matching, and verbose output.
    
    Examples:
        flask test
        flask test --coverage
        flask test --verbose --pattern test_text_to_sql
        flask test --coverage --html
    """
    try:
        # Check if pytest is available
        subprocess.run(['pytest', '--version'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("Error: pytest not found. Install with: pip install pytest pytest-cov")
        sys.exit(1)
    
    # Build pytest command
    cmd = ['pytest']
    
    # Add coverage options
    if coverage:
        cmd.extend(['--cov=app', '--cov-report=term-missing'])
        if html:
            cmd.append('--cov-report=html')
    
    # Add verbosity
    if verbose:
        cmd.append('-v')
    
    # Add pattern matching
    if pattern:
        cmd.extend(['-k', pattern])
    
    # Add fail fast
    if fail_fast:
        cmd.append('-x')
    
    # Add test directory
    cmd.append('tests/')
    
    # Set environment variables for testing
    env = os.environ.copy()
    env['FLASK_CONFIG'] = 'TEST'
    env['TESTING'] = 'True'
    
    # If no real API key is set, use test key
    if not env.get('GOOGLE_API_KEY') or env.get('GOOGLE_API_KEY') == 'your-real-gemini-key':
        env['GOOGLE_API_KEY'] = 'test-key'
        env['GEMINI_API_KEY'] = 'test-key'
    
    click.echo(f"Running command: {' '.join(cmd)}")
    click.echo("=" * 60)
    
    # Run tests
    result = subprocess.run(cmd, env=env)
    
    if result.returncode == 0:
        click.echo("=" * 60)
        click.echo("✅ All tests passed!")
        
        if coverage and html:
            click.echo("📊 HTML coverage report generated in htmlcov/")
            click.echo("💡 Open htmlcov/index.html in your browser to view the report")
    else:
        click.echo("=" * 60)
        click.echo("❌ Some tests failed!")
        sys.exit(1)


@click.command()
@click.option('--install', is_flag=True, help='Install test dependencies')
@with_appcontext
def test_setup(install):
    """
    Set up the testing environment.
    
    Installs necessary testing dependencies and prepares the test environment.
    """
    if install:
        click.echo("Installing test dependencies...")
        
        # Install test packages
        test_packages = [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'pytest-flask>=1.2.0',
            'coverage>=7.0.0'
        ]
        
        for package in test_packages:
            click.echo(f"Installing {package}...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', package
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                click.echo(f"❌ Failed to install {package}")
                click.echo(result.stderr)
                sys.exit(1)
            else:
                click.echo(f"✅ {package} installed successfully")
        
        click.echo("🎉 Test environment setup complete!")
    else:
        click.echo("Test setup options:")
        click.echo("  --install    Install test dependencies")


def init_test_commands(app):
    """
    Initialize test commands for the Flask CLI.
    
    Args:
        app: Flask application instance
    """
    app.cli.add_command(test)
    app.cli.add_command(test_setup)