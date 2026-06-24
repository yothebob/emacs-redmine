#!/usr/bin/python

import logging
import os
import sys
import tempfile
import argparse
import settings
from redmine_api import *
from genshi.template import NewTextTemplate
import csv

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(f"{settings.PROJECT_PATH}/logs/redmine.log"),
        logging.StreamHandler()
    ]
)


class Org:

    root_folder = os.path.dirname(os.path.realpath(__file__))
    template_folder = os.path.join(root_folder, "templates")

    def __init__(self, redmine, args):
        self.redmine = redmine
        self.args = args

    def get_setting_statuses(self, **kwargs):
        res = "(setq *API-REDMINE-STATUSES* '("+ " ".join([f"( \"{name}\" . {_id})" for _id, name in settings.STATUSES.items()]) + "))"
        logger.info(res)
        return res

    def get_setting_users(self, **kwargs):
        res = "(setq *ASSIGNEE* '("+ " ".join([f"( \"{name}\" . {_id})" for _id, name in settings.USERS.items()]) + "))"
        logger.info(res)
        return res

    def test_function(self, **kwargs):
        logger.info("kwargs", kwargs)
        return "DONE"
    
        
    def sprints(self, **kwargs):
        sprints = self.redmine.getVersions(kwargs["project"])
        logger.info(self._process_template("sprints.org", project=kwargs["project"], sprints=sprints))

    def everything(self, **kwargs):
        sprints = self.redmine.getVersions(kwargs["project"])

        for sprint in sprints:
            sprint.issues = self.redmine.findIssues(
                get_all_info=True,
                project_id=kwargs["redmine_project"],
                include="journals",
                sort="position",
                tracker_id=settings.TRACKER_SPRINT,
                fixed_version_id=sprint.id,
                status_id="*",
                limit=900,
            )

            for issue in sprint.issues:
                tasks = []
                for child in issue.children:
                    tasks.append(self.redmine.getIssue(child["id"]))
                issue.tasks = tasks

        logger.info(
            self._process_template("everything.org", project=kwargs["project"], sprints=sprints)
        )

    def everything_for_sprint(self, **kwargs):
        if kwargs["sprint_id"] is None:
            raise Exception("sprint must be specified")

        sprints = self.redmine.getVersions(kwargs["project"])
        for sprint in sprints:
            if sprint.id == kwargs["sprint_id"]:
                break

        sprint.issues = self.redmine.findIssues(
            get_all_info=True,
            project_id=kwargs["redmine_project"],
            include="journals",
            sort="position",
            tracker_id=settings.TRACKER_SPRINT,
            fixed_version_id=sprint.id,
            status_id="*",
            limit=900,
        )

        for issue in sprint.issues:
            tasks = []
            for child in issue.children:
                tasks.append(self.redmine.getIssue(child["id"]))
            issue.tasks = tasks
            if issue.status["name"] == "New":
                issue.status["org_name"] = "TODO"
            else:
                issue.status["org_name"] = "DONE"

        logger.info(
            self._process_template(
                "everything_sprint.org", project=kwargs["project"], sprint=sprint
            )
        )

    # def time_sheet(self, project, sprint): 
    #     if sprint is None:
    #         raise Exception("sprint must be specified")
    #     timesheets = self.redmine.timesheets(project, fixed_version_id=sprint)
    #     timesheet_content = self._process_template(
    #         "timesheets.org", timesheets=timesheets, project=project, sprint=sprint
    #     )
    #     filename = "/home/gtp/temp/timesheet.csv"
    #     f = open(os.path.join(filename), "w")
    #     f.write(timesheet_content)
    #     logger.info("\nWritten to %s\n\n" % filename)
    #     logger.info(timesheet_content)

    def issues(self, **kwargs):
        """get_all_info=True is much slower since it makes an
        additional api call for each issue, only use it if you want
        each issue in full."""
        issues_per_page = 100
        offset = issues_per_page * (kwargs["page"] - 1)
        if kwargs["sprint"] is None:
            raise Exception("sprint must be specified")
        issues = self.redmine.findIssues(
            get_all_info=False,
            project_id=args.redmine_project,
            include="journals",
            sort="position",
            tracker_id=settings.TRACKER_SPRINT,
            fixed_version_id=kwargs["sprint"],
            status_id="*",
            limit=issues_per_page,
            offset=offset,
        )
        logger.info(self._process_template("issues.org", sprint=kwargs["sprint"], issues=issues))

    def assigned_to_me(self, **kwargs):
        issues_per_page = 100
        offset = issues_per_page * (kwargs["page"] - 1)
        issues = self.redmine.findIssues(
            get_all_info=False,
            assigned_to_id="me",
            status_id="o",
            limit=issues_per_page,
        )
        logger.info(self._process_template("issues.org", sprint=kwargs["sprint"], issues=issues))


        
    def issue(self, **kwargs):
        issue = self.redmine.getIssue(kwargs["issue"])
        logger.info(self._process_template("issue.org", issue=issue, key=self.redmine.key))

    def new_issue(self, **kwargs):

        subject = self._read_argument("Subject")
        description = self._read_argument("Description", multi_line=True)
        tracker_name = "feature"

        if kwargs["sprint"] is None:
            raise Exception("sprint must be specified")
        self.redmine.new_issue(
            kwargs["project"],
            fixed_version_id=kwargs["sprint"],
            tracker_name=tracker_name,
            subject=subject,
            description=description,
        )
        logger.info("Issue created")

    def edit_issue(self, **kwargs):
        if kwargs["issue"] is None:
            raise Exception("issue must be specified")

        args = {}
        issue = self.redmine.getIssue(kwargs["issue"])
        logger.info("")
        logger.info("---------------------------------------")
        logger.info("Current subject is : \n %s" % issue.subject)
        logger.info("---------------------------------------")
        logger.info("")
        self._set_argument_or_ignore(
            args, "subject", prompt="Subject (leave blank to ignore)"
        )

        logger.info("")
        logger.info("---------------------------------------")
        logger.info("Current description is :\n %s" % issue.description)
        logger.info("---------------------------------------")
        logger.info("")
        self._set_argument_or_ignore(
            args,
            "description",
            prompt="Description (leave blank to ignore, type 'plus' (without quotes) on a line by itself to insert the existing description at that point)",
            multi_line=True,
        )

        if args["description"].startswith("plus\n"):
            args["description"] = (
                issue.description + args["description"][len("plus\n") :]
            )
        args["description"] = args["description"].replace(
            "\nplus\n", "\n%s\n" % issue.description
        )
        self.redmine.updateIssueFromDict(kwargs["issue"], args)
        logger.info("Issue %s updated" % str(kwargs["issue"]))

    def set_issue_status(self, **kwargs):
        if kwargs["status"] is None:
            raise Exception("Status must be specified")
        if kwargs["status"] not in settings.STATUSES.values():
            raise Exception(f"Status must be in {', '.join(settings.STATUSES.values())}")
        self.redmine.updateIssueFromDict(kwargs["issue"], status_id=settings.STATUSES_REVERSED[kwargs["status"]])
        logger.info("Issue status changed to " + kwargs["status"])

    def _process_template(self, template_filename, **kwargs):
        f = open(os.path.join(self.template_folder, template_filename))
        template_text = f.read()
        template = NewTextTemplate(template_text)
        f.close()
        stream = template.generate(**kwargs)
        return stream.render()

    def _read_multiline_input(self, prompt):
        user_input = []
        entry = input(prompt + "\n(enter 'done' on its own line when done) \n\n")
        while entry != "done":
            user_input.append(entry)
            entry = input("")
        user_input = "\n".join(user_input)
        return user_input

    def _read_argument(self, prompt, multi_line=False):
        if not multi_line:
            return input(prompt + ": ")
        else:
            return self._read_multiline_input(prompt)
            # t = tempfile.NamedTemporaryFile(delete=False)
            # try:
            #     editor = os.environ['EDITOR']
            # except KeyError:
            #     editor = 'nano'
            #     subprocess.call([editor, t.name])
            # return t.read()

    def _set_argument_or_ignore(self, args_dict, arg_name, *args, **kwargs):
        v = self._read_argument(*args, **kwargs)
        if v is None or len(str(v).strip()) == 0:
            return
        args_dict[arg_name] = v

        
    # I do not use this
    # def delete_issue(self, **kwargs):
    #     if kwargs["issue"] is None:
    #         raise Exception("issue must be specified")

    #     confirm = self._read_argument(
    #         "Are you sure you want to delete issue "
    #         + str(kwargs["issue"])
    #         + "? (type yes to confirm) : "
    #     )
    #     if str(confirm) != "yes":
    #         return

    #     self.redmine.deleteIssue(kwargs["issue"])
    #     logger.info("Issue %s deleted" % str(kwargs["issue"]))

    def add_issue_journal(self, **kwargs):
        if kwargs["issue"] is None:
            raise Exception("issue must be specified")

        args = {}
        args["notes"] = kwargs["note"]
        if kwargs["status"]:
            if kwargs["status"] not in settings.STATUSES.values():
                raise Exception(f"Status must be in {', '.join(settings.STATUSES.values())}")
            args["status_id"] = settings.STATUSES_REVERSED[kwargs["status"]]

        if kwargs["branch"]:
            args["custom_fields"] = [{"value":kwargs["branch"], "name":"Branch", "id": 3}]
            # args["branch"] = kwargs["branch"]
        if kwargs["assignee"]:    
            if kwargs["assignee"] not in settings.USERS.values():
                raise Exception(f"Status must be in {', '.join(settings.USERS.values())}")
            args["assigned_to_id"] = settings.USERS_REVERSED[kwargs["assignee"]]
        logger.info(kwargs["issue"], args)
        self.redmine.update_issue_with_json(kwargs["issue"], **args)
        logger.info("Issue journal entry created for %s" % str(kwargs["issue"]))






