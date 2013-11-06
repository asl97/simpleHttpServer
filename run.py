"""
simpleHttpServer runner.
"""

from http_server.server import run
from config import HOST
from config import PORT
from config import setup_logging

def Log(string): print string

if __name__ == '__main__':
    setup_logging()

    try:
        run(host=HOST, port=PORT)
    except KeyboardInterrupt:
        Log('simpleHttpServer stopped')
