/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

"use strict";

var $ = document.querySelector.bind(document);
var $$ = document.querySelectorAll.bind(document);

Element.prototype.$ = function () {
  return this.querySelector.apply(this, arguments);
};

Element.prototype.$$ = function () {
  return this.querySelectorAll.apply(this, arguments);
};

var gesso = {
    openRequest: function (method, url, handler) {
        var request = new XMLHttpRequest();

        request.onreadystatechange = function () {
            if (request.readyState === 4) {
                handler(request);
            }
        };

        request.open(method, url);

        return request;
    },

    sendRequest: function (method, url, handler) {
        var request = gesso.openRequest(method, url, handler);

        request.send(null);

        return request;
    },

    fetchDataAttributes: {
        minInterval: 500,
        maxInterval: 60 * 1000,
        currentInterval: null,
        currentTimeoutId: null,
        etags: {}
    },

    fetchData: function (path, handler) {
        console.log("Fetching data from", path);

        var attrs = gesso.fetchDataAttributes;

        var request = gesso.openRequest("GET", path, function (request) {
            if (request.status === 200) {
                attrs.etags[path] = request.getResponseHeader("ETag");

                handler(JSON.parse(request.responseText));
            }
        });

        var etag = attrs.etags[path];

        if (etag) {
            request.setRequestHeader("If-None-Match", etag);
        }

        request.send(null);
    },

    fetchDataPeriodically: function (path, handler) {
        var attrs = gesso.fetchDataAttributes;

        window.clearTimeout(attrs.currentTimeoutId);
        attrs.currentInterval = attrs.minInterval;

        gesso.doFetchDataPeriodically(path, handler);
    },

    doFetchDataPeriodically: function (path, handler) {
        var attrs = gesso.fetchDataAttributes;

        if (attrs.currentInterval >= attrs.maxInterval) {
            window.setInterval(gesso.fetchData, attrs.maxInterval, path, handler);
            return;
        }

        attrs.currentTimeoutId = window.setTimeout(gesso.doFetchDataPeriodically,
                                                   attrs.currentInterval,
                                                   path, handler);

        attrs.currentInterval = Math.min(attrs.currentInterval * 2, attrs.maxInterval);

        gesso.fetchData(path, handler);
    },

    parseQueryString: function (str) {
        if (str.startsWith("?")) {
            str = str.slice(1);
        }

        var qvars = str.split(/[&;]/);
        var obj = {};

        for (var i = 0; i < qvars.length; i++) {
            var [name, value] = qvars[i].split("=", 2);

            name = decodeURIComponent(name);
            value = decodeURIComponent(value);

            obj[name] = value;
        }

        return obj;
    },

    emitQueryString: function (obj) {
        var tokens = [];

        for (var name in obj) {
            if (!obj.hasOwnProperty(name)) {
                continue;
            }

            var value = obj[name];

            name = decodeURIComponent(name);
            value = decodeURIComponent(value);

            tokens.push(name + "=" + value);
        }

        return tokens.join(";");
    },

    createElement: function (parent, tag, text) {
        var elem = document.createElement(tag);

        parent.appendChild(elem);

        if (text) {
            gesso.createText(elem, text);
        }

        return elem;
    },

    createText: function (parent, text) {
        var node = document.createTextNode(text);

        parent.appendChild(node);

        return node;
    },

    createDiv: function (parent, clazz, text) {
        var elem = gesso.createElement(parent, "div", text);

        if (clazz) {
            elem.setAttribute("class", clazz);
        }

        return elem;
    },

    createLink: function (parent, href, text) {
        var elem = gesso.createElement(parent, "a", text);

        if (href) {
            elem.setAttribute("href", href);
        }

        return elem;
    }
}
