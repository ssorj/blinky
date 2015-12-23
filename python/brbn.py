
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import datetime as _datetime
import functools as _functools
import hashlib as _hashlib
import logging as _logging
import os as _os
import pprint as _pprint
import re as _re
import sched as _sched
import sys as _sys
import threading as _threading
import time as _time
import traceback as _traceback
import urllib as _urllib
import uuid as _uuid

from tornado.httpserver import HTTPServer as _HTTPServer
from tornado.ioloop import IOLoop as _IOLoop
from tornado.wsgi import WSGIContainer as _WSGIContainer
from urllib.parse import quote_plus as _url_escape
from urllib.parse import unquote_plus as _url_unescape
from xml.sax.saxutils import escape as _xml_escape
from xml.sax.saxutils import unescape as _xml_unescape

_log = _logging.getLogger("brbn")

_xhtml = "application/xhtml+xml; charset=utf-8"
_text = "text/plain"

_content_types_by_extension = {
    ".css": "text/css",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".html": _xhtml,
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "application/javascript",
    ".svg": "image/svg+xml",
    ".txt": _text,
    ".woff": "application/font-woff",
}

_page_template = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <link rel="stylesheet" href="/site.css" type="text/css"/>
    <link rel="icon" href="" type="image/png"/>
    <script src="/site.js" type="application/javascript" defer="defer"></script>
  </head>
  <body>
    <div id="-head">
      <div id="-head-content">
        {head}
      </div>
    </div>
    <div id="-body">
      <div id="-body-content">
        {body}
      </div>
    </div>
    <div id="-foot">
      <div id="-foot-content">
        {foot}
      </div>
    </div>
  </body>
