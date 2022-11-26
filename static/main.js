// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

import * as gesso from "./gesso/gesso.js";
import * as pretty from "./pretty.js";
import * as sortable from "./sortable.js";

const html = `
<body>
  <div id="content">
    <span class="notice">Loading...</span>
  </div>
</body>
`;

const state = {
    query: {
        category: "all",
        view: "panel",
    },
    data: null,
    renderTime: null,
};

class Page extends gesso.Page {
    constructor(router) {
        super(router, "/", html);
    }

    update() {
        for (const [key, value] of new URLSearchParams(window.location.search).entries()) {
            if (value) {
                state.query[key] = value;
            }
        }

            // state.query = Object.fromEntries();

        gesso.getJson("/api/data", (data) => {
            state.data = data;
            renderPage();
            Sortable.init();
        });
    }
}

const router = new gesso.Router();
const mainPage = new Page(router);
new pretty.Page(router);

window.setInterval(() => {
    if (router.page === mainPage && state.query.view === "panel") {
        mainPage.update();
    }
}, 60 * 1000);

function renderPage() {
    console.log("Rendering page");

    state.renderTime = new Date().getTime();

    renderSiteIcon();

    document.title = state.data.title;

    let elem = gesso.createDiv(null, "#content");

    renderHeader(elem);
    renderBody(elem);
    renderFooter(elem);

    gesso.replaceElement($("#content"), elem);
}

function renderSiteIcon() {
    const jobs = state.data.jobs;
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

function renderHeader(parent) {
    let elem = gesso.createDiv(parent, "header");

    renderViewSelector(elem);

    gesso.createElement(elem, "h1", state.data.title);

    renderCategorySelector(elem);
}

function renderBody(parent) {
    let elem = gesso.createDiv(parent, "body");
    let view = state.query.view;

    if (view === "panel") {
        renderPanelView(elem);
    } else if (view === "table") {
        renderTableView(elem);
    } else {
        throw new Error(`Unknown view mode: ${view}`);
    }
}

function renderFooter(parent) {
    let elem = gesso.createDiv(parent, "footer");
    let time = new Date((state.data.update_time));
    let url = new URL("/api/data", window.location.href);

    gesso.createSpan(elem, "#timestamp", time.toLocaleString());
    gesso.createText(elem, " \u2022 ");
    gesso.createLink(elem, "pretty?url=" + encodeURIComponent(url), "Data");
}

function renderViewSelector(parent) {
    let elem = gesso.createDiv(parent, "view-selector");

    renderViewSelectorLink(elem, "Panel", "panel");
    renderViewSelectorLink(elem, "Table", "table");
}

function renderViewSelectorLink(parent, text, view) {
    let query = Object.assign({}, state.query);
    query.view = view;

    renderStateChangeLink(parent, text, query, view === state.query.view);
}

function renderCategorySelector(parent) {
    let elem = gesso.createDiv(parent, "category-selector");

    renderCategorySelectorLink(elem, "All", "all");

    let categories = state.data.categories;

    for (let categoryId of Object.keys(categories)) {
        let category = categories[categoryId];
        renderCategorySelectorLink(elem, category.name, category.key);
    }
}

function renderCategorySelectorLink(parent, text, category) {
    let query = Object.assign({}, state.query);
    query.category = category;

    renderStateChangeLink(parent, text, query, category === state.query.category);
}

function renderStateChangeLink(parent, text, query, selected) {
    let href = "?" + new URLSearchParams(query).toString();;
    let elem = gesso.createLink(parent, href, text);

    if (selected) {
        elem.classList.add("selected");
    }
}

function createObjectLink(parent, obj, text) {
    if (text == null) {
        text = obj.name;
    }

    if (text == null) {
        text = "-";
    }

    return gesso.createLink(parent, obj.html_url, text);
}

function renderRunLinks(parent, run) {
    let data_url = "pretty?url=" + encodeURIComponent(run.data_url);

    gesso.createLink(parent, data_url, "Data");
    gesso.createText(parent, ", ");

    if (run.tests_url == null) {
        gesso.createSpan(parent, "disabled", "Tests");
    } else {
        gesso.createLink(parent, run.tests_url, "Tests");
    }
}

function renderPanelView(parent) {
    let elem = gesso.createDiv(parent, "panel");

    let groups = state.data.groups;
    let categories = state.data.categories;
    let jobs = state.data.jobs;

    let selection = state.query.category;

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
            renderJob(jobContainer, job);
        }
    }
}

