"""
simpleHttpServer request handler.
"""

import socket
import urllib
import cgi
import os
from file_system.helper import get_file
from http_protocol.request import parse_http_request
from http_protocol.response import HttpResponse
from thread_pool.pool import ThreadPool
from config import RECV_BUFSIZ
from config import STATIC_FILES_DIR
from config import THREAD_POOL_SIZE
from config import SOCKET_BACKLOG_SIZE

def Log(string): print string


def handle_request(clientsock, addr):

    data = clientsock.recv(RECV_BUFSIZ)

    #Log('Request received: %s' % data)

    request = parse_http_request(data)

    path = STATIC_FILES_DIR + clean_path(request.request_uri)

    # check if path is dir (copy from the SimpleHttpServer)
    if os.path.isdir(path):
        if not path.endswith('/'):
            # redirect browser - doing basically what apache does
            response = HttpResponse(protocol=request.protocol, status_code=301)
            response.headers['Location'] = path + "/"
            Log('%s GET "%s" %s %s %s' %
                (addr[0], request.request_uri, request.protocol, request.get_range(), response.status_code))
            response.write_to(clientsock)
            clientsock.close()
            return None
        for index in "index.html", "index.htm":
            index = os.path.join(path, index)
            if os.path.exists(index):
                path = index
                break
        else:
            # quick and dirty but it works :P (also copy from SimpleHttpServer)
            try:
                list = os.listdir(path)
            except os.error:
                response = HttpResponse(protocol=request.protocol, status_code=404)
                response.headers['Content-type'] = 'text/plain'
                response.content = 'No permission to list directory'
                Log('%s GET "%s" %s %s %s' %
                    (addr[0], request.request_uri, request.protocol, request.get_range(), response.status_code))
                response.write_to(clientsock)
                clientsock.close()
                return None
            list.sort(key=lambda a: a.lower())
            f = str()
            displaypath = cgi.escape(urllib.unquote(path))
            f += '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">'
            f += "<html>\n<title>Directory listing for %s</title>\n" % displaypath
            f +="<body>\n<h2>Directory listing for %s</h2>\n" % displaypath
            f += "<hr>\n<ul>\n"
            for name in list:
                fullname = os.path.join(path, name)
                displayname = linkname = name
                # Append / for directories or @ for symbolic links
                if os.path.isdir(fullname):
                    displayname = name + "/"
                    linkname = name + "/"
                if os.path.islink(fullname):
                    displayname = name + "@"
                    # Note: a link to a directory displays with @ and links with /
                f += '<li><a href="%s">%s</a>\n' % (urllib.quote(linkname), cgi.escape(displayname))
            f += "</ul>\n<hr>\n</body>\n</html>\n"
            response = HttpResponse(protocol=request.protocol, status_code=200)
            response.headers['Content-type'] = 'text/html'
            response.headers['Content-Length'] = len(f)
            response.headers['Accept-Ranges'] = 'bytes'
            response.content = f
            Log('%s GET "%s" %s %s %s' %
                (addr[0], request.request_uri, request.protocol, request.get_range(), response.status_code))
            response.write_to(clientsock)
            clientsock.close()
            return None

    file = get_file(path)

    if file.exists and request.is_range_requested():
        response = HttpResponse(protocol=request.protocol, status_code=206,
                                range=request.get_range())
        response.file = file

    elif file.exists:
        response = HttpResponse(protocol=request.protocol, status_code=200)
        response.file = file

    else:
        response = HttpResponse(protocol=request.protocol, status_code=404)
        response.headers['Content-type'] = 'text/plain'
        response.content = 'This file does not exist!'

    Log('%s GET "%s" %s %s %s' %
        (addr[0], request.request_uri, request.protocol, request.get_range(), response.status_code))

    response.write_to(clientsock)
    clientsock.close()

def clean_path(path):
    """ remove query parameters and decode html """
    # abandon query parameters
    path = path.split('?',1)[0]
    path = path.split('#',1)[0]
    path = urllib.unquote(path)
    return path

def run(host, port):
    address = (host, port)
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversock.bind(address)
    serversock.listen(SOCKET_BACKLOG_SIZE)

    Log('simpleHttpServer started on %s:%s' % (host, port))

    pool = ThreadPool(THREAD_POOL_SIZE)

    while True:
        #Log('Waiting for connection...')

        clientsock, addr = serversock.accept()
        #Log('Connected from: %s' % addr)

        pool.add_task(handle_request, clientsock, addr)

