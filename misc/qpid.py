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

cpp_group = TestGroup(model, "Qpid C++")
java_group = TestGroup(model, "Qpid Java")
#dispatch_group = TestGroup(model, "Qpid Dispatch")
jms_group = TestGroup(model, "Qpid JMS")
proton_group = TestGroup(model, "Qpid Proton")

dispatch = Component(model, "Dispatch")
proton_c = Component(model, "Proton C")
proton_j = Component(model, "Proton J")
qpid_cpp = Component(model, "Qpid C++")
qpid_java = Component(model, "Qpid Java")
qpid_jms = Component(model, "Qpid JMS")

fedora = Environment(model, "Fedora")
java_7 = Environment(model, "Java 7")
java_8 = Environment(model, "Java 8")
rhel_5 = Environment(model, "RHEL 5")
rhel_6 = Environment(model, "RHEL 6")
rhel_7 = Environment(model, "RHEL 7")
ubuntu = Environment(model, "Ubuntu")
ubuntu_lts = Environment(model, "Ubuntu LTS")
windows = Environment(model, "Windows")

asf_jenkins = JenkinsAgent(model, "ASF Jenkins", "https://builds.apache.org")
travis = TravisAgent(model, "Travis CI", "https://api.travis-ci.org")
appveyor = AppveyorAgent(model, "Appveyor", "https://ci.appveyor.com")

# Qpid C++

test = Test(model, cpp_group, qpid_cpp)

JenkinsJob(model, asf_jenkins, test, ubuntu, "Qpid-cpp-trunk-test")

# Qpid Java

test = Test(model, java_group, qpid_java)

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-Java-Java-Test-IBMJDK1.7")
JenkinsJob(model, asf_jenkins, test, java_8, "Qpid-Java-Java-Test-JDK1.8")

test = Test(model, java_group, qpid_java, "Joram")

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-Java-JoramJMSTest")

test = Test(model, java_group, qpid_java, "BDB")

JenkinsJob(model, asf_jenkins, test, java_8, "Qpid-Java-Java-BDB-TestMatrix")

test = Test(model, java_group, qpid_java, "MMS")

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-Java-Java-MMS-TestMatrix")

test = Test(model, java_group, qpid_java, "C++ broker")

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-Java-Cpp-Test")

test = Test(model, java_group, qpid_java, "Deploy")

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-Java-Artefact-Release")

# Qpid JMS

test = Test(model, jms_group, qpid_jms)

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-JMS-Test-JDK7")
TravisJob(model, travis, test, java_7, "apache/qpid-jms", "master")
AppveyorJob(model, appveyor, test, java_7, "stumped2", "qpid-jms", "master")
JenkinsJob(model, asf_jenkins, test, java_8, "Qpid-JMS-Test-JDK8")

test = Test(model, jms_group, qpid_jms, "Extra tests")

JenkinsJob(model, asf_jenkins, test, java_8, "Qpid-JMS-Checks")

test = Test(model, jms_group, qpid_jms, "Deploy")

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-JMS-Deploy")

# Qpid Proton

test = Test(model, proton_group, proton_c)

JenkinsJob(model, asf_jenkins, test, ubuntu, "Qpid-proton-c")
TravisJob(model, travis, test, ubuntu_lts, "apache/qpid-proton", "master")
AppveyorJob(model, appveyor, test, windows, "ke4qqq", "qpid-proton", "master")

test = Test(model, proton_group, proton_j)

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-proton-j")

test = Test(model, proton_group, proton_j, "Deploy")

JenkinsJob(model, asf_jenkins, test, java_7, "Qpid-proton-j-Deploy")
