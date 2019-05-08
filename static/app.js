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

const gesso = new Gesso();

class Blinky {
    constructor() {
        this.state = {
            query: {
                category: "all",
                view: "panel",
            },
            data: null,
            dataFetchState: null,
            renderTime: null,
        };

        window.addEventListener("statechange", (event) => {
            this.renderPage();

            if (this.state.query.view === "table") {
                Sortable.init();
            }
        });

        window.addEventListener("load", (event) => {
            if (window.location.search) {
                this.state.query = gesso.parseQueryString(window.location.search);
            }

            if (this.state.query.view === "table") {
                gesso.fetch("/data.json", (data) => {
                    this.state.data = data;
                    window.dispatchEvent(new Event("statechange"));
                });
            } else {
                this.state.dataFetchState = gesso.fetchPeriodically("/data.json", (data) => {
                    this.state.data = data;
                    window.dispatchEvent(new Event("statechange"));
                });

                window.setInterval(() => { this.checkFreshness }, 60 * 1000);
            }
        });

        window.addEventListener("popstate", (event) => {
            this.state.query = event.state;
            window.dispatchEvent(new Event("statechange"));
        });
    }

    renderHeader(parent) {
        let elem = gesso.createDiv(parent, "header");

        this.renderViewSelector(elem);

        gesso.createElement(elem, "h1", this.state.data.title);

        this.renderCategorySelector(elem);
    }

    renderBody(parent) {
        let elem = gesso.createDiv(parent, "body");
        let view = this.state.query.view;

        if (view === "panel") {
            this.renderPanelView(elem);
        } else if (view === "table") {
            this.renderTableView(elem);
        } else {
            throw new Error();
        }
    }

    renderFooter(parent) {
        let elem = gesso.createDiv(parent, "footer");

        let time = new Date((this.state.data.update_time));

        let status = gesso.createSpan(elem, "#timestamp", time.toLocaleString());

        gesso.createText(elem, " \u2022 ");
        gesso.createLink(elem, "pretty-data.html?url=/data.json", "Data");
    }

    renderViewSelector(parent) {
        let elem = gesso.createDiv(parent, "view-selector");

        this.renderViewSelectorLink(elem, "Panel", "panel");
        this.renderViewSelectorLink(elem, "Table", "table");
    }

    renderViewSelectorLink(parent, text, view) {
        let query = Object.assign({}, this.state.query);
        query.view = view;

        this.renderStateChangeLink(parent, text, query, view === this.state.query.view);
    }

    renderCategorySelector(parent) {
        let elem = gesso.createDiv(parent, "category-selector");

        this.renderCategorySelectorLink(elem, "All", "all");

        let categories = this.state.data.categories;

        for (let categoryId of Object.keys(categories)) {
            let category = categories[categoryId];
            this.renderCategorySelectorLink(elem, category.name, category.key);
        }
    }

    renderCategorySelectorLink(parent, text, category) {
        let query = Object.assign({}, this.state.query);
        query.category = category;

        this.renderStateChangeLink(parent, text, query, category === this.state.query.category);
    }

    renderStateChangeLink(parent, text, query, selected) {
        let href = "?" + gesso.emitQueryString(query);
        let elem = gesso.createLink(parent, href, text);

        if (selected) {
            elem.classList.add("selected");
        }

        elem.addEventListener("click", (event) => {
            event.preventDefault();

            this.state.query = query;
            window.history.pushState(this.state.query, null, event.target.href);

            window.dispatchEvent(new Event("statechange"));
        });
    }

    createObjectLink(parent, obj, text) {
        if (text == null) {
            text = obj.name;
        }

        if (text == null) {
            text = "-";
        }

        return gesso.createLink(parent, obj.html_url, text);
    }

    renderResultLinks(parent, result) {
        let data_url = "pretty-data.html?url=" + encodeURIComponent(result.data_url);

        gesso.createLink(parent, data_url, "Data");
        gesso.createText(parent, ", ");

        if (result.tests_url == null) {
            gesso.createSpan(parent, "disabled", "Tests");
        } else {
            gesso.createLink(parent, result.tests_url, "Tests");
        }
    }

    renderPanelView(parent) {
        let elem = gesso.createDiv(parent, "panel");

        let groups = this.state.data.groups;
        let categories = this.state.data.categories;
        let jobs = this.state.data.jobs;

        let selection = this.state.query.category;

        for (let groupId of Object.keys(groups)) {
            let group = groups[groupId];
            let category = categories[group.category_id];

            if (selection !== "all" && selection !== category.key) {
                continue;
            }

            let groupElem = gesso.createDiv(elem, "group");

            gesso.createElement(groupElem, "h2", group.name);

            let jobContainer = gesso.createDiv(groupElem, "job-container");
            let jobIds = group.job_ids;

            for (let j = 0; j < jobIds.length; j++) {
                let job = jobs[jobIds[j]];
                this.renderJob(jobContainer, job);
            }
        }
    }

