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

var blinky = {
    formatDuration: function (seconds) {
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

    createHeader: function (parent, state) {
        var elem = gesso.createDiv(parent, "header");

        blinky.createViewSelector(elem, state);
        gesso.createElement(elem, "h1", state.data.title);
        blinky.createCategorySelector(elem, state);

        return elem;
    },

    createBody: function (parent, state) {
        var elem = gesso.createDiv(parent, "body");

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

    createFooter: function (parent, state) {
        var elem = gesso.createDiv(parent, "footer");

        var offset = new Date().getTimezoneOffset() * 60;
        var time = new Date((state.data.update_time - offset) * 1000);

        var status = gesso.createElement(elem, "span", time.toLocaleString());
        status.setAttribute("id", "timestamp");

        gesso.createText(elem, " \u2022 ");

        var link = gesso.createLink(elem, "pretty-data.html?url=/data.json", "Data");
        link.setAttribute("target", "blinky");

        return elem;
    },

    createViewSelector: function (parent, state) {
        var elem = gesso.createDiv(parent, "view-selector");

        blinky.createViewSelectorLink(elem, state, "Panel", "panel");
        blinky.createViewSelectorLink(elem, state, "Table", "table");

        return elem;
    },

    createViewSelectorLink: function (parent, state, text, view) {
        var query = Object.assign({}, state.query); // XXX compat
        query.view = view;

        var elem = blinky.createStateLink(parent, state, text, query);

        if (view === state.query.view) {
            elem.classList.add("selected");
        }

        return elem;
    },

    createCategorySelector: function (parent, state) {
        var elem = gesso.createDiv(parent, "category-selector");

        blinky.createCategorySelectorLink(elem, state, "All", "all");

        var categories = state.data.categories;

        for (var categoryId in categories) {
            var category = categories[categoryId];
            blinky.createCategorySelectorLink(elem, state, category.name, category.key);
        }

        return elem;
    },

    createCategorySelectorLink: function (parent, state, text, category) {
        var query = Object.assign({}, state.query); // XXX compat
        query.category = category;

        var elem = blinky.createStateLink(parent, state, text, query);

        if (category === state.query.category) {
            elem.classList.add("selected");
        }

        return elem;
    },

    // XXX name kinda sucks
    createStateLink: function (parent, state, text, query) {
        var href = "?" + gesso.emitQueryString(query);
        var elem = gesso.createLink(parent, href, text);

        elem.addEventListener("click", function (event) {
            event.preventDefault();

            state.query = query;
            window.history.pushState(state.query, null, event.target.href);

            window.dispatchEvent(new Event("statechange"));
        });

        return elem;
    },

    createObjectLink: function (parent, obj) {
        var elem = gesso.createLink(parent, obj.html_url, obj.name);
        elem.setAttribute("target", "blinky");
        return elem;
    },

    createObjectDataLink: function (parent, obj) {
        var url = "pretty-data.html?url=" + encodeURIComponent(obj.data_url);
        var elem = gesso.createLink(parent, url, obj.name);

        elem.setAttribute("target", "blinky");

        return elem;
    },

    createResultTestsLink: function (parent, result) {
        if (!result.tests_url) {
            var elem = gesso.createElement(parent, "span", "Tests");
            elem.setAttribute("class", "disabled");
            return elem;
        }

        var elem = gesso.createLink(parent, result.tests_url, "Tests");
        elem.setAttribute("target", "blinky");

        return elem;
    },

    createPanel: function (parent, state) {
        var elem = gesso.createDiv(parent, "panel");

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

            var groupElem = gesso.createDiv(elem, "group");

            gesso.createElement(groupElem, "h2", group.name);

            var jobContainer = gesso.createDiv(groupElem, "job-container");
            var jobIds = group.job_ids;

            for (var j = 0; j < jobIds.length; j++) {
                var job = jobs[jobIds[j]];
                blinky.createJob(jobContainer, state, job);
            }
        }

        return elem;
    },

    createJob: function (parent, state, job) {
        var component = state.data.components[job.component_id];
        var environment = state.data.environments[job.environment_id];
        var currResult = job.current_result;
        var prevResult = job.previous_result;

        var elem = gesso.createDiv(parent, "job");

        var summary = gesso.createLink(elem, job.html_url);
        summary.setAttribute("target", "blinky");
        summary.setAttribute("class", "job-summary");

        gesso.createDiv(summary, "summary-component", component.name);
        gesso.createDiv(summary, "summary-job", job.name);
        gesso.createDiv(summary, "summary-environment", environment.name);

        if (!currResult) {
            elem.classList.add("no-data");
            return elem;
        }

        summary.setAttribute("href", currResult.html_url);

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

        gesso.createDiv(summary, "summary-start-time", blinky.formatDuration(secondsAgo));
        blinky.createJobDetail(elem, state, job);

        return elem;
    },

    createJobDetail: function (parent, state, job) {
        var elem = gesso.createDiv(parent, "job-detail");

        var component = state.data.components[job.component_id];
        var environment = state.data.environments[job.environment_id];
        var agent = state.data.agents[job.agent_id];
        var currResult = job.current_result;
        var prevResult = job.previous_result;

        var table = gesso.createElement(elem, "table");
        var tbody = gesso.createElement(table, "tbody");
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

            gesso.createText(td, ", ");

            link = blinky.createResultTestsLink(td, currResult);
        }

        return elem;
    },

    createJobDetailField: function (parent, name, text) {
        var tr = gesso.createElement(parent, "tr");
        var th = gesso.createElement(tr, "th", name);
        var td = gesso.createElement(tr, "td", text);

        return td;
    },

    createTable: function (parent, state) {
        var elem = gesso.createElement(parent, "table");

        elem.classList.add("jobs");
        elem.setAttribute("data-sortable", "data-sortable");

        var thead = gesso.createElement(elem, "thead");
        var tr = gesso.createElement(thead, "tr");

        gesso.createElement(tr, "th", "Component");
        gesso.createElement(tr, "th", "Environment");
        gesso.createElement(tr, "th", "Job");
        gesso.createElement(tr, "th", "Agent");
        gesso.createElement(tr, "th", "Number");
        gesso.createElement(tr, "th", "Time");
        gesso.createElement(tr, "th", "Duration");
        gesso.createElement(tr, "th", "Curr status");
        gesso.createElement(tr, "th", "Prev status");
        gesso.createElement(tr, "th", "Links");

        var tbody = gesso.createElement(elem, "tbody");

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

            var tr = gesso.createElement(tbody, "tr");
            var td = null;
            var link = null;

            gesso.createElement(tr, "td", component.name);
            gesso.createElement(tr, "td", environment.name);

            td = gesso.createElement(tr, "td");
            blinky.createObjectLink(td, job);

            td = gesso.createElement(tr, "td");
            blinky.createObjectLink(td, agent);

            if (currResult) {
                var timeSeconds = currResult.start_time;
                var timeAgo = blinky.formatDuration(nowSeconds - timeSeconds) + " ago";
                var duration = blinky.formatDuration(currResult.duration);

                td = gesso.createElement(tr, "td");
                link = blinky.createObjectLink(td, currResult);
                link.textContent = currResult.number;

                td = gesso.createElement(tr, "td");
                td.setAttribute("data-value", timeSeconds);
                td.textContent = timeAgo;

                td = gesso.createElement(tr, "td");
                td.setAttribute("data-value", currResult.duration);
                td.textContent = duration;

                td = gesso.createElement(tr, "td")
                td.textContent = currResult.status;

                td = gesso.createElement(tr, "td");

                if (prevResult) {
                    td.textContent = prevResult.status;
                }

                td = gesso.createElement(tr, "td");

                link = blinky.createObjectDataLink(td, currResult);
                link.textContent = "Data";

                gesso.createText(td, ", ");

                link = blinky.createResultTestsLink(td, currResult);
            } else {
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
            }
        }

        return elem;
    },

    state: {
        query: {
            category: "all",
            view: "panel"
        },
        data: null
    },

    renderPage: function (state) {
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

    updateTimestamp: function (request) {
        var elem = $("#timestamp");
        var time = new Date().toLocaleString();
    },

    checkFreshness: function () {
        console.log("Checking freshness");

        if (gesso.fetchDataAttributes.failedAttempts >= 1) {
            window.alert("Trouble! I can't reach the server.");
        }
    },

    init: function () {
        window.addEventListener("statechange", function (event) {
            blinky.renderPage(blinky.state);

            if (blinky.state.query.view === "table") {
                Sortable.init();
            }
        });

        window.addEventListener("load", function (event) {
            if (window.location.search) {
                blinky.state.query = gesso.parseQueryString(window.location.search);
            }

            function handler(data) {
                blinky.state.data = data;
                window.dispatchEvent(new Event("statechange"));
            }

            if (blinky.state.query.view === "table") {
                gesso.fetchData("/data.json", handler)
            } else {
                gesso.fetchDataPeriodically("/data.json", handler);
            }
        });

        window.addEventListener("popstate", function (event) {
            blinky.state.query = event.state;
            window.dispatchEvent(new Event("statechange"));
        });
    }
};