if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "--url", dest="redmine_url", type=str, required=False, help="the url to redmine"
    )
    parser.add_argument(
        "--userkey",
        dest="redmine_login_key",
        type=str,
        required=False,
        help='the user key to redmine, can be found on the right of the "my account" page in redmine.',
    )
    parser.add_argument(
        "--project",
        dest="project",
        type=str,
        required=False,
        help="the project name",
    )
    parser.add_argument(
        "--action",
        dest="action",
        type=str,
        required=True,
        help="""What to do, one of: issues issue new-issue set-issue-status versions (and probably more)""",
    )
    parser.add_argument(
        "--sprint",
        dest="sprint",
        type=str,
        required=False,
        default=None,
        help="The sprint id, used for some actions",
    )
    parser.add_argument(
        "--page",
        dest="page",
        type=int,
        required=False,
        default=1,
        help="The page number, used when viewing issues in a sprint",
    )
    parser.add_argument(
        "--issue",
        dest="issue",
        type=str,
        required=False,
        default=None,
        help="The issue id, used for some actions",
    )
    parser.add_argument(
        "--status",
        dest="status",
        type=str,
        required=False,
        default=None,
        help="The status name, used for some actions. One of new, devdone, tested, reopened",
    )
    parser.add_argument(
        "--assignee",
        dest="assignee",
        type=str,
        required=False,
        default=None,
        help="to assign to, not their id but their name",
    )
    parser.add_argument(
        "--note",
        dest="note",
        type=str,
        required=False,
        default=None,
        help="journal entry",
    )
    parser.add_argument(
        "--branch",
        dest="branch",
        type=str,
        required=False,
        default=None,
        help="git branch",
    )
    args = parser.parse_args()

    redmine = Redmine(url=args.redmine_url, key=args.redmine_login_key, debug=True)

    org = Org(redmine, args)

    action_to_func_map = {
        "test" : org.test_function,
        "issues" : org.issues,
        "statuses" : org.get_setting_statuses,
        "users" : org.get_setting_users,
        "everything" : org.everything,
        "everything-sprint" : org.everything_for_sprint,
        "issue" : org.issue,
        "new-issue" : org.new_issue,
        "edit-issue" : org.edit_issue,
        "assigned-to-me": org.assigned_to_me,
        # "time-sheet" : org.time_sheet,
        # "delete-issue" : org.delete_issue(args.issue)
        "add-issue-journal" : org.add_issue_journal,
        # "sprints" : org.sprints(args.redmine_project)
        "set-issue-status" : org.set_issue_status
    }
    if args.action not in action_to_func_map.keys():
        raise Exception("Unknown action : " + args.action)
    action_to_func_map[args.action](**vars(args))