    renderJob(parent, job) {
        let elem = gesso.createDiv(parent, "job");

        let component = this.state.data.components[job.component_id];
        let agent = this.state.data.agents[job.agent_id];
        let environment = this.state.data.environments[job.environment_id];
        let currResult = job.current_result;
        let prevResult = job.previous_result;

        let summary = gesso.createLink(elem, job.html_url, {"class": "job-summary"});

        gesso.createDiv(summary, "summary-component", component.name);

        if (job.name != null) {
            gesso.createDiv(summary, "summary-job", job.name);
        }

        gesso.createDiv(summary, "summary-agent", agent.name);
        gesso.createDiv(summary, "summary-environment", environment.name);

        if (currResult == null) {
            elem.classList.add("no-data");
            return;
        }

        summary.setAttribute("href", currResult.html_url);

        if (currResult.tests_url != null) {
            summary.setAttribute("href", currResult.tests_url);
        }

        if (currResult.status === "PASSED") {
            elem.classList.add("passed");
        } else if (currResult.status === "FAILED") {
            elem.classList.add("failed");

            if (prevResult != null && prevResult.status === "PASSED") {
                elem.classList.add("blinky");
            }
        }

        if (job.update_failures >= 10) {
            elem.classList.add("stale-data");
        }

        let ago = null;

        if (currResult.start_time != null) {
            ago = this.state.renderTime - currResult.start_time;
        }

        gesso.createDiv(summary, "summary-start-time", gesso.formatDurationBrief(ago));

        this.renderJobDetail(elem, job);
    }

    renderJobDetail(parent, job) {
        let elem = gesso.createDiv(parent, "job-detail");

        let component = this.state.data.components[job.component_id];
        let environment = this.state.data.environments[job.environment_id];
        let agent = this.state.data.agents[job.agent_id];
        let currResult = job.current_result;
        let prevResult = job.previous_result;

        let table = gesso.createElement(elem, "table");
        let tbody = gesso.createElement(table, "tbody");
        let td;

        this.createJobDetailField(tbody, "Component", component.name);
        this.createJobDetailField(tbody, "Environment", environment.name);

        td = this.createJobDetailField(tbody, "Agent");
        this.createObjectLink(td, agent);

        td = this.createJobDetailField(tbody, "Job");
        this.createObjectLink(td, job);

        if (currResult != null) {
            let ago = "-";

            if (currResult.start_time != null) {
                let millisAgo = this.state.renderTime - currResult.start_time;
                ago = gesso.formatDurationBrief(millisAgo) + " ago";
            }

            let duration = gesso.formatDurationBrief(currResult.duration);

            td = this.createJobDetailField(tbody, "Number");
            this.createObjectLink(td, currResult, currResult.number);

            this.createJobDetailField(tbody, "Time", ago);
            this.createJobDetailField(tbody, "Duration", duration);
            this.createJobDetailField(tbody, "Status", currResult.status);

            if (prevResult == null) {
                this.createJobDetailField(tbody, "Prev status", "-");
            } else {
                this.createJobDetailField(tbody, "Prev status", prevResult.status);
            }

            td = this.createJobDetailField(tbody, "Links");
            this.renderResultLinks(td, currResult);
        }
    }

    createJobDetailField(parent, name, text) {
        let tr = gesso.createElement(parent, "tr");
        let th = gesso.createElement(tr, "th", name);
        let td = gesso.createElement(tr, "td", text);

        return td;
    }

    renderTableView(parent) {
        let elem = gesso.createElement(parent, "table",
                                       {"class": "jobs", "data-sortable": "data-sortable"});

        let thead = gesso.createElement(elem, "thead");
        let tr = gesso.createElement(thead, "tr");

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

        let tbody = gesso.createElement(elem, "tbody");

        let jobs = this.state.data.jobs;
        let groups = this.state.data.groups;
        let categories = this.state.data.categories;
        let components = this.state.data.components;
        let environments = this.state.data.environments;
        let agents = this.state.data.agents;

        let selection = this.state.query.category;

        for (let jobId of Object.keys(jobs)) {
            let job = jobs[jobId];

            let group = groups[job.group_id];
            let category = categories[group.category_id];

            if (selection !== "all" && selection !== category.key) {
                continue;
            }

            let component = components[job.component_id];
            let environment = environments[job.environment_id];
            let agent = agents[job.agent_id];

            let currResult = job.current_result;
            let prevResult = job.previous_result;

            let tr = gesso.createElement(tbody, "tr");
            gesso.createElement(tr, "td", component.name);
            gesso.createElement(tr, "td", environment.name);

            let td;

            td = gesso.createElement(tr, "td");
            this.createObjectLink(td, job);

            td = gesso.createElement(tr, "td");
            this.createObjectLink(td, agent);

            if (currResult) {
                let duration = gesso.formatDurationBrief(currResult.duration);
                let ago = "-";
                let prevResultStatus = "-";

                if (currResult.start_time) {
                    let millisAgo = this.state.renderTime - currResult.start_time;
                    ago = gesso.formatDurationBrief(millisAgo) + " ago";
                }

                if (prevResult) {
                    prevResultStatus = prevResult.status;
                }

                td = gesso.createElement(tr, "td");
                this.createObjectLink(td, currResult, currResult.number);

                gesso.createElement(tr, "td", {text: ago, "data-value": currResult.start_time});
                gesso.createElement(tr, "td", {text: duration, "data-value": currResult.duration});
                gesso.createElement(tr, "td", currResult.status);
                gesso.createElement(tr, "td", prevResultStatus);

                td = gesso.createElement(tr, "td");
                this.renderResultLinks(td, currResult);
            } else {
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
                gesso.createElement(tr, "td");
            }
        }
    }

    renderPage() {
        console.log("Rendering page");

        this.state.renderTime = new Date().getTime();

        let elem = gesso.createDiv(null, "#content");

        document.title = this.state.data.title;

        this.renderHeader(elem);
        this.renderBody(elem);
        this.renderFooter(elem);

        gesso.replaceElement($("#content"), elem);
    }

    checkFreshness() {
        console.log("Checking freshness");

        let failedAttempts = this.state.dataFetchState.failedAttempts;

        if (failedAttempts == 0) {
            $("body").classList.remove("disconnected");
        } else if (failedAttempts >= 10) {
            $("body").classList.add("disconnected");
        }
    }
}