function renderJob(parent, job) {
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
        "agent": getName(state.data.agents[job.agent_id]),
        "name": job.name,
        "variant": job.variant,
    }

    let summary = gesso.createLink(elem, job.html_url, {"class": "job-summary"});

    const group = state.data.groups[job.group_id];

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
        ago = state.renderTime - currRun.start_time;
    }

    gesso.createDiv(summary, "summary-start-time", gesso.formatDurationBrief(ago));

    renderJobDetail(elem, job);
}

function renderJobDetail(parent, job) {
    let elem = gesso.createDiv(parent, "job-detail");

    let agent = state.data.agents[job.agent_id];
    let currRun = job.current_run;
    let prevRun = job.previous_run;

    let table = gesso.createElement(elem, "table");
    let tbody = gesso.createElement(table, "tbody");
    let td;

    td = createJobDetailField(tbody, "Agent");
    createObjectLink(td, agent);

    td = createJobDetailField(tbody, "Job");
    createObjectLink(td, job);

    if (currRun != null) {
        let ago = "-";

        if (currRun.start_time != null) {
            let millisAgo = state.renderTime - currRun.start_time;
            ago = gesso.formatDurationBrief(millisAgo) + " ago";
        }

        let duration = gesso.formatDurationBrief(currRun.duration);

        td = createJobDetailField(tbody, "Run");
        createObjectLink(td, currRun, currRun.number);

        createJobDetailField(tbody, "Start time", ago);
        createJobDetailField(tbody, "Duration", duration);
        createJobDetailField(tbody, "Status", currRun.status);

        if (prevRun == null) {
            createJobDetailField(tbody, "Prev status", "-");
        } else {
            createJobDetailField(tbody, "Prev status", prevRun.status);
        }

        td = createJobDetailField(tbody, "Links");
        renderRunLinks(td, currRun);
    }
}

function createJobDetailField(parent, name, text) {
    let tr = gesso.createElement(parent, "tr");
    let th = gesso.createElement(tr, "th", name);
    let td = gesso.createElement(tr, "td", text);

    return td;
}

function renderTableView(parent) {
    let elem = gesso.createElement(parent, "table",
                                   {"class": "jobs", "data-sortable": "data-sortable"});

    let thead = gesso.createElement(elem, "thead");
    let tr = gesso.createElement(thead, "tr");

    gesso.createElement(tr, "th", "Agent");
    gesso.createElement(tr, "th", "Group");
    gesso.createElement(tr, "th", "Name");
    gesso.createElement(tr, "th", "Variant");
    gesso.createElement(tr, "th", "Latest run");
    gesso.createElement(tr, "th", "Start time");
    gesso.createElement(tr, "th", "Duration");
    gesso.createElement(tr, "th", "Status");
    gesso.createElement(tr, "th", "Prev status");
    gesso.createElement(tr, "th", "Links");

    let tbody = gesso.createElement(elem, "tbody");

    let jobs = state.data.jobs;
    let groups = state.data.groups;
    let categories = state.data.categories;
    let agents = state.data.agents;

    let selection = state.query.category;

    for (let jobId of Object.keys(jobs)) {
        let job = jobs[jobId];
        let group = groups[job.group_id];
        let category = categories[group.category_id];

        if (selection !== "all" && selection !== category.key) {
            continue;
        }

        let agent = agents[job.agent_id];
        let currRun = job.current_run;
        let prevRun = job.previous_run;

        let tr = gesso.createElement(tbody, "tr");
        let td;

        td = gesso.createElement(tr, "td");
        createObjectLink(td, agent);

        gesso.createElement(tr, "td", group.name);

        td = gesso.createElement(tr, "td");
        createObjectLink(td, job);

        gesso.createElement(tr, "td", job.variant || "-");

        if (currRun) {
            let duration = gesso.formatDurationBrief(currRun.duration);
            let ago = "-";
            let prevRunStatus = "-";

            if (currRun.start_time) {
                let millisAgo = state.renderTime - currRun.start_time;
                ago = gesso.formatDurationBrief(millisAgo) + " ago";
            }

            if (prevRun) {
                prevRunStatus = prevRun.status;
            }

            td = gesso.createElement(tr, "td");
            createObjectLink(td, currRun, currRun.number);

            gesso.createElement(tr, "td", {text: ago, "data-value": currRun.start_time});
            gesso.createElement(tr, "td", {text: duration, "data-value": currRun.duration});
            gesso.createElement(tr, "td", currRun.status);
            gesso.createElement(tr, "td", prevRunStatus);

            td = gesso.createElement(tr, "td");
            renderRunLinks(td, currRun);
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
