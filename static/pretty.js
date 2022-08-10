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

const html = `
<body>
  <p><a id="link" href=""></a></p>

  <pre id="content" class="json">[Loading...]</pre>
</body>
`;

export class Page extends gesso.Page {
    constructor(router) {
        super(router, "/pretty", html);
    }

    update() {
        const url = new URL(window.location.href).searchParams.get("url");
        const proxy = new URL("proxy?url=" + encodeURIComponent(url), window.location.href);
        const link = $("#link");
        let contentType;

        link.setAttribute("href", url);
        link.textContent = url;

        fetch(proxy, {
            method: "GET",
        })
            .then(response => {
                contentType = response.headers.get("Content-Type");
                return response.text()
            })
            .then(text => {
                if (contentType.indexOf("text/json") === 0 || contentType.indexOf("application/json") === 0) {
                    const json = JSON.parse(text);

                    text = JSON.stringify(json, null, 4);
                    text = hljs.highlight(text, {language: "json"}).value;
                    text = text.replace(/&quot;(https?:\/\/.*?)&quot;/g, "&quot;<a href=\"pretty?url=$1\">$1</a>&quot;");
                }

                try {
                    $("#content").innerHTML = text;
                } catch (e) {
                    $("#content").textContent = "[Error! The data isn't what I expected]";
                }
            })
            .catch(error => {
                $("#content").textContent = "[Error! My request for data failed]";
            });
    }
}
