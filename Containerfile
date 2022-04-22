#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

FROM registry.fedoraproject.org/fedora-minimal AS build

RUN microdnf -y install findutils make python3 && microdnf clean all

COPY . /src

RUN mkdir /app
ENV HOME=/app

WORKDIR /src

RUN ./plano install --clean --prefix /app

FROM registry.fedoraproject.org/fedora-minimal

RUN microdnf -y install python3-certifi python3-requests python3-tornado && microdnf clean all

COPY --from=build /app /app

COPY misc/config.py /etc/blinky/config.py

WORKDIR /app
ENV HOME=/app
ENV PATH=$HOME/bin:$PATH

EXPOSE 8080

CMD ["blinky"]
