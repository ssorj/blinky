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
                gesso.fetch("/api/data", (data) => {
                    this.state.data = data;
                    window.dispatchEvent(new Event("statechange"));
                });
            } else {
                this.state.dataFetchState = gesso.fetchPeriodically("/api/data", (data) => {
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

        let url = new URL("/api/data", window.location.href);

        gesso.createText(elem, " \u2022 ");
        gesso.createLink(elem, "pretty.html?url=" + encodeURIComponent(url), "Data");
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

    renderRunLinks(parent, run) {
        let data_url = "pretty.html?url=" + encodeURIComponent(run.data_url);

        gesso.createLink(parent, data_url, "Data");
        gesso.createText(parent, ", ");

        if (run.tests_url == null) {
            gesso.createSpan(parent, "disabled", "Tests");
        } else {
            gesso.createLink(parent, run.tests_url, "Tests");
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

        function getName(obj) {
            if (obj != null) {
                return obj.name;
            }
        }

        function capitalize(string) {
            return string.charAt(0).toUpperCase() + string.slice(1);
        }

        const fields = {
            "name": job.name,
            "branch": capitalize(job.branch),
            "agent": getName(this.state.data.agents[job.agent_id]),
            "component": getName(this.state.data.components[job.component_id]),
            "environment": getName(this.state.data.environments[job.environment_id]),
        }

        let summary = gesso.createLink(elem, job.html_url, {"class": "job-summary"});

        const group = this.state.data.groups[job.group_id];

        for (const name of group.fields) {
            if (fields[name] != null) {
                gesso.createDiv(summary, null, fields[name]);
            }
        }

        let currRun = job.current_run;
        let prevRun = job.previous_run;

        if (currRun == null) {
            elem.classList.add("no-data");
            return;
        }

        summary.setAttribute("href", currRun.html_url);

        if (currRun.logs_url != null) {
            summary.setAttribute("href", currRun.logs_url);
        }

        if (currRun.tests_url != null) {
            summary.setAttribute("href", currRun.tests_url);
        }

        if (currRun.status === "PASSED") {
            elem.classList.add("passed");
        } else if (currRun.status === "FAILED") {
            elem.classList.add("failed");

            if (prevRun != null && prevRun.status === "PASSED") {
                elem.classList.add("blinky");
            }
        }

        if (job.update_failures >= 10) {
            elem.classList.add("stale-data");
        }

        let ago = null;

        if (currRun.start_time != null) {
            ago = this.state.renderTime - currRun.start_time;
        }

        gesso.createDiv(summary, "summary-start-time", gesso.formatDurationBrief(ago));

        this.renderJobDetail(elem, job);
    }

    renderJobDetail(parent, job) {
        let elem = gesso.createDiv(parent, "job-detail");

        let component = this.state.data.components[job.component_id];
        let environment = this.state.data.environments[job.environment_id];
        let agent = this.state.data.agents[job.agent_id];
        let currRun = job.current_run;
        let prevRun = job.previous_run;

        let table = gesso.createElement(elem, "table");
        let tbody = gesso.createElement(table, "tbody");
        let td;

        // XXX
        if (component != null) {
            this.createJobDetailField(tbody, "Component", component.name);
        }

        if (environment != null) {
            this.createJobDetailField(tbody, "Environment", environment.name);
        }

        td = this.createJobDetailField(tbody, "Agent");
        this.createObjectLink(td, agent);

        td = this.createJobDetailField(tbody, "Job");
        this.createObjectLink(td, job);

        if (currRun != null) {
            let ago = "-";

            if (currRun.start_time != null) {
                let millisAgo = this.state.renderTime - currRun.start_time;
                ago = gesso.formatDurationBrief(millisAgo) + " ago";
            }

            let duration = gesso.formatDurationBrief(currRun.duration);

            td = this.createJobDetailField(tbody, "Run");
            this.createObjectLink(td, currRun, currRun.number);

            this.createJobDetailField(tbody, "Time", ago);
            this.createJobDetailField(tbody, "Duration", duration);
            this.createJobDetailField(tbody, "Status", currRun.status);

            if (prevRun == null) {
                this.createJobDetailField(tbody, "Prev status", "-");
            } else {
                this.createJobDetailField(tbody, "Prev status", prevRun.status);
            }

            td = this.createJobDetailField(tbody, "Links");
            this.renderRunLinks(td, currRun);
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

            let currRun = job.current_run;
            let prevRun = job.previous_run;

            let tr = gesso.createElement(tbody, "tr");

            if (component != null) {
                gesso.createElement(tr, "td", component.name);
            } else {
                gesso.createElement(tr, "td", "-");
            }

            if (environment != null) {
                gesso.createElement(tr, "td", environment.name);
            } else {
                gesso.createElement(tr, "td", "-");
            }

            let td;

            td = gesso.createElement(tr, "td");
            this.createObjectLink(td, job);

            td = gesso.createElement(tr, "td");
            this.createObjectLink(td, agent);

            if (currRun) {
                let duration = gesso.formatDurationBrief(currRun.duration);
                let ago = "-";
                let prevRunStatus = "-";

                if (currRun.start_time) {
                    let millisAgo = this.state.renderTime - currRun.start_time;
                    ago = gesso.formatDurationBrief(millisAgo) + " ago";
                }

                if (prevRun) {
                    prevRunStatus = prevRun.status;
                }

                td = gesso.createElement(tr, "td");
                this.createObjectLink(td, currRun, currRun.number);

                gesso.createElement(tr, "td", {text: ago, "data-value": currRun.start_time});
                gesso.createElement(tr, "td", {text: duration, "data-value": currRun.duration});
                gesso.createElement(tr, "td", currRun.status);
                gesso.createElement(tr, "td", prevRunStatus);

                td = gesso.createElement(tr, "td");
                this.renderRunLinks(td, currRun);
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

    renderSiteIcon() {
        const jobs = this.state.data.jobs;
        let passed = 0;
        let failed = 0;

        for (let jobId of Object.keys(jobs)) {
            let job = jobs[jobId];

            if (!job.current_run) {
                continue;
            }

            if (job.current_run.status == "PASSED") {
                passed += 1;
            } else if (job.current_run.status == "FAILED") {
                failed += 1;
            }
        }

        const total = passed + failed;
        let icon;

        if (total == 0) {
            return;
        }

        if (failed / total >= 0.75) {
            icon = "/images/icon-4.svg";
        } else if (failed / total >= 0.5) {
            icon = "/images/icon-3.svg";
        } else if (failed / total >= 0.25) {
            icon = "/images/icon-2.svg";
        } else if (failed / total >= 0.0) {
            icon = "/images/icon-1.svg";
        } else {
            icon = "/images/icon-0.svg";
        }

        $("link[rel*='icon']").href = icon;
    }

    renderPage() {
        console.log("Rendering page");

        this.state.renderTime = new Date().getTime();

        this.renderSiteIcon();

        document.title = this.state.data.title;

        let elem = gesso.createDiv(null, "#content");

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
