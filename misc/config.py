from blinky.appveyor import *
from blinky.circleci import *
from blinky.github import *
from blinky.jenkins import *
from blinky.travisci import *

http_port = 8080

model.title = "Test CI"

# Components

proton_c = Component(model, "Proton C")

# Environments

multiple = Environment(model, "Multiple OSes")

# Agents

github = GitHubAgent(model, "GitHub")

# Categories

client_tests = Category(model, "Clients", "client")

# Groups

group = Group(model, client_tests, "Proton C")

# To look up GitHub Actions workflow IDs:
# curl https://api.github.com/repos/apache/qpid-proton/actions/workflows

GitHubJob  (model, group, proton_c,         multiple,       github,           None,                         "apache/qpid-proton", "master", "Build", 2012003)
