# otus_http_server
Веб-сервер частично реализующий протокол HTTP
Веб-сервер умеет:
  - Масштабироваться на несколько worker'ов (реализовано на thread`s)
  - Числов worker'ов задается аргументом командной строки -w
  - Отвечать 200, 403 или 404 на GET-запросы и HEAD-запросы
  - Отвечать 405 на прочие запросы
  - Возвращать файлы по произвольному пути в DOCUMENT_ROOT.
  - Вызов /file.html возвращать содердимое DOCUMENT_ROOT/file.html
  - задавать DOCUMENT_ROOT аргументом командной строки -r
  - Возвращать index.html как индекс директории
  - Возвращать DOCUMENT_ROOT/directory/index.html при вызове /directory/
  - Отвечать следующими заголовками для успешных GET-запросов: Date, Server, Content-Length, Content-Type, Connection
  - Корректный Content-Type для: .html, .css, .js, .jpg, .jpeg, .png, .gif, .swf
  - Понимать пробелы и %XX в именах файлов