</html>"""

_head_template = """{global_navigation}
{path_navigation}"""

_foot_template = """ """

def url_escape(string):
    if string is None:
        return

    return _url_escape(string)

def url_unescape(string):
    if string is None:
        return

    return _url_unescape(string)

_extra_entities = {
    '"': "&quot;",
    "'": "&#x27;",
    "/": "&#x2F;",
}

def xml(meth):
    meth._xml = True
    return meth
    
def xml_escape(string):
    if string is None:
        return

    return _xml_escape(string, _extra_entities)

def xml_unescape(string):
    if string is None:
        return

    return _xml_unescape(string)

class Error(Exception):
    pass

class Application:
    def __init__(self, home=None):
        self._home = home
        self._brbn_home = None

        self._pages_by_path = dict()
        self._files_by_path = dict()

        self._root_page = None
        self._error_page = _ErrorPage(self)

        self._sessions_by_id = dict()
        self._session_expire_thread = _SessionExpireThread(self)

    def __repr__(self):
        return _format_repr(self, self.home)

    @property
    def spec(self):
        return "{}:{}".format(self.__module__, self.__class__.__name__)

    @property
    def home(self):
        return self._home

    @property
    def brbn_home(self):
        return self._brbn_home

    @property
    def pages_by_path(self):
        return self._pages_by_path

    @property
    def files_by_path(self):
        return self._files_by_path

    @property
    def root_page(self):
        return self._root_page

    @root_page.setter
    def root_page(self, page):
        assert isinstance(page, Page), page
        assert page.path == "/"

        self._root_page = page
    
    def load(self):
        _log.info("Loading {}".format(self))

        if self.brbn_home is not None:
            brbn_files_dir = _os.path.join(self.brbn_home, "files")
            self._load_files(brbn_files_dir)

        if self.home is not None:
            app_files_dir = _os.path.join(self.home, "files")
            self._load_files(app_files_dir)
        
    def _load_files(self, files_dir):
        if not _os.path.isdir(files_dir):
            return

        _log.debug("Loading files under {}".format(files_dir))
        
        for root, dirs, files in _os.walk(files_dir):
            for name in files:
                path = _os.path.join(root, name)

                with open(path, "rb") as file:
                    content = file.read()

                path = path[len(files_dir):]

                File(self, path, content)

    def init(self):
        _log.info("Initializing {}".format(self))
        
        for path, page in sorted(self.pages_by_path.items()):
            page.init()

    def start(self):
        _log.info("Starting {}".format(self))
        
        self._session_expire_thread.start()

    def __call__(self, env, start_response):
        request = Request(self, env, start_response)

        try:
            return self._call_with_request(request)
        except Exception as e:
            _log.exception("Unexpected error")
            return request.respond_unexpected_error(e)

    def _call_with_request(self, request):
        try:
            request.load()
        except _RequestError as e:
            _log.exception("Request error")
            return request.respond_error(e)

        _log.debug("Receiving {}".format(request))

        csp = "default-src: 'self'"
        sts = "max-age=31536000"

        request.add_response_header("Content-Security-Policy", csp)
        request.add_response_header("Strict-Transport-Security", sts)
    
        try:
            return self.receive_request(request)
        except _RequestError as e:
            _log.exception("Request error")
            return request.respond_error(e)
        
    def receive_request(self, request):
        path = request.path

        try:
            page = self.pages_by_path[path]
        except KeyError:
            return self.send_response(request)

        return page.receive_request(request)

    def send_response(self, request):
        return self.send_file(request)
    
    def send_file(self, request, path=None):
        if path is None:
            path = request.path
        
        if path == "/":
            path = "/index.html"

        try:
            file = self.files_by_path[path]
        except KeyError:
            return request.respond_not_found()

        if not request.is_modified(file.etag):
            return request.respond_not_modified()
            
        request.add_response_header("ETag", file.etag)
        request.add_response_header("Cache-Control", "max-age=120")

        return request.respond("200 OK", file.content, file.content_type)

class Request:
    def __init__(self, app, env, start_response):
        self._app = app
        self._env = env
        self._start_response = start_response

        self._parameters_by_name = None
        self._response_headers = list()

        self._session = None
        self._object = None

    def __repr__(self):
        return _format_repr(self, self.path)

    @property
    def app(self):
        return self._app

    @property
    def env(self):
        return self._env

    @property
    def parameters_by_name(self):
        return self._parameters_by_name

    @property
    def response_headers(self):
        return self._response_headers

    @property
    def session(self):
        return self._session

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, obj):
        self._object = obj

    def load(self):
        self._parameters_by_name = self._parse_query_string()

        session_id = self._parse_session_cookie()

        if session_id is None:
            self._session = Session(self.app)
        else:
            try:
                self._session = self.app._sessions_by_id[session_id]
            except KeyError:
                self._session = Session(self.app)

        self.session._touched = _datetime.datetime.now()

    def _parse_query_string(self):
        query_string = None

        if self.method == "GET":
            query_string = self.env["QUERY_STRING"]
        elif self.method == "POST":
            content_type = self.env["CONTENT_TYPE"]

            assert content_type == "application/x-www-form-urlencoded"

            length = int(self.env["CONTENT_LENGTH"])
            query_string = self.env["wsgi.input"].read(length)

        if not query_string:
            return {}

        try:
            return _urllib.parse.parse_qs(query_string, False, True)
        except ValueError:
            raise _RequestError("I can't parse the query string '{}'".format
                                (query_string))

    def _parse_session_cookie(self):
        try:
            cookie_string = self.env["HTTP_COOKIE"]
        except KeyError:
            return

        for crumb in cookie_string.split(";"):
            name, value = crumb.split("=", 1)
            name = name.strip()
            
            if name == "session":
                return value.strip()
        
    @property
    def method(self):
        return self.env["REQUEST_METHOD"]

    @property
    def path(self):
        return self.env["PATH_INFO"]

    def get(self, name):
        try:
            return self.parameters_by_name[name][0]
        except KeyError:
            raise _RequestError("Parameter '{}' is missing".format(name))
        except IndexError:
            raise _RequestError("Parameter '{}' has no values".format(name))
        
    def is_modified(self, server_etag):
        client_etag = self.env.get("HTTP_IF_NONE_MATCH")

        if client_etag is not None and server_etag is not None:
            return client_etag != server_etag

        return True

    def add_response_header(self, name, value):
        self.response_headers.append((name, str(value)))
    
    def respond(self, status, content=None, content_type=None):
        if self.session is not None:
            # value = "session={}; Path=/; Secure; HttpOnly".format(self.session._id)
            value = "session={}; Path=/; HttpOnly".format(self.session._id)
            self.add_response_header("Set-Cookie", value)
        
        if content is None:
            self.add_response_header("Content-Length", 0)
            self._start_response(status, self.response_headers)
            return (b"",)

        if isinstance(content, str):
            content = content.encode("utf-8")
        
        assert isinstance(content, bytes), type(content)
        assert content_type is not None

        content_length = len(content)

        self.add_response_header("Content-Length", content_length)
        self.add_response_header("Content-Type", content_type)

        self._start_response(status, self.response_headers)

        return (content,)

    def respond_ok(self, content, content_type):
        return self.respond("200 OK", content, content_type)
    
    def respond_redirect(self, location):
        self.add_response_header("Location", location)

        return self.respond("303 See Other")

    def respond_not_modified(self):
        return self.respond("304 Not Modified")
    
    def respond_not_found(self):
        self.error_status = "404 Not Found"
        self.error_title = "Not found!"
        self.error_message = "I can't find a page or file for path '{}'" \
            .format(self.path)

        return self.app._error_page.send_response(self)
        
    def respond_error(self, error):
        self.error_status = "500 Internal Server Error"
        self.error_title = "Error!"
        self.error_message = str(error)
        
        return self.app._error_page.send_response(self)

    def respond_unexpected_error(self, exception):
        try:
            return self._do_respond_unexpected_error(exception)
        except:
            return self._respond_unexpected_error_fallback()
        
    def _do_respond_unexpected_error(self, exception):
        self.error_status = "500 Internal Server Error"
        self.error_title = "Error!"
        self.error_message = "Yikes! An unexpected problem: {}" \
            .format(str(exception))
        
        return self.app._error_page.send_response(self)

    def _respond_unexpected_error_fallback(self):
        content = _traceback.format_exc()
        content_type = "text/plain"
        
        return self.respond("500 Internal Server Error", content, content_type)

class _RequestError(Exception):
    pass

class File:
    def __init__(self, app, path, content):
        self._app = app
        self._path = path
        self._content = content

        name, ext = _os.path.splitext(self.path)

        self._content_type = _content_types_by_extension.get(ext, _text)
        self._etag = _hashlib.sha1(self.content).hexdigest()[:8]
        
        self.app.files_by_path[self.path] = self
        
    def __repr__(self):
        return _format_repr(self, self.path, self.etag)

    @property
    def app(self):
        return self._app

    @property
    def path(self):
        return self._path

    @property
    def content(self):
        return self._content

    @property
    def content_type(self):
        return self._content_type

    @property
    def etag(self):
        return self._etag

    def get_href(self):
        return self.path
    
    def get_link(self):
        href = self.get_href()
        return "<a href=\"{}\">{}</a>".format(href, xml_escape(self.path))

    def decode(self, encoding="utf-8", errors="strict"):
        return self.content.decode(encoding, errors)

class Page:
    def __init__(self, app, path, template=None, title=None, parent=None):
        self._app = app
        self._path = path
        self._title = title
        self._parent = parent

        name, ext = _os.path.splitext(self.path)

        self._content_type = _content_types_by_extension.get(ext, _xhtml)

        self._page_template = Template(_page_template, self)
        self._head_template = Template(_head_template, self)
        self._body_template = None
        self._foot_template = Template(_foot_template, self)

        if template is not None:
            self._body_template = Template(template, self)

        self.app.pages_by_path[self.path] = self
    
    def __repr__(self):
        return _format_repr(self, self.path)

    @property
    def app(self):
        return self._app

    @property
    def title(self):
        return self._title

    @property
    def parent(self):
        return self._parent

    @property
    def path(self):
        return self._path

    @property
    def content_type(self):
        return self._content_type

    def init(self):
        _log.debug("Initializing {}".format(self))

        if self.parent is None and self.path != "/":
            self._parent = self.app.root_page

    def receive_request(self, request):
        return self.send_response(request)

    def get_href(self, **params):
        if not params:
            return self.path
        
        query_vars = list()

        for name, value in sorted(params.items()):
            query_vars.append("{}={}".format(url_escape(name), url_escape(value)))

        query_vars = ";".join(query_vars)

        return "{}?{}".format(self.path, query_vars)

    def get_link(self, **params):
        title = self.title
        href = self.get_href(**params)

        return "<a href=\"{}\">{}</a>".format(href, xml_escape(title))
        
    @xml
    def render(self, request):
        return self._page_template.render(request)

    @xml
    def render_head(self, request):
        return self._head_template.render(request)

    @xml
    def render_body(self, request):
        if self._body_template is not None:
            return self._body_template.render(request)

    @xml
    def render_foot(self, request):
        return self._foot_template.render(request)

    def render_title(self, request):
        return self.title

    @xml
    def render_path_navigation(self, request):
        links = list()
        page = self

        links.append(page.render_title(request))
        page = page.parent

        while page is not None:
            links.append(page.get_link())
            page = page.parent

        items = ["<li>{}</li>".format(x) for x in reversed(links)]
        items = "".join(items)
        
        return "<ul id=\"-path-navigation\">{}</ul>".format(items)
    
    @xml
    def render_global_navigation(self, request):
        return "<ul id=\"-global-navigation\"></ul>"

    def send_response(self, request):
        content = self.render(request)
        return request.respond_ok(content, self.content_type)

class Template:
    @staticmethod
    def _render_escaped(func):
        @_functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if result is None:
                return ""

            return xml_escape(result)

        return wrapper        
    
    @staticmethod
    def _render_unescaped(func):
        @_functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if result is None:
                return ""

            return result

        return wrapper

    def __init__(self, string, object):
        self._string = string
        self._object = object
        self._elements = self._bind()

    def __repr__(self):
        return _format_repr(self)
    
    def _bind(self):
        elems = list()
        tokens = _re.split("({.+?})", self._string)

        for token in tokens:
            if token.startswith("{") and token.endswith("}"):
                meth_name = "render_{}".format(token[1:-1])
                meth = getattr(self._object, meth_name, None)

                if meth is not None:
                    assert callable(meth), meth_name

                    if hasattr(meth, "_xml"):
                        meth = self._render_unescaped(meth)
                    else:
                        meth = self._render_escaped(meth)

                    elems.append(meth)
                    
                    continue

            elems.append(token)

        return elems

    def render(self, request):
        out = list()

        for elem in self._elements:
            if callable(elem):
                elem = elem(request)

            out.append(elem)

        return "".join(out)

class FilePage(Page):
    def __init__(self, app, path, file_path, title=None, parent=None):
        super().__init__(app, path, title=title, parent=parent)

        self._file_path = file_path

    def init(self):
        super().init()

        file = self.app.files_by_path[self._file_path]
        self._body_template = Template(file.decode(), self)

class ObjectPage(Page):
    def receive_request(self, request):
        try:
            request.object = self.get_object(request)
        except ObjectNotFound as e:
            return request.respond_not_found()

        return self.send_response(request)

    def get_object(self, request):
        pass
    
    def get_object_name(self, request, obj):
        if hasattr(obj, "name"):
            return obj.name

    def get_object_id(self, request, obj):
        if hasattr(obj, "id"):
            return obj.id

    def get_object_href(self, request, obj):
        key = self.get_object_id(request, obj)
        return self.get_href(id=key)

    def get_object_parent(self, request, obj):
        if hasattr(obj, "parent"):
            return obj.parent

    def get_object_link(self, request, obj):
        name = self.get_object_name(request, obj)
        href = self.get_object_href(request, obj)

        return "<a href=\"{}\">{}</a>".format(href, xml_escape(name))

    def render_title(self, request):
        if request.object is not None:
            return self.get_object_name(request, request.object)

        super().render_title(request)

class ObjectNotFound(Exception):
    pass
    
class _SitePage(Page):
    template = """
    <h1>{title}</h1>
    <h2>Pages</h2>
    {pages}
    <h2>Files</h2>
    {files}
    """

    def __init__(self, app, path, title="Site info", parent=None):
        super().__init__(app, path, self.template, title=title, parent=parent)

    @xml
    def render_pages(self, request):
        items = list()
        
        for path, page in sorted(self.app.pages_by_path.items()):
            if page is self.app._error_page:
                continue
            
            items.append(page.get_link())

        items = "".join(["<li>{}</li>".format(x) for x in items])
            
        return "<ul>{}</ul>".format(items)

    @xml
    def render_files(self, request):
        items = list()
        
        for path, file in sorted(self.app.files_by_path.items()):
            items.append(file.get_link())

        items = "".join(["<li>{}</li>".format(x) for x in items])
            
        return "<ul>{}</ul>".format(items)
    
class _RequestPage(Page):
    def __init__(self, app, path):
        super().__init__(app, path, title="Request info")

        self.request_info = _RequestInfo()

    @xml
    def render_body(self, request):
        return self.request_info.render(request)

class _ErrorPage(Page):
    template = """
    <h1>{title}</h1>
    <p>{message}</p>
    <div class="hidden">{request_info}</div>
    """

    def __init__(self, app):
        super().__init__(app, "/error", self.template, title="Error!")

        self._request_info = _RequestInfo()

    def render_title(self, request):
        return request.error_title
        
    def render_message(self, request):
        return request.error_message

    @xml
    def render_request_info(self, request):
        return self._request_info.render(request)

    def send_response(self, request):
        status = request.error_status
        content = self.render(request)
        
        return request.respond(status, content, self.content_type)

class _RequestInfo(Template):
    template = """
    <h2>Traceback</h2>
    {traceback}
    <h2>Request</h2>
    {request}
    <h2>Application</h2>
    {application}
    <h2>System</h2>
    {system}
    """

    def __init__(self):
        super().__init__(self.template, self)

    def _render_attributes(self, attrs):
        lines = list()

        if isinstance(attrs, dict):
            attrs = sorted(attrs.items())

        for name, value in attrs:
            value = _pprint.pformat(value)
            value = value.replace("\n", "\n{}".format(" " * 26))

            lines.append("{:24}  {}".format(name, value))

        return "<pre>{}</pre>".format(xml_escape("\n".join(lines)))

    @xml
    def render_traceback(self, request):
        if _sys.exc_info()[1] is None:
            return "<p>None</p>"

        traceback = _traceback.format_exc()
        
        return "<pre>{}</pre>".format(xml_escape(traceback))

    @xml
    def render_request(self, request):
        attrs = (
            ("request.app", request.app),
            ("request.method", request.method),
            ("request.path", request.path),
            ("request.parameters_by_name", request.parameters_by_name),
            ("request.response_headers", request.response_headers),
            ("request.object", request.object),
        )
        
        return self._render_attributes(attrs)

    @xml
    def render_application(self, request):
        attrs = (
            ("app.spec", request.app.spec),
            ("app.home", request.app.home),
            ("app.brbn_home", request.app.brbn_home),
            ("app.files_by_path", request.app.files_by_path),
            ("app.pages_by_path", request.app.pages_by_path),
            ("app.root_page", request.app.root_page),
        )

        return self._render_attributes(attrs)

    @xml
    def render_system(self, request):
        attrs = (
            ("sys.argv", _sys.argv),
            ("sys.executable", _sys.executable),
            ("sys.path", _sys.path),
            ("sys.version", _sys.version),
            ("sys.prefix", _sys.prefix),
            ("sys.exec_prefix", _sys.exec_prefix),
            ("sys.platform", _sys.platform),
            ("sys.defaultencoding", _sys.getdefaultencoding()),
            ("sys.filesystemencoding", _sys.getfilesystemencoding()),
        )

        return self._render_attributes(attrs)

class Session:
    def __init__(self, app):
        self._app = app
        self._id = str(_uuid.uuid4())
        self._touched = _datetime.datetime.now()

        self.app._sessions_by_id[self._id] = self

    @property
    def app(self):
        return self._app

class _SessionExpireThread(_threading.Thread):
    def __init__(self, app):
        super().__init__()
        
        self.app = app
        self.daemon = True
        self.scheduler = _sched.scheduler()

    def run(self):
        self.expire_sessions()
        self.scheduler.run()

    def expire_sessions(self):
        try:
            self.do_expire_sessions()
        except:
            _log.exception("Failure expiring sessions")
            
        self.scheduler.enter(60, 1, self.expire_sessions)

    def do_expire_sessions(self):
        when = _datetime.datetime.now() - _datetime.timedelta(hours=1)
        count = 0

        for session in list(self.app._sessions_by_id.values()):
            if session._touched < when:
                del self.app._sessions_by_id[session._id]
                count += 1

        _log.debug("Expired {} client sessions".format(count))
        
class Server:
    def __init__(self, app, port=8000):
        self._app = app
        self._port = port

        self._tornado_server = _HTTPServer(_WSGIContainer(self._app))

    def __repr__(self):
        return _format_repr(self, self._app, self._port)

    def run(self):
        _log.info("Starting {}".format(self))

        try:
            self._tornado_server.listen(self._port)
        except OSError as e:
            msg = "Cannot listen on port {}: {}".format(self._port, str(e))
            raise Error(msg)

        _IOLoop.current().start()
        
def _format_repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]
    return "{}({})".format(cls, ",".join(strings))

class Hello(Application):
    template = """
    <h1>{title}</h1>
    <p>I am Brbn.</p>
    <p><a href="/nope.html">404!</a> <a href="/explode.html">500!</a></p>
    {request_info}
    """

    def __init__(self, home):
        super().__init__(home)

        self.root_page = _HelloPage(self)
        self.site_page = _SitePage(self, "/site")
        self.request_page = _RequestPage(self, "/request")
        self.explode_page = _ExplodePage(self)

class _HelloPage(FilePage):
    def __init__(self, app):
        super().__init__(app, "/", "/hello.in", title="Brbn")
       
class _ExplodePage(Page):
    def __init__(self, app):
        super().__init__(app, "/explode", title="Explode!")

    def render_body(self, request):
        raise Exception("Exploding!")
