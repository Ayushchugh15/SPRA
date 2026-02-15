#!/usr/bin/env python3
"""
Production entry point.
Uses Gunicorn on Linux/Mac, Waitress on Windows.
"""
import os
import sys

os.environ['FLASK_ENV'] = 'production'

if __name__ == '__main__':
    from app import app, db

    with app.app_context():
        db.create_all()

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    if sys.platform == 'win32':
        try:
            import waitress
            print(f"Starting production server (Waitress) on http://{host}:{port}")
            waitress.serve(app, host=host, port=port, threads=4)
        except ImportError:
            print("Install waitress for Windows: pip install waitress")
            app.run(host=host, port=port, debug=False)
    else:
        try:
            import gunicorn.app.base

            class StandaloneApplication(gunicorn.app.base.BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            StandaloneApplication(app, {
                'bind': f'{host}:{port}',
                'workers': int(os.environ.get('WORKERS', 4)),
                'timeout': 120,
            }).run()
        except ImportError:
            print("Install gunicorn: pip install gunicorn")
            app.run(host=host, port=port, debug=False)
