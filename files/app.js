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

var $ = function(selectors) {
    return document.querySelector(selectors);
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

    createChild: function(parent, tag) {
        var child = document.createElement(tag);

        parent.appendChild(child);

        return child;
    },

    createText: function(parent, text) {
        var node = document.createTextNode(text);

        parent.appendChild(node);

        return node;
    },

    createObjectLink: function(parent, obj) {
        var elem = blinky.createChild(parent, "a");

        elem.setAttribute("href", obj.html_url);
        elem.setAttribute("target", "blinky");
        elem.textContent = obj.name;

        return elem;
    },

    createObjectDataLink: function(parent, obj) {
        var elem = blinky.createChild(parent, "a");

        elem.setAttribute("href", "pretty.html?url=" + encodeURIComponent(obj.data_url));
        elem.setAttribute("target", "blinky");
        elem.textContent = obj.name;

        return elem;
    },

    createResultTestsLink: function(parent, result) {
        if (!result.tests_url) {
            var elem = blinky.createChild(parent, "span");

            elem.setAttribute("class", "disabled");
            elem.textContent = "Tests";
                
            return elem;
        }
        
        var elem = blinky.createChild(parent, "a");

        elem.setAttribute("href", result.tests_url);
        elem.setAttribute("target", "blinky");
        elem.textContent = "Tests";

        return elem;
    },

    formatDuration: function(seconds) {
        if (seconds < 0)
            seconds = 0;

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

    renderPanel: function(data) {
        var oldContent = $("#content");
        var newContent = document.createElement("div");
        newContent.setAttribute("id", "content");

        var groups = data.groups;

        for (var groupId in groups) {
            var group = groups[groupId];

            var groupElem = blinky.createChild(newContent, "div");
            groupElem.setAttribute("class", "group");

            var h2 = blinky.createChild(groupElem, "h2");
            h2.textContent = group.name;

            var containerElem = blinky.createChild(groupElem, "div");
            containerElem.setAttribute("class", "job-container");

            var jobIds = group.job_ids;

            for (var i = 0; i < jobIds.length; i++) {
                var job = data.jobs[jobIds[i]];

                var resultElem = blinky.createJob(data, job);
                containerElem.appendChild(resultElem);
            }
        }

        oldContent.parentNode.replaceChild(newContent, oldContent);
    },

    createJob: function(data, job) {
        var component = data.components[job.component_id];
        var environment = data.environments[job.environment_id];
        var currentResult = job.current_result;
        var previousResult = job.previous_result;

        var elem = document.createElement("a");
        elem.setAttribute("class", "job-item");
        elem.setAttribute("href", job.html_url);
        elem.setAttribute("target", "blinky");

        var summary = blinky.createChild(elem, "div");
        summary.setAttribute("class", "job-summary");

        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-component");
        field.textContent = component.name;

        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-job");
        field.textContent = job.name;

        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-environment");
        field.textContent = environment.name;

        if (!currentResult) {
            return elem;
        }

        elem.setAttribute("href", currentResult.html_url);

        var secondsNow = new Date().getTime() / 1000;
        var secondsAgo = secondsNow - currentResult.start_time;

        if (currentResult.status === "PASSED") {
            elem.setAttribute("class", "job-item passed");
        } else if (currentResult.status === "FAILED") {
            if (previousResult && previousResult.status === "PASSED") {
                elem.setAttribute("class", "job-item failed blinky");
            } else {
                elem.setAttribute("class", "job-item failed");
            }
        }

        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-start-time");
        field.textContent = blinky.formatDuration(secondsAgo);

        var detail = blinky.createJobDetail(data, job);
        elem.appendChild(detail);

        return elem;
    },

    createJobDetail: function(data, job) {
        var component = data.components[job.component_id];
        var environment = data.environments[job.environment_id];
        var agent = data.agents[job.agent_id];
        var currentResult = job.current_result;
        var previousResult = job.previous_result;

        var elem = document.createElement("div");
        elem.setAttribute("class", "job-detail");

        var table = blinky.createChild(elem, "table");
        var tbody = blinky.createChild(table, "tbody");
        var td = null;
        var link = null;

        blinky.createJobDetailField(tbody, "Component").textContent = component.name;
        blinky.createJobDetailField(tbody, "Environment").textContent = environment.name;

        td = blinky.createJobDetailField(tbody, "Agent");
        blinky.createObjectLink(td, agent);

        td = blinky.createJobDetailField(tbody, "Job");
        blinky.createObjectLink(td, job);

        if (currentResult) {
            var duration = blinky.formatDuration(currentResult.duration);
            var secondsNow = new Date().getTime() / 1000;
            var secondsAgo = secondsNow - currentResult.start_time;
            var timeAgo = blinky.formatDuration(secondsAgo) + " ago";

            td = blinky.createJobDetailField(tbody, "Number");
            blinky.createObjectLink(td, currentResult).textContent = currentResult.number;

            blinky.createJobDetailField(tbody, "Time").textContent = timeAgo;
            blinky.createJobDetailField(tbody, "Duration").textContent = duration;

            blinky.createJobDetailField(tbody, "Status").textContent = currentResult.status;

            if (previousResult) {
                blinky.createJobDetailField(tbody, "Prev status").textContent = previousResult.status;
            }

            td = blinky.createJobDetailField(tbody, "Links");

            link = blinky.createObjectDataLink(td, currentResult)
            link.textContent = "Data";

            blinky.createText(td, ", ");

            link = blinky.createResultTestsLink(td, currentResult);
        }

        return elem;
    },

    createJobDetailField: function(tbody, name) {
        var tr = blinky.createChild(tbody, "tr");
        var th = blinky.createChild(tr, "th");
        var td = blinky.createChild(tr, "td");

        th.textContent = name;

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
            var currentResult = job.current_result;
            var previousResult = job.previous_result;

            var timeSeconds = null;
            var durationSeconds = null;

            var timeAgo = "-";
            var duration = "-";
            var number = "-"
            var status = "-"
            var previousStatus = "-";

            if (currentResult !== null) {
                timeSeconds = currentResult.start_time;
                durationSeconds = currentResult.duration;

                timeAgo = blinky.formatDuration(nowSeconds - timeSeconds) + " ago";
                duration = blinky.formatDuration(currentResult.duration);
                number = currentResult.number;
                status = currentResult.status;
            }

            if (previousResult !== null) {
                previousStatus = previousResult.status;
            }

            var tr = blinky.createChild(newContent, "tr");
            var td = null;
            var link = null;

            blinky.createChild(tr, "td").textContent = component.name;
            blinky.createChild(tr, "td").textContent = environment.name;

            td = blinky.createChild(tr, "td");
            link = blinky.createObjectLink(td, job);

            td = blinky.createChild(tr, "td");
            link = blinky.createObjectLink(td, agent);

            td = blinky.createChild(tr, "td");
            link = blinky.createObjectLink(td, currentResult);
            link.textContent = number;

            td = blinky.createChild(tr, "td");
            td.setAttribute("data-value", timeSeconds);
            td.textContent = timeAgo;

            td = blinky.createChild(tr, "td");
            td.setAttribute("data-value", durationSeconds);
            td.textContent = duration;

            blinky.createChild(tr, "td").textContent = status;
            blinky.createChild(tr, "td").textContent = previousStatus;

            td = blinky.createChild(tr, "td");

            link = blinky.createObjectDataLink(td, currentResult);
            link.textContent = "Data";

            blinky.createText(td, ", ");

            link = blinky.createResultTestsLink(td, currentResult);
        }

        oldContent.parentNode.replaceChild(newContent, oldContent);
    },

    renderTitle: function(data) {
        var elem = $("h1");

        if (elem === null) {
            return;
        }

        elem.textContent = data.title;
    },

    renderUpdateInfo: function(request) {
        var elem = $("#update-info");

        if (elem === null) {
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
            }
        };

        request.open("GET", "/data.json");

        if (blinky.etag !== null) {
            request.setRequestHeader("If-None-Match", blinky.etag);
        }

        request.send(null);
    },

    updatePanel: function() {
        blinky.update(blinky.renderPanel);
    },

    updateTable: function() {
        blinky.update(blinky.renderTable);
    }
};
