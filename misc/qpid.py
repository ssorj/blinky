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

from blinky.appveyor import *
from blinky.jenkins import *
from blinky.travis import *

http_port = 56720

# Components

dispatch = Component(model, "Dispatch")
proton_c = Component(model, "Proton C")
proton_j = Component(model, "Proton J")
qpid_cpp = Component(model, "Qpid C++")
qpid_java = Component(model, "Qpid Java")
qpid_jms = Component(model, "Qpid JMS")

# Environments

fedora = Environment(model, "Fedora")
java_7 = Environment(model, "Java 7")
java_8 = Environment(model, "Java 8")
rhel_5 = Environment(model, "RHEL 5")
rhel_6 = Environment(model, "RHEL 6")
rhel_7 = Environment(model, "RHEL 7")
ubuntu = Environment(model, "Ubuntu")
ubuntu_lts = Environment(model, "Ubuntu LTS")
windows = Environment(model, "Windows")

# Agents

asf_jenkins = JenkinsAgent(model, "ASF Jenkins", "https://builds.apache.org")
travis = TravisAgent(model, "Travis CI")
appveyor = AppveyorAgent(model, "Appveyor")

# Qpid brokers

group = Group(model, "Qpid brokers")

JenkinsJob(model, group, qpid_java, java_7, asf_jenkins, "Test",       "Qpid-Java-Java-Test-IBMJDK1.7")
JenkinsJob(model, group, qpid_java, java_8, asf_jenkins, "Test",       "Qpid-Java-Java-Test-JDK1.8")
JenkinsJob(model, group, qpid_java, java_7, asf_jenkins, "C++ broker", "Qpid-Java-Cpp-Test")
JenkinsJob(model, group, qpid_java, java_7, asf_jenkins, "Deploy",     "Qpid-Java-Artefact-Release")
JenkinsJob(model, group, qpid_java, java_7, asf_jenkins, "Joram",      "Qpid-Java-JoramJMSTest")
JenkinsJob(model, group, qpid_java, java_7, asf_jenkins, "MMS",        "Qpid-Java-Java-MMS-TestMatrix")
JenkinsJob(model, group, qpid_java, java_8, asf_jenkins, "BDB",        "Qpid-Java-Java-BDB-TestMatrix")
JenkinsJob(model, group, qpid_cpp,  ubuntu, asf_jenkins, "Test",       "Qpid-cpp-trunk-test")

# Qpid JMS

group = Group(model, "Qpid JMS")

JenkinsJob (model, group, qpid_jms, java_7, asf_jenkins, "Test",        "Qpid-JMS-Test-JDK7")
JenkinsJob (model, group, qpid_jms, java_8, asf_jenkins, "Test",        "Qpid-JMS-Test-JDK8")
TravisJob  (model, group, qpid_jms, java_7, travis,      "Test",        "apache/qpid-jms", "master")
AppveyorJob(model, group, qpid_jms, java_7, appveyor,    "Test",        "stumped2", "qpid-jms", "master")
JenkinsJob (model, group, qpid_jms, java_7, asf_jenkins, "Deploy",      "Qpid-JMS-Deploy")
JenkinsJob (model, group, qpid_jms, java_8, asf_jenkins, "Extra tests", "Qpid-JMS-Checks")

# Qpid Proton

group = Group(model, "Qpid Proton")

JenkinsJob (model, group, proton_c, ubuntu,     asf_jenkins, "Test",   "Qpid-proton-c")
TravisJob  (model, group, proton_c, ubuntu_lts, travis,      "Test",   "apache/qpid-proton", "master")
AppveyorJob(model, group, proton_c, windows,    appveyor,    "Test",   "ke4qqq", "qpid-proton", "master")
JenkinsJob (model, group, proton_j, java_7,     asf_jenkins, "Test",   "Qpid-proton-j")
JenkinsJob (model, group, proton_j, java_7,     asf_jenkins, "Deploy", "Qpid-proton-j-Deploy")
