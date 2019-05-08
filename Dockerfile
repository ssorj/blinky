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

FROM registry.fedoraproject.org/fedora-minimal

RUN microdnf --nodocs install findutils make python2 python3-requests python3-tornado && microdnf clean all

COPY . /app/src
ENV HOME=/app

WORKDIR /app/src
RUN make clean install INSTALL_DIR=/app

RUN chown -R 1001:0 /app && chmod -R 775 /app
USER 1001

WORKDIR /app
ENV PATH=/app/bin:$PATH

EXPOSE 8080

CMD ["blinky"]
