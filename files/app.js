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
    sendRequest: function(url, handler) {
        var request = new XMLHttpRequest();

        request.onreadystatechange = function() {
            if (request.readyState === 4 && request.status === 200) {
                handler(request);
            }
        };

        request.open("GET", url);
        request.send(null);
    },

    createElem: function(parent, tag) {
        var child = document.createElement(tag);
        parent.appendChild(child);
        return child;
    },

    createText: function(parent, text) {
        var node = document.createTextNode(text);
        parent.appendChild(node);
        return node;
    },

    createTextElem: function(parent, tag, text) {
        var elem = blinky.createElem(parent, tag);

        if (text) {
            blinky.createText(elem, text);
        }

        return elem;
    },

    createDiv: function(parent, class_) {
        var elem = blinky.createElem(parent, "div");

        if (class_) {
            elem.setAttribute("class", class_);
        }

        return elem;
    },

    createTextDiv: function(parent, class_, text) {
        var elem = blinky.createDiv(parent, class_);

        if (text) {
            blinky.createText(elem, text);
        }

        return elem;
    },

    createLink: function(parent, href, text) {
        var elem = blinky.createTextElem(parent, "a", text);
        elem.setAttribute("href", href);
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
            var elem = blinky.createTextElem(parent, "span", "Tests");
            elem.setAttribute("class", "disabled");
            return elem;
        }

        var elem = blinky.createLink(parent, result.test_url, "Tests");
        elem.setAttribute("target", "blinky");

        return elem;
    },

    createCategorySelector: function(parent, categories) {
        var selector = blinky.createDiv(parent, "category-selector");
        var link = blinky.createLink(selector, "#all", "All");

        for (var categoryId in categories) {
            var category = categories[categoryId];
            var link = blinky.createLink(selector, "#" + category.key, category.name);
        }
    },

    updateCategorySelection: function(event) {
        event.preventDefault();

        var hash = window.location.hash;

        if (!hash) {
            hash = "#all";
        }

        var links = $$(".category-selector > a");

        for (var i = 0; i < links.length; i++) {
            var elem = links[i];

            if (elem.getAttribute("href") == hash) {
                elem.classList.add("selected");
            } else {
                elem.classList.remove("selected");
            }
        }

        var selectedCategory = $(hash);
        var categories = $$(".category");

        for (var i = 0; i < categories.length; i++) {
            var elem = categories[i];

            if (hash === "#all") {
                elem.className = "category";
                continue;
            }

            if (elem == selectedCategory) {
                elem.classList.remove("invisible");
            } else {
                elem.classList.add("invisible");
            }
        }
    },

    renderPanel: function(data) {
        var oldContent = $("#content");
        var newContent = document.createElement("div");
        newContent.setAttribute("id", "content");

        var categories = data.categories;

        blinky.createCategorySelector(newContent, categories);

        for (var categoryId in categories) {
            var category = categories[categoryId];
            var categoryElem = blinky.createDiv(newContent, "category");

            categoryElem.setAttribute("id", category.key);

            var groupIds = category.group_ids;

            for (var i = 0; i < groupIds.length; i++) {
                var group = data.groups[groupIds[i]];
                var groupElem = blinky.createDiv(categoryElem, "group");

                blinky.createTextElem(groupElem, "h2", group.name);

                var container = blinky.createDiv(groupElem, "job-container");
                var jobIds = group.job_ids;

                for (var j = 0; j < jobIds.length; j++) {
                    var job = data.jobs[jobIds[j]];
                    blinky.createJob(container, data, job);
                }
            }
        }

        oldContent.parentNode.replaceChild(newContent, oldContent);
    },

    createJob: function(parent, data, job) {
        var component = data.components[job.component_id];
        var environment = data.environments[job.environment_id];
        var currResult = job.current_result;
        var prevResult = job.previous_result;

        var elem = blinky.createLink(parent, job.html_url, null);

        elem.setAttribute("target", "blinky");
        elem.classList.add("job-item");

        var summary = blinky.createDiv(elem, "job-summary");

        blinky.createTextDiv(summary, "summary-component", component.name);
        blinky.createTextDiv(summary, "summary-job", job.name);
        blinky.createTextDiv(summary, "summary-environment", environment.name);

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

        var secondsNow = new Date().getTime() / 1000;
        var secondsAgo = secondsNow - currResult.start_time;

        blinky.createTextDiv(summary, "summary-start-time", blinky.formatDuration(secondsAgo));
        blinky.createJobDetail(elem, data, job);

        return elem;
    },

    createJobDetail: function(parent, data, job) {
        var component = data.components[job.component_id];
        var environment = data.environments[job.environment_id];
        var agent = data.agents[job.agent_id];
        var currResult = job.current_result;
        var prevResult = job.previous_result;

        var elem = blinky.createDiv(parent, "job-detail");

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
            var secondsNow = new Date().getTime() / 1000;
            var secondsAgo = secondsNow - currResult.start_time;
            var timeAgo = blinky.formatDuration(secondsAgo) + " ago";

            td = blinky.createJobDetailField(tbody, "Number", null);
            blinky.createObjectLink(td, currResult, currResult.number);

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

    createJobDetailField: function(tbody, name, text) {
        var tr = blinky.createElem(tbody, "tr");
        var th = blinky.createTextElem(tr, "th", name);
        var td = blinky.createTextElem(tr, "td", text);

        return td;
    },

    renderTable: function(data) {
        var oldContent = $("#content");
        var newContent = document.createElement("tbody");
        newContent.setAttribute("id", "content");

        var nowSeconds = new Date().getTime() / 1000;

        for (var jobId in data.jobs) {
            var job = data.jobs[jobId];
            var component = data.components[job.component_id];
            var environment = data.environments[job.environment_id];
            var agent = data.agents[job.agent_id];
            var currResult = job.current_result;
            var prevResult = job.previous_result;

            var tr = blinky.createElem(newContent, "tr");
            var td = null;
            var link = null;

            blinky.createElem(tr, "td").textContent = component.name;
            blinky.createElem(tr, "td").textContent = environment.name;

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

        oldContent.parentNode.replaceChild(newContent, oldContent);
    },

    renderTitle: function(data) {
        var elem = $("h1");

        if (!elem) {
            return;
        }

        elem.textContent = data.title;
    },

    renderUpdateInfo: function(request) {
        var elem = $("#update-info");

        if (!elem) {
            return;
        }

        var time = new Date().toLocaleString();

        elem.textContent = time + " (HTTP " + request.status + ")";
    },

    etag: null,
    updateInterval: 60 * 1000,

    update: function(handler) {
        var request = new XMLHttpRequest();

        request.onreadystatechange = function() {
            if (request.readyState === 4) {
                blinky.renderUpdateInfo(request);

                if (request.status !== 200) {
                    return;
                }

                blinky.etag = request.getResponseHeader("ETag");

                if (!request.responseText) {
                    return;
                }

                var data = JSON.parse(request.responseText);

                blinky.renderTitle(data);

                handler(data);

                window.dispatchEvent(new Event("update"));
            }
        };

        request.open("GET", "/data.json");

        if (blinky.etag) {
            request.setRequestHeader("If-None-Match", blinky.etag);
        }

        request.send(null);
    },

    updatePanel: function(event) {
        blinky.update(blinky.renderPanel);
    },

    updateTable: function(event) {
        blinky.update(blinky.renderTable);
    }
};
