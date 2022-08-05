from blinky.appveyor import *
from blinky.circleci import *
from blinky.github import *
from blinky.jenkins import *
from blinky.travisci import *

http_port = 8080

model.title = "Test CI"

appveyor = AppVeyorAgent(model, "AppVeyor")
asf_jenkins = JenkinsAgent(model, "ASF Jenkins", "https://ci-builds.apache.org/job/Qpid")
circleci = CircleCiAgent(model, "CircleCI")
github = GitHubAgent(model, "GitHub")
travis_ci = TravisCiAgent(model, "Travis CI", html_url="https://travis-ci.com/github", token="HFsJh03_8VhtMDGv8w4e2Q")

category = Category(model, "Clients", "client")

group = Group(category, "Proton C")

GitHubJob(github, group, "apache/qpid-proton", "main", "build.yml")
TravisCiJob(travis_ci, group, "apache/qpid-proton", "main")

group = Group(category, "Qpid JMS")

JenkinsJob(asf_jenkins, group, "Qpid-JMS-Test-JDK11", name="Test", variant="Java 11")
AppVeyorJob(appveyor, group, "ApacheSoftwareFoundation", "qpid-jms", "main", variant="Windows")

category = Category(model, "Skupper", "skupper")

group = Group(category, "Skupper")

CircleCiJob(circleci, group, "gh/skupperproject/skupper", "master")
