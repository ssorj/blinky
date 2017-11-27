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

Element.prototype.$ = function() {
  return this.querySelector.apply(this, arguments);
};

Element.prototype.$$ = function() {
  return this.querySelectorAll.apply(this, arguments);
};

var blinky = {
    openGetRequest: function(url, handler) {
        var request = new XMLHttpRequest();

        request.onreadystatechange = function() {
            if (request.readyState === 4) {
                handler(request);
            }
        };

        request.open("GET", url);

        return request;
    },

    sendGetRequest: function(url, handler) {
        var request = blinky.openGetRequest(url, function(request) {
            handler(request);
        });

        request.send(null);

        return request;
    },

    parseQueryString: function(str) {
        if (str.startsWith("?")) { // XXX compat
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

    emitQueryString: function(obj) {
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

    createElem: function(parent, tag, text) {
        var elem = document.createElement(tag);

        parent.appendChild(elem);

        if (text) {
            blinky.createText(elem, text);
        }

        return elem;
    },

    createText: function(parent, text) {
        var node = document.createTextNode(text);
        parent.appendChild(node);
        return node;
    },

    createDiv: function(parent, class_, text) {
        var elem = blinky.createElem(parent, "div", text);

        if (class_) {
            elem.setAttribute("class", class_);
        }

        return elem;
    },

    createLink: function(parent, href, text) {
        var elem = blinky.createElem(parent, "a", text);

        if (href) {
            elem.setAttribute("href", href);
        }

        return elem;
    },

    formatDuration: function(seconds) {
        if (seconds < 0) {
            seconds = 0;
        }

        var minutes = Math.floor(seconds / 60);
        var hours = Math.floor(seconds / 3600);
        var days = Math.floor(seconds / 86400);
        var weeks = Math.floor(seconds / 432000);

        if (weeks >= 2) {
            return weeks + "w";
        }

        if (days >= 2) {
            return days + "d";
        }

        if (hours >= 1) {
            return hours + "h";
        }

        if (minutes >= 1) {
            return minutes + "m";
        }

        return Math.floor(seconds) + "s";
    },

    createHeader: function(parent, state) {
        var elem = blinky.createDiv(parent, "header");

        blinky.createViewSelector(elem, state);
        blinky.createElem(elem, "h1", state.data.title);
        blinky.createCategorySelector(elem, state);

        return elem;
    },

    createBody: function(parent, state) {
        var elem = blinky.createDiv(parent, "body");

        var view = state.query.view;

        if (view === "panel") {
            blinky.createPanel(elem, state);
        } else if (view === "table") {
            blinky.createTable(elem, state);
        } else {
            // XXX Error output
        }

        return elem;
    },

    createFooter: function(parent, state) {
        var elem = blinky.createDiv(parent, "footer");
        var time = new Date().toLocaleString();

        var status = blinky.createElem(elem, "span", time + " (200 OK)"); // XXX a fib
        status.setAttribute("id", "request-status");

        blinky.createText(elem, " \u2022 ");

        var link = blinky.createLink(elem, "pretty-data.html?url=/data.json", "Data");
        link.setAttribute("target", "blinky");

        return elem;
    },

    createViewSelector: function(parent, state) {
        var elem = blinky.createDiv(parent, "view-selector");

        blinky.createViewSelectorLink(elem, state, "Panel", "panel");
        blinky.createViewSelectorLink(elem, state, "Table", "table");

        return elem;
    },

    createViewSelectorLink: function(parent, state, text, view) {
        var query = Object.assign({}, state.query); // XXX compat
        query.view = view;

        var elem = blinky.createStateLink(parent, state, text, query);

        if (view === state.query.view) {
            elem.classList.add("selected");
        }

        return elem;
    },

    createCategorySelector: function(parent, state) {
        var elem = blinky.createDiv(parent, "category-selector");

        blinky.createCategorySelectorLink(elem, state, "All", "all");

        var categories = state.data.categories;

        for (var categoryId in categories) {
            var category = categories[categoryId];
            blinky.createCategorySelectorLink(elem, state, category.name, category.key);
        }

        return elem;
    },

    createCategorySelectorLink: function(parent, state, text, category) {
        var query = Object.assign({}, state.query); // XXX compat
        query.category = category;

        var elem = blinky.createStateLink(parent, state, text, query);

        if (category === state.query.category) {
            elem.classList.add("selected");
        }

        return elem;
    },

    // XXX name kinda sucks
    createStateLink: function(parent, state, text, query) {
        var href = "?" + blinky.emitQueryString(query);
        var elem = blinky.createLink(parent, href, text);

        elem.addEventListener("click", function(event) {
            event.preventDefault();

            state.query = query;
            window.history.pushState(state.query, null, event.target.href);

            blinky.fireStateChangeEvent();
        });

        return elem;
    },

    createObjectLink: function(parent, obj) {
        var elem = blinky.createLink(parent, obj.html_url, obj.name);
        elem.setAttribute("target", "blinky");
        return elem;
    },

    createObjectDataLink: function(parent, obj) {
        var url = "pretty-data.html?url=" + encodeURIComponent(obj.data_url);
        var elem = blinky.createLink(parent, url, obj.name);

        elem.setAttribute("target", "blinky");

        return elem;
    },

    createResultTestsLink: function(parent, result) {
        if (!result.tests_url) {
            var elem = blinky.createElem(parent, "span", "Tests");
            elem.setAttribute("class", "disabled");
            return elem;
        }

        var elem = blinky.createLink(parent, result.tests_url, "Tests");
        elem.setAttribute("target", "blinky");

        return elem;
    },

    createPanel: function(parent, state) {
        var elem = blinky.createDiv(parent, "panel");

        var groups = state.data.groups;
        var categories = state.data.categories;
        var jobs = state.data.jobs;

        var selection = state.query.category;

        for (var groupId in groups) {
            var group = groups[groupId];
            var category = categories[group.category_id];

            if (selection !== "all" && selection !== category.key) {
                continue;
            }

            var groupElem = blinky.createDiv(elem, "group");

            blinky.createElem(groupElem, "h2", group.name);

            var jobContainer = blinky.createDiv(groupElem, "job-container");
            var jobIds = group.job_ids;

            for (var j = 0; j < jobIds.length; j++) {
                var job = jobs[jobIds[j]];
                blinky.createJob(jobContainer, state, job);
            }
        }

        return elem;
    },

    createJob: function(parent, state, job) {
        var component = state.data.components[job.component_id];
        var environment = state.data.environments[job.environment_id];
        var currResult = job.current_result;
        var prevResult = job.previous_result;

        var elem = blinky.createDiv(parent, "job");

        var summary = blinky.createLink(elem, job.html_url);
        summary.setAttribute("target", "blinky");
        summary.setAttribute("class", "job-summary");

        blinky.createDiv(summary, "summary-component", component.name);
        blinky.createDiv(summary, "summary-job", job.name);
        blinky.createDiv(summary, "summary-environment", environment.name);

        if (!currResult) {
            elem.classList.add("no-data");
            return elem;
        }

        elem.setAttribute("href", currResult.html_url);

        if (currResult.status === "PASSED") {
            elem.classList.add("passed");
        } else if (currResult.status === "FAILED") {
            elem.classList.add("failed");

            if (prevResult && prevResult.status === "PASSED") {
                elem.classList.add("blinky");
            }
        }

        if (job.update_failures >= 10) {
            elem.classList.add("stale-data");
        }

        var secondsNow = new Date().getTime() / 1000; // XXX use a shared snapshot time?
        var secondsAgo = secondsNow - currResult.start_time;

        blinky.createDiv(summary, "summary-start-time", blinky.formatDuration(secondsAgo));
        blinky.createJobDetail(elem, state, job);

        return elem;
    },

    createJobDetail: function(parent, state, job) {
        var elem = blinky.createDiv(parent, "job-detail");

        var component = state.data.components[job.component_id];
        var environment = state.data.environments[job.environment_id];
        var agent = state.data.agents[job.agent_id];
        var currResult = job.current_result;
        var prevResult = job.previous_result;

        var table = blinky.createElem(elem, "table");
        var tbody = blinky.createElem(table, "tbody");
        var td = null;
        var link = null;

        blinky.createJobDetailField(tbody, "Component", component.name);
        blinky.createJobDetailField(tbody, "Environment", environment.name);

        td = blinky.createJobDetailField(tbody, "Agent", null);
        blinky.createObjectLink(td, agent);

        td = blinky.createJobDetailField(tbody, "Job", null);
        blinky.createObjectLink(td, job);

        if (currResult) {
            var duration = blinky.formatDuration(currResult.duration);
            var secondsNow = new Date().getTime() / 1000; // XXX shared timestamp
            var secondsAgo = secondsNow - currResult.start_time;
            var timeAgo = blinky.formatDuration(secondsAgo) + " ago";

            td = blinky.createJobDetailField(tbody, "Number", null);
            link = blinky.createObjectLink(td, currResult);
            link.textContent = currResult.number;

            blinky.createJobDetailField(tbody, "Time", timeAgo);
            blinky.createJobDetailField(tbody, "Duration", duration);
            blinky.createJobDetailField(tbody, "Status", currResult.status);

            if (prevResult) {
                blinky.createJobDetailField(tbody, "Prev status", prevResult.status);
            }

            td = blinky.createJobDetailField(tbody, "Links", null);

            link = blinky.createObjectDataLink(td, currResult)
            link.textContent = "Data";

            blinky.createText(td, ", ");

            link = blinky.createResultTestsLink(td, currResult);
        }

        return elem;
    },

    createJobDetailField: function(parent, name, text) {
        var tr = blinky.createElem(parent, "tr");
        var th = blinky.createElem(tr, "th", name);
        var td = blinky.createElem(tr, "td", text);

        return td;
    },

    createTable: function(parent, state) {
        var elem = blinky.createElem(parent, "table");

        elem.classList.add("jobs");
        elem.setAttribute("data-sortable", "data-sortable");

        var thead = blinky.createElem(elem, "thead");
        var tr = blinky.createElem(thead, "tr");

        blinky.createElem(tr, "th", "Component");
        blinky.createElem(tr, "th", "Environment");
        blinky.createElem(tr, "th", "Job");
        blinky.createElem(tr, "th", "Agent");
        blinky.createElem(tr, "th", "Number");
        blinky.createElem(tr, "th", "Time");
        blinky.createElem(tr, "th", "Duration");
        blinky.createElem(tr, "th", "Curr status");
        blinky.createElem(tr, "th", "Prev status");
        blinky.createElem(tr, "th", "Links");

        var tbody = blinky.createElem(elem, "tbody");

        var nowSeconds = new Date().getTime() / 1000; // XXX share me

        var jobs = state.data.jobs;
        var groups = state.data.groups;
        var categories = state.data.categories;
        var components = state.data.components;
        var environments = state.data.environments;
        var agents = state.data.agents;

        var selection = state.query.category;

        for (var jobId in jobs) {
            var job = jobs[jobId];

            var group = groups[job.group_id];
            var category = categories[group.category_id];

            if (selection !== "all" && selection !== category.key) {
                continue;
            }

            var component = components[job.component_id];
            var environment = environments[job.environment_id];
            var agent = agents[job.agent_id];

            var currResult = job.current_result;
            var prevResult = job.previous_result;

            var tr = blinky.createElem(tbody, "tr");
            var td = null;
            var link = null;

            blinky.createElem(tr, "td", component.name);
            blinky.createElem(tr, "td", environment.name);

            td = blinky.createElem(tr, "td");
            blinky.createObjectLink(td, job);

            td = blinky.createElem(tr, "td");
            blinky.createObjectLink(td, agent);

            if (currResult) {
                var timeSeconds = currResult.start_time;
                var timeAgo = blinky.formatDuration(nowSeconds - timeSeconds) + " ago";
                var duration = blinky.formatDuration(currResult.duration);

                td = blinky.createElem(tr, "td");
                link = blinky.createObjectLink(td, currResult);
                link.textContent = currResult.number;

                td = blinky.createElem(tr, "td");
                td.setAttribute("data-value", timeSeconds);
                td.textContent = timeAgo;

                td = blinky.createElem(tr, "td");
                td.setAttribute("data-value", currResult.duration);
                td.textContent = duration;

                td = blinky.createElem(tr, "td")
                td.textContent = currResult.status;

                td = blinky.createElem(tr, "td");

                if (prevResult) {
                    td.textContent = prevResult.status;
                }

                td = blinky.createElem(tr, "td");

                link = blinky.createObjectDataLink(td, currResult);
                link.textContent = "Data";

                blinky.createText(td, ", ");

                link = blinky.createResultTestsLink(td, currResult);
            } else {
                blinky.createElem(tr, "td");
                blinky.createElem(tr, "td");
                blinky.createElem(tr, "td");
                blinky.createElem(tr, "td");
                blinky.createElem(tr, "td");
                blinky.createElem(tr, "td");
            }
        }

        return elem;
    },

    state: {
        query: {
            category: "all",
            view: "panel"
        },
        data: null,
        dataHash: null,
        dataTimestamp: null // XXX
    },

    fetchInterval: 60 * 1000,

    fetchData: function() {
        console.log("Fetching data");

        var request = blinky.openGetRequest("/data.json", function(request) {
            if (request.status === 200) {
                blinky.state.dataHash = request.getResponseHeader("ETag");
                blinky.state.data = JSON.parse(request.responseText);
                blinky.fireStateChangeEvent();
            }

            blinky.updateRequestStatus(request);
        });

        if (blinky.state.dataHash) {
            request.setRequestHeader("If-None-Match", blinky.state.dataHash);
        }

        request.send(null);
    },

    renderPage: function(state) {
        console.log("Rendering page");

        var oldContent = $("#content");
        var newContent = document.createElement("div");

        newContent.setAttribute("id", "content");

        document.title = state.data.title;

        blinky.createHeader(newContent, state);
        blinky.createBody(newContent, state);
        blinky.createFooter(newContent, state);

        oldContent.parentNode.replaceChild(newContent, oldContent);
    },

    updateRequestStatus: function(request) {
        var elem = $("#request-status");
        var time = new Date().toLocaleString();

        if (elem) {
            elem.textContent = time + " (" + request.status + " " + request.statusText + ")";
        }
    },

    fireStateChangeEvent: function() {
        window.dispatchEvent(new Event("statechange"));
    },

    init: function() {
        window.addEventListener("statechange", function(event) {
            blinky.renderPage(blinky.state);

            if (blinky.state.query.view === "table") {
                Sortable.init();
            }
        });

        window.addEventListener("load", function(event) {
            if (window.location.search) {
                blinky.state.query = blinky.parseQueryString(window.location.search);
            }

            blinky.fetchData();

            window.setInterval(function() {
                if (blinky.state.query.view !== "table") {
                    blinky.fetchData();
                }
            }, blinky.fetchInterval);
        });

        window.addEventListener("popstate", function(event) {
            blinky.state.query = event.state;
            blinky.fireStateChangeEvent();
        });
    }
};
