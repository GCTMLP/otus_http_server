import socket
import os
import threading
from datetime import datetime
import mimetypes
import magic
from pathlib import Path
import re
import urllib.parse
from optparse import OptionParser

SOCKET_TIMEOUT = 1000
RECONNECT_MAX_ATTEMPTS = 3
RECONNECT_DELAY = 3
MAX_LINE = 100
MAX_HEADERS = 10
STATUS_REASON = {
    200: "OK",
    403: "Forbidden",
    404: "Not Found",
    405: "MethodNotAllowed"
}

CONTENT_TYPES= {
    ".txt": "text/plain",
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".swf": "application/x-shockwave-flash",
}


class MyHTTPServer:
    def __init__(self, host, port, workers, 
                socket_timeout=SOCKET_TIMEOUT,
                reconnect_max_attempts=RECONNECT_MAX_ATTEMPTS,
                reconnect_delay=RECONNECT_DELAY):
        self._host = host
        self._port = port
        self.workers = workers
        self.socket_timeout = socket_timeout
        self.reconnect_delay = reconnect_delay
        self.reconnect_max_attempts = reconnect_max_attempts
        self._socket = None


    def connect(self):
        """
        Метод устанавливки соединения, создает сокет и ждет подключений клиентов,
        масштабируется на несколько воркеров (задается параметром командной строки)
        """
        try:
            if self._socket:
                self._socket.close()
                self._socket = socket.socket()
            else:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            self._socket.settimeout(self.socket_timeout)
            self._socket.bind((self._host, self._port))
            self._socket.listen()
            for i in range (self.workers):
                try:
                    client_handler = threading.Thread(
                                    target=self.wait_connection,)
                    client_handler.start()
                except Exception as e:
                    raise Exception(e)
        except socket.error as e:
            raise Exception(e)


    def wait_connection(self):
        """
        Метод, в котором принимается соединение от клиента,
        а также вызываются методы для обработки запроса и создания ответа 
        """
        while True:
            conn, address = self._socket.accept()
            # Обрабатываем запрос
            method, target, ver, headers = self.read_request(conn)
            # Генерируем ответ
            resp = self.make_response(method, target, ver, headers)
            # Отвечаем клиенту
            self.send_response(conn, resp)
            conn.close()
      

    def read_request(self, conn):
        """
        Метод, в котором получаем запрос клиента и разбиваем его на параметры 
        (метод запроса, версию протокола, запрашиваемый ресурс 
        и остальные параметры запроса)
        """
        rfile = conn.makefile('rb')
        # Работаем с первой строкой запроса
        raw = rfile.readline(MAX_LINE + 1)
        req_line = str(raw, 'iso-8859-1')
        if not req_line:
            raise Exception("Empty request")
        req_line = req_line.rstrip('\r\n')
        # Разделяем регуляркой на метод, версию протокола и запрашиваемый ресурс
        method, ver = re.split(r' /[a-zA-z \.\d%\/-]*\.?[a-z\/]*[ ?]*[\S]* ', 
                                req_line)
        target = re.findall(r' (/[a-zA-z \.\d%\/-]*\.?[a-z\/]*)[ ?]*[\S]* ', 
                                req_line)[0].lstrip().rstrip()
        target = urllib.parse.unquote_plus(target, encoding='utf-8',
                          errors='replace')
        # Работаем с остальными строками запроса, разбиваем 
        # на название парметра запроса и его значение
        headers = {}
        while True:
            raw = rfile.readline(MAX_LINE + 1)
            if raw in (b'\r\n', b'\n', b'', b'\r\n\r\n'):
                break
            key, value = raw.decode('iso-8859-1').split(':',1)
            headers[key] = value
        return method, target, ver, headers


    def make_response(self, method, target, ver, headers):
        """
        Метод, в котором создается ответ на запрос
        parameters: 
            - method - метод запроса
            - target - запрашиваемый ресурс
            - ver - версию протокола
            - headers - словарь остальных параметров запроса
        """
        status = 200
        headers = {}
        headers['Connectoin'] = "keep alive"
        headers['Server'] = "My_Super_Server"
        now = datetime.now()
        headers['Date'] = now.strftime("%m/%d/%Y, %H:%M:%S")
        if method not in ['GET', 'HEAD'] or ver != 'HTTP/1.1':
            status = 405
            resp = Response(status, STATUS_REASON[status], headers)
            return resp
        file_path = opts.doc_root+target
        # если в запрашивамом ресурсе клиент пытаеься выйти из директории проекта
        # (методом \..\..\..\)
        if re.findall(r'\/\.\.\/', target):
            status = 404
            resp = Response(status, STATUS_REASON[status], headers)
            return resp
        # Если запрашивается директория - возвращаем файл index.html
        if Path(file_path).is_dir():
            file_path+='index.html'
        else:
            # Если после запрашиваемого файла клиент поставил /
            if target[len(target)-1] == '/':
                status = 404
                resp = Response(status, STATUS_REASON[status], headers)
                return resp
        # Считываем данные из запрашиваемого файла
        try:
            file = open(file_path, 'rb')
        except:
            status = 404
            resp = Response(status, STATUS_REASON[status], headers)
            return resp
        data = b''
        for line in file:
            data+=line
            data+=b'\n'
        # Считаем размер файла, а также определяем его тип
        headers['Content-Length'] = os.stat(file_path).st_size
        mime = magic.Magic(mime=True)
        file_type = Path(file_path).suffix
        headers['Content-Type'] = CONTENT_TYPES[file_type]
        if method == "GET":
            resp = Response(status, STATUS_REASON[status], headers, data)
        if method == "HEAD":
            resp = Response(status, STATUS_REASON[status], headers)
        return resp


    def send_response(self, conn, resp):
        """
        Метод, в котором отправляем запрос
        parameters: 
            - conn - коннектор подключения клиента
            - resp - объект класса Response (сформарованный ответ клиенту)
        """
        wfile = conn.makefile('wb')
        status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
        wfile.write(status_line.encode('iso-8859-1'))
        if resp.headers:
            for key, value in resp.headers.items():
                header_line = f'{key}: {value}\r\n'
                wfile.write(header_line.encode('iso-8859-1'))
        wfile.write(b'\r\n')
        if resp.body:
            wfile.write(resp.body)
        wfile.flush()
        wfile.close()


class Response():
    def __init__(self, status, reason, headers=None, body=None):
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-l", "--host", action="store", default='localhost')
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-r", "--doc_root", action="store", default="")
    op.add_option("-u", "--url", action="store", default='localhost')
    op.add_option("-w", "--workers", action="store", default=1)
    (opts, args) = op.parse_args()
    serv = MyHTTPServer(opts.host, opts.port, opts.workers)
    try:
        serv.connect()
    except KeyboardInterrupt:
        pass