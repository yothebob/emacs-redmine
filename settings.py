# Database IDs for statuses
import logging
import subprocess
import json

project_path_cmd = subprocess.run(["emacsclient", "-e", "(message redmine-path)"], capture_output=True)
PROJECT_PATH = project_path_cmd.stdout.decode("utf8").replace("\"","").replace("\n", "")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(f"{PROJECT_PATH}/logs/settings.log"),
        logging.StreamHandler()
    ]
)

STATUSES = {}
STATUSES_REVERSED = {}
USERS = {}
USERS_REVERSED = {}
URL = ""

try:
    with open(f"{PROJECT_PATH}/config.json", 'r', encoding='utf-8') as file:
        data = json.load(file)
        STATUSES = {int(k) : v for k, v in data.get("STATUSES", STATUSES).items()}
        USERS = {int(k) : v for k, v in data.get("USERS", USERS).items()}
        URL = data.get("URL", URL)
except Exception as e:
    logger.error(e)


STATUSES_REVERSED = {v: k for k, v in STATUSES.items()}    
USERS_REVERSED = {v: k for k, v in USERS.items()}

ISSUE_STATUS_NEW = 1
ISSUE_STATUS_REOPENED = 4
ISSUE_STATUS_DEV_DONE = 5
ISSUE_STATUS_TESTED = 7
ISSUE_STATUS_CANT_REPRODUCE = 12

TRACKER_BUG = 1
TRACKER_SPRINT = TRACKER_FEATURE = 2
TRACKER_TASK = TRACKER_SUPPORT = 3

TRACKERS = {"bug": TRACKER_BUG, "feature": TRACKER_FEATURE, "task": TRACKER_TASK}
