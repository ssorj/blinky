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
    etag: null,
    updateInterval: 10000,

    sendRequest: function(url, handler) {
        var request = new XMLHttpRequest();
        
        request.onreadystatechange = function() {
            if (request.readyState == 4 && request.status == 200) {
                handler(request);
                blinky.etag = request.getResponseHeader("ETag");
            }
        };

        request.open("GET", url);

        if (blinky.etag !== null) {
            request.setRequestHeader("If-None-Match", blinky.etag);
        }
        
        request.send(null);
    },

    createChild: function(parent, tag) {
        var child = document.createElement(tag);

        parent.appendChild(child);

        return child;
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

    renderLights: function(request) {
        var data = JSON.parse(request.responseText);

        var oldContent = $("#content");
        var newContent = document.createElement("div");
        newContent.setAttribute("id", "content");
        
        var testGroups = data["test_groups"];
        
        for (var testGroupId in testGroups) {
            var testGroup = testGroups[testGroupId];

            var groupElem = blinky.createChild(newContent, "div");
            groupElem.setAttribute("class", "test-group");
            
            var h2 = blinky.createChild(groupElem, "h2");
            h2.textContent = testGroup.name;

            var containerElem = blinky.createChild(groupElem, "div");
            containerElem.setAttribute("class", "result-container");

            var testIds = testGroup["test_ids"];
            
            for (var j = 0; j < testIds.length; j++) {
                var test = data["tests"][testIds[j]];
                var jobIds = test["job_ids"];

                for (var k = 0; k < jobIds.length; k++) {
                    var job = data["jobs"][jobIds[k]];

                    var resultElem = blinky.createResultElement(data, job);
                    containerElem.appendChild(resultElem);
                }
            }
        }

        oldContent.parentNode.replaceChild(newContent, oldContent);
    },

    createResultElement: function(data, agent) {
        var test = data.tests[agent.test_id];
        var component = data.components[test.component_id];
        var environment = data.environments[agent.environment_id];
        var currentResult = agent.current_result;
        var previousResult = agent.previous_result;

        var elem = document.createElement("a");
        elem.setAttribute("class", "result-item");
        elem.setAttribute("href", agent.url);
        elem.setAttribute("target", "_parent");

        var summary = blinky.createChild(elem, "div");
        summary.setAttribute("class", "result-summary");
        
        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-item summary-title");
        field.textContent = component.name;

        if (test.name) {
            var field = blinky.createChild(summary, "div");
            field.setAttribute("class", "summary-item");
            field.textContent = test.name;
        }

        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-item");
        field.textContent = environment.name;

        if (!currentResult) {
            return elem;
        }

        elem.setAttribute("href", currentResult.url);

        var secondsNow = new Date().getTime() / 1000;
        var secondsAgo = secondsNow - currentResult.timestamp;
        
        if (currentResult.status === "SUCCESS") {
            elem.setAttribute("class", "result-item success");
        } else if (currentResult.status === "FAILURE") {
            if (previousResult && previousResult.status === "SUCCESS") {
                elem.setAttribute("class", "result-item failure blinky");
            } else {
                elem.setAttribute("class", "result-item failure");
            }
        } else if (currentResult.status === "UNSTABLE") {
            if (previousResult && previousResult.status === "STABLE") {
                elem.setAttribute("class", "result-item failure blinky");
            } else {
                elem.setAttribute("class", "result-item failure");
            }
        }

        var field = blinky.createChild(summary, "div");
        field.setAttribute("class", "summary-item summary-timestamp");
        field.textContent = blinky.formatDuration(secondsAgo);

        var detail = blinky.createDetailElement(data, agent);
        elem.appendChild(detail);

        return elem;
    },

    createDetailElement: function(data, agent) {
        var test = data.tests[agent.test_id];
        var component = data.components[test.component_id];
        var environment = data.environments[agent.environment_id];
        var currentResult = agent.current_result;
        var previousResult = agent.previous_result;

        var elem = document.createElement("div");
        elem.setAttribute("class", "result-detail");

        var table = blinky.createChild(elem, "table");
        var tbody = blinky.createChild(table, "tbody");

        var testName = test.name;

        if (!testName) {
            testName = "Main";
        }
        
        blinky.createDetailField(tbody, "Component", component.name);
        blinky.createDetailField(tbody, "Test", testName);
        blinky.createDetailField(tbody, "Environment", environment.name);

        if (currentResult) {
            var duration = blinky.formatDuration(currentResult.duration);
        
            var secondsNow = new Date().getTime() / 1000;
            var secondsAgo = secondsNow - currentResult.timestamp;
            var timeAgo = blinky.formatDuration(secondsAgo) + " ago";

            blinky.createDetailField(tbody, "Time", timeAgo);
            blinky.createDetailField(tbody, "Duration", duration);
            blinky.createDetailField(tbody, "Status", currentResult.status);

            if (previousResult) {
                blinky.createDetailField(tbody, "Previous status",
                                         previousResult.status);
            }
        }
        
        return elem;
    },

    createDetailField: function(tbody, name, value) {
        var tr = blinky.createChild(tbody, "tr");
        var th = blinky.createChild(tr, "th");
        var td = blinky.createChild(tr, "td");

        th.textContent = name;
        td.textContent = value;
    },

    renderTable: function(request) {
        var data = JSON.parse(request.responseText);

        var oldContent = $("#content");
        var newContent = document.createElement("tbody");
        newContent.setAttribute("id", "content");

        var secondsNow = new Date().getTime() / 1000;
        
        for (var jobId in data["jobs"]) {
            var job = data["jobs"][jobId];
            var currentResult = job["current_result"];
            var previousResult = job["previous_result"];
            var test = data["tests"][job["test_id"]]
            var testGroup = data["test_groups"][test["test_group_id"]]
            var component = data["components"][test["component_id"]]
            var environment = data["environments"][job["environment_id"]]
            var agent = data["agents"][job["agent_id"]]

            var time = "-";
            var duration = "-";
            var number = "-"
            var status = "-"
            var previousStatus = "-";
            
            if (currentResult !== null) {
                time = blinky.formatDuration(secondsNow - currentResult.timestamp);
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
            
            td = blinky.createChild(tr, "td");
            link = blinky.createChild(td, "a");
            link.setAttribute("href", "data.html?source=" + encodeURIComponent(job.url));
            link.textContent = job.name;
            
            blinky.createChild(tr, "td").textContent = component.name;
            blinky.createChild(tr, "td").textContent = environment.name;
            blinky.createChild(tr, "td").textContent = test.name ? test.name : "Main";
            blinky.createChild(tr, "td").textContent = time;
            blinky.createChild(tr, "td").textContent = duration;
            blinky.createChild(tr, "td").textContent = number;
            blinky.createChild(tr, "td").textContent = status;
            blinky.createChild(tr, "td").textContent = previousStatus;
            blinky.createChild(tr, "td").textContent = testGroup.name;

            td = blinky.createChild(tr, "td");
            link = blinky.createChild(td, "a");
            link.setAttribute("href", "data.html?source=" + encodeURIComponent(agent.url));
            link.textContent = agent.name;
        }
        
        oldContent.parentNode.replaceChild(newContent, oldContent);
    },
    
    updateLights: function() {
        blinky.sendRequest("data.json", blinky.renderLights);
    }, 

    updateTable: function() {
        blinky.sendRequest("data.json", blinky.renderTable);
    }
};
