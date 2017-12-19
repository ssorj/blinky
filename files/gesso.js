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

        request.open(method, url);

        if (handler) {
            request.addEventListener("load", handler);
        }

        return request;
    },

    minFetchInterval: 500,
    maxFetchInterval: 60 * 1000,
    fetchStates: {}, // By path

    FetchState: function () {
        return {
            currentInterval: null,
            currentTimeoutId: null,
            failedAttempts: 0,
            etag: null,
            timestamp: null
        }
    },

    getFetchState: function (path) {
        var state = gesso.fetchStates[path];

        if (!state) {
            state = new gesso.FetchState();
            gesso.fetchStates[path] = state;
        }

        return state;
    },

    fetch: function (path, dataHandler) {
        console.log("Fetching data from", path);

        var state = gesso.getFetchState(path);

        function loadHandler(event) {
            if (event.target.status === 200) {
                state.etag = event.target.getResponseHeader("ETag");
                state.failedAttempts = 0;

                dataHandler(JSON.parse(event.target.responseText));
            }

            state.timestamp = new Date().getTime();
        }

        function errorHandler(event) {
            console.log("Fetch failed");

            state.failedAttempts++;
        }

        var request = gesso.openRequest("GET", path, loadHandler);

        request.addEventListener("error", errorHandler);

        var etag = state.etag;

        if (etag) {
            request.setRequestHeader("If-None-Match", etag);
        }

        request.send();

        return state;
    },

    fetchPeriodically: function (path, dataHandler) {
        var state = gesso.getFetchState(path);

        window.clearTimeout(state.currentTimeoutId);
        state.currentInterval = gesso.minFetchInterval;

        gesso.doFetchPeriodically(path, dataHandler, state);

        return state;
    },

    doFetchPeriodically: function (path, dataHandler, state) {
        if (state.currentInterval >= gesso.maxFetchInterval) {
            window.setInterval(gesso.fetch, gesso.maxFetchInterval, path, dataHandler);
            return;
        }

        state.currentTimeoutId = window.setTimeout(gesso.doFetchPeriodically,
                                                   state.currentInterval,
                                                   path, dataHandler, state);

        state.currentInterval = Math.min(state.currentInterval * 2, gesso.maxFetchInterval);

        gesso.fetch(path, dataHandler);
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
