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

http_port = 8000

model.title = "Apache Qpid CI"

# Components

dispatch = Component(model, "Dispatch")
proton_c = Component(model, "Proton C")
proton_j = Component(model, "Proton J")
qpid_cpp = Component(model, "Qpid C++")
qpid_python = Component(model, "Qpid Python")
qpid_java = Component(model, "Qpid for Java")
qpid_jms = Component(model, "Qpid JMS")

# Environments

centos_6 = Environment(model, "CentOS 6")
centos_7 = Environment(model, "CentOS 7")
fedora = Environment(model, "Fedora")
ubuntu_12_lts = Environment(model, "Ubuntu 12 LTS")
ubuntu_14_lts = Environment(model, "Ubuntu 14 LTS")
ubuntu_16_lts = Environment(model, "Ubuntu 16 LTS")
ubuntu_lts = Environment(model, "Ubuntu LTS")
windows = Environment(model, "Windows")

# Agents

asf_jenkins = JenkinsAgent(model, "ASF Jenkins", "https://builds.apache.org")
travis = TravisAgent(model, "Travis CI")
appveyor = AppveyorAgent(model, "Appveyor")

# Jobs

group = Group(model, "Qpid JMS")

JenkinsJob (model, group, qpid_jms,     ubuntu_lts,     asf_jenkins,      "ASF Jenkins",             "Qpid-JMS-Test-JDK8")
TravisJob  (model, group, qpid_jms,     ubuntu_12_lts,  travis,           "Travis CI",               "apache/qpid-jms", "master")
AppveyorJob(model, group, qpid_jms,     windows,        appveyor,         "Appveyor",                "stumped2", "qpid-jms", "master")
JenkinsJob (model, group, qpid_jms,     ubuntu_lts,     asf_jenkins,      "Regression",              "Qpid-JMS-Checks")
JenkinsJob (model, group, qpid_jms,     ubuntu_lts,     asf_jenkins,      "Deploy",                  "Qpid-JMS-Deploy")

group = Group(model, "Qpid Proton")

JenkinsJob (model, group, proton_c,     ubuntu_lts,     asf_jenkins,      "ASF Jenkins",             "Qpid-proton-c")
TravisJob  (model, group, proton_c,     ubuntu_12_lts,  travis,           "Travis CI",               "apache/qpid-proton", "master")
AppveyorJob(model, group, proton_c,     windows,        appveyor,         "Appveyor",                "ke4qqq", "qpid-proton", "master")
JenkinsJob (model, group, proton_j,     ubuntu_lts,     asf_jenkins,      "ASF Jenkins",             "Qpid-proton-j")
TravisJob  (model, group, proton_j,     ubuntu_12_lts,  travis,           "Travis CI",               "apache/qpid-proton-j", "master")
AppveyorJob(model, group, proton_j,     windows,        appveyor,         "Appveyor",                "ApacheSoftwareFoundation", "qpid-proton-j", "master")
JenkinsJob (model, group, proton_j,     ubuntu_lts,     asf_jenkins,      "Regression",              "Qpid-proton-j-Checks")
JenkinsJob (model, group, proton_j,     ubuntu_lts,     asf_jenkins,      "Deploy",                  "Qpid-proton-j-Deploy")

group = Group(model, "Qpid for Java")

JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "OpenJDK 8",               "Qpid-Java-Java-Test-JDK1.8")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "IBM JDK 8",               "Qpid-Java-Java-Test-IBMJDK1.8")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "Python",                  "Qpid-Python-Java-Test")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "C++",                     "Qpid-Java-Cpp-Test")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "Joram",                   "Qpid-Java-JoramJMSTest")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "MMS",                     "Qpid-Java-Java-MMS-TestMatrix")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "BDB",                     "Qpid-Java-Java-BDB-TestMatrix")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "Regression",              "Qpid-Java-Checks")
JenkinsJob (model, group, qpid_java,    ubuntu_lts,     asf_jenkins,      "Deploy",                  "Qpid-Java-Artefact-Release")

group = Group(model, "Qpid C++")

JenkinsJob (model, group, qpid_cpp,     ubuntu_lts,     asf_jenkins,      "Test",                    "Qpid-cpp-trunk-test")

# group = Group(model, "Qpid Dispatch")
# group = Group(model, "Qpid Python")
