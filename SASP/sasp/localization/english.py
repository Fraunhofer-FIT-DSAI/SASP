def _returnText(message):
    """Returns a lambda function that returns 'message' when called."""

    return lambda: message


def _formattedText(message):
    """Returns a lambda function that returns 'message' when called."""

    return lambda *args: message.format(*args)


def _returnDict(message_dict):
    """Returns a lambda function that returns 'message_dict' when called."""

    return lambda: message_dict


def _returnFromDisk(path_file, path_value):
    """
    Returns a lambda function that returns 'message' when called.
    Reads the message from a file on disk.
    Currently unused, but added if scalability is needed.
    """


class AttrDict(dict):
    """Dictionary subclass whose entries can be accessed by attributes
    (as well as normally).
    """

    def __init__(self, *args, **kwargs):
        def from_nested_dict(data):
            """Construct nested AttrDicts from nested dictionaries."""
            if not isinstance(data, dict):
                return data
            else:
                return AttrDict({key: from_nested_dict(data[key]) for key in data})

        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

        for key in self.keys():
            self[key] = from_nested_dict(self[key])


class Labels:
    """
    This class contains all the labels that are displayed to the user, e.g. in buttons.
    Labels are accessed by nested attributes, e.g. Labels.page_not_found.
    Every label is a function that returns a string. Details e.g. formatted
    strings are passed as arguments to the function.
    """

    def get_common():
        """Returns a dictionary containing all the common labels."""
        return {
            x.split("__")[0]: Labels.common[x]()
            for x in Labels.common
            if x.endswith("__TXT")
        }

    common = AttrDict()
    common.home__TXT = _returnText("Home")
    common.submit__TXT = _returnText("Submit")

    sharing = AttrDict()
    sharing.misp = AttrDict()
    sharing.misp.export__TXT = _returnText("Export")
    sharing.misp.import__TXT = _returnText("Import")
    sharing.misp.view_external__TXT = _returnText("View on MISP")

    sharing.stix = AttrDict()
    sharing.stix.export__TXT = _returnText("Export")
    sharing.stix.import__TXT = _returnText("Import")


class Messages:
    """A class that contains all the messages that are displayed to the user.
    Messages are accessed by nested attributes, e.g. Messages.page_not_found.
    Every message is a function that returns a string. Details e.g. formatted
    strings are passed as arguments to the function.
    """

    def get_common():
        """Returns a dictionary containing all the common labels."""
        return {
            x.split("__")[0]: Messages.common[x]()
            for x in Messages.common
            if x.endswith("__TXT")
        }

    common = AttrDict()
    common.empty_record__TXT = _returnText("No records found")

    sharing = AttrDict()
    sharing.misp = AttrDict()
    sharing.misp.import_ = AttrDict()
    sharing.misp.import_.title__TXT = _returnText("MISP Import")
    sharing.misp.import_.details = AttrDict()
    sharing.misp.import_.details.title__TXT = _formattedText("MISP Event {}")
    sharing.misp.import_.prompt_for_name__TXT = _returnText("Please enter a name")
    sharing.misp.export = AttrDict()
    sharing.misp.export.title__TXT = _returnText("MISP Export")
    sharing.misp.errors = AttrDict()
    sharing.misp.errors.no_misp__TITLE = _returnText("No MISP instance connected")
    sharing.misp.errors.no_misp__TXT = _returnText(
        "You have not connected a MISP instance or the connection is not working. Please check the credentials in the config file."
    )
    sharing.misp.errors.export_failed__TITLE = _returnText("Export failed")
    sharing.misp.errors.export_failed__TXT = _returnText("Export to MISP failed")
    sharing.misp.errors.import_ = AttrDict()
    sharing.misp.errors.import_.name_exists__TITLE = _returnText("Name already exists")
    sharing.misp.errors.import_.name_exists__TXT = _formattedText("A playbook with the name '{}' already exists. Please choose a different name.")
    sharing.misp.errors.import_.page_exists__TXT = _returnText("A page with this name already exists")
    sharing.misp.errors.import_.playbook_exists__TXT = _returnText("A playbook with this name already exists")
    sharing.misp.errors.import_.no_name__TXT = _returnText("Please enter a name")
    sharing.misp.errors.import_.invalid_name__TXT = _formattedText("Character '{}' is not allowed in name")
    sharing.misp.errors.import_.not_cacao__TXT = _returnText("This is not a CACAO playbook")
    sharing.misp.errors.import_.invalid_json__TXT = _returnText("Invalid JSON")
    sharing.misp.errors.import_.unsupported_version__TXT = _formattedText("Unsupported CACAO version: {}")
    sharing.misp.errors.import_.invalid_playbook__TITLE = _returnText("Can't import. Invalid playbook.")
    sharing.misp.errors.import_.import_failed__TITLE = _returnText("Import failed")
    sharing.misp.errors.import_.import_failed__TXT = _returnText("Import from MISP failed")

    sharing.misp.success = AttrDict()
    sharing.misp.success.export_success__TXT = _returnText("Export successful")
    sharing.misp.success.import_success__TXT = _returnText("Import successful")

    sharing.stix = AttrDict()
    sharing.stix.import_ = AttrDict()
    sharing.stix.import_.title__TXT = _returnText("STIX Import")
    sharing.stix.export = AttrDict()
    sharing.stix.export.title__TXT = _returnText("STIX Export")


class HelpTexts:
    index_page__OBJ = _returnDict(
        {
            "title": "Main Page",
            "content": "This is the main page. Below you see the list of all playbooks. You can click on a playbook to see its details. You can also create a new playbook by clicking on the 'New' button.",
        }
    )
    playbook = AttrDict()
    playbook.page = AttrDict()
    playbook.page__OBJ = _returnDict(
        {
            "title": "Playbook",
            "content": "This is a playbook page. To the left you see a list of all objects associated with this playbook and below you see the details of this playbook. To edit this playbook use the 'Edit' button to the left.",
        }
    )
    playbook.page.new = AttrDict()
    playbook.page.new.initial__OBJ = _returnDict(
        {
            "title": "Creation page",
            "content": """
            On this page you can create a new playbook or playbook object. Choose the form of the object you wish to create and give it a name. If you want to create a new playbook be sure to choose Playbook/CACAO Playbook.
            If you came here from a playbook or a playbook object page, the name of the playbook or playbook object will be pre-filled. You can change it if you wish.
            Once you press submit, the tool will fetch the form from the wiki and create the relevant fields for you.
            """,
        }
    )
    playbook.page.new.details__OBJ = _returnDict(
        {
            "title": "Creation page",
            "content": """
        At the top you see the creation form for your new playbook or playbook object. Below you see the details of its parent objects. 
        You can edit these details here and they will be updated on the parent objects.
        If you have multiple values for a field, separate them with a comma (Fields like 'name' and 'description' are exempted from this).
        The parent playbook, should one have been selected, will be updated automatically and is not editable here. 
        """,
        }
    )
    playbook.page.edit = AttrDict()
    playbook.page.edit__OBJ = _returnDict(
        {
            "title": "Edit Page",
            "content": """
        On this page you can edit a playbook or playbook object. If you have multiple values for a field, separate them with a comma (Fields like 'name' and 'description' are exempted from this).
        Once you are done, press submit to save your changes.
        If you wish to rename the playbook or playbook object, you can do so on the wiki, changes will be propagated the next time you visit the home or playbook page respectively.
        """,
        }
    )

    playbook_object = AttrDict()
    playbook_object.page = AttrDict()
    playbook_object.page__OBJ = _returnDict(
        {
            "title": "Playbook Object",
            "content": "This is a playbook object page. Below you see the details of this playbook object. To edit this playbook object use the 'Edit' button to the left.",
        }
    )
    playbook_object.page.new = AttrDict()
    playbook_object.page.new.initial__OBJ = playbook.page.new.initial__OBJ
    playbook_object.page.edit = AttrDict()
    playbook_object.page.edit__OBJ = playbook.page.edit__OBJ

    sharing = AttrDict()
    sharing.json = AttrDict()
    
    sharing.json.validator = AttrDict()
    sharing.json.validator__OBJ = _returnDict(
        {
            "title": "JSON CACAO v2 Validator",
            "content": """
        Either directly paste the JSON content of a CACAO v2 playbook in the text area below or drag and drop the playbook
        file there. The tool will evaluate the JSON content and provide feedback on the validity of the playbook.
        Keep in mind that the validator works was designed for CACAO v2 playbooks, while the rest of our tool uses CACAO
        1.1. So, even if the validator says the playbook is valid, it might not work in the rest of the tool and vice versa.
        """,
        }
    )
    sharing.json.import_ = AttrDict()
    sharing.json.import__OBJ = _returnDict(
        {
            "title": "JSON Import",
            "content": """
        On this page you can import a JSON file containing a playbook. The file must be in a valid format.
        Some basic validation is done on the file, but changes are made to the wiki directly, so if the file is invalid, the wiki may be corrupted.
        Be careful, this will overwrite any existing playbook with the same name.
        """,
        }
    )
    sharing.json.export = AttrDict()
    sharing.json.export__OBJ = _returnDict(
        {
            "title": "JSON Export",
            "content": """
        On this page you can export a playbook to a json file. You see a list of all playbooks on the wiki below. Just select the playbook you wish to export and press the button.
        """,
        }
    )
    sharing.stix = AttrDict()
    sharing.stix.import_ = AttrDict()
    sharing.stix.import__OBJ = _returnDict(
        {
            "title": "STIX Import",
            "content": """
        THIS IS A DEMO PAGE. IT DOES NOT WORK YET.
        On this page you can import a playbook from a connected stix repository. 
        The search supports freetext search, but you can also specify the property you wish to search for by using the format 'property:value'.
        """,
        }
    )
    sharing.stix.export = AttrDict()
    sharing.stix.export__OBJ = _returnDict(
        {
            "title": "STIX Export",
            "content": """
        THIS IS A DEMO PAGE. IT DOES NOT WORK YET.
        On this page you can export a playbook to a stix repository. You see a list of all playbooks on the wiki below. Just select the playbook you wish to export and press the button.
        """,
        }
    )

    sharing.misp = AttrDict()
    sharing.misp.import_ = AttrDict()
    sharing.misp.import__OBJ = _returnDict(
        {
            "title": "MISP Import",
            "content": """
        On this page you can import a playbook from a connected MISP instance. 
        The best way to search for playbooks is by labels.
        Search terms are separated by a comma, and the search is case insensitive.
        A limitation of MISP API search is that only complete words can be searched for, so if you search for 'ransom', you will not find 'ransomware' or 'ransom note'.
        """,
        }
    )
    sharing.misp.import_.details = AttrDict()
    sharing.misp.import_.details__OBJ = _returnDict(
        {
            "title": "MISP Import Preview",
            "content": """
            Below you see a preview of the playbook that will be imported.
            If you are satisfied, at the bottom of the page you can choose a name for the playbook and press submit to import it.
            Make sure the name is unique, and that no playbook objects with the same name exist.
            """
        }
    )
    sharing.misp.export = AttrDict()
    sharing.misp.export__OBJ = _returnDict(
        {
            "title": "MISP Export",
            "content": """
        On this page you can export a playbook to a MISP instance. You see a list of all playbooks on the wiki below. Just select the playbook you wish to export and press the button.
        
        Be aware only CACAO playbooks can be exported to MISP.
        """,
        }
    )

    bpmn = AttrDict()
    bpmn.page = AttrDict()
    bpmn.page__OBJ = _returnDict(
        {
            "title": "BPMN",
            "content": """
        This page shows a BPMN diagram of the selected playbook. The diagram is generated from the workflow steps of the playbook and interactive, try clicking on the elements.
        You can drag the viewport around and zoom in by pressing ctrl and scrolling.
        If the page displays an error, that doesn't seem to make sense, try opening the playbook's content page on the left under heading 'CACAO Playbooks',
        that should make sure all the necessary data is loaded.
        """,
        }
    )

    archive = AttrDict()
    archive.playbook = AttrDict()
    archive.playbook.page = AttrDict()
    archive.playbook.page__OBJ = _returnDict(
        {
            "title": "Playbook",
            "content": "This page shows an archived version of the playbook. To the left you see a list of all objects associated with this playbook and below you see the details of this playbook. Archived playbooks cannot be edited.",
        }
    )
    archive.playbook_object = AttrDict()
    archive.playbook_object.page = AttrDict()
    archive.playbook_object.page__OBJ = _returnDict(
        {
            "title": "Playbook Object",
            "content": "This is an archived playbook object page. Below you see the details of this playbook object. Archived playbook objects cannot be edited.",
        }
    )

    thehive = AttrDict()
    thehive.dashboard = AttrDict()
    thehive.dashboard__OBJ = _returnDict(
        {
            "title": "TheHive Dashboard",
            "content": " ".join((
                "This page allows the execution of playbooks on TheHive cases. Below you see a list of all cases,",
                "marked open, on TheHive, a list of all available playbooks in the tool and a list of previously executed playbooks.",
                "At the top you can pick a combination of case and playbook to execute, which will redirect you to the execution page.",
            )),
        }
    )
    thehive.run = AttrDict()
    thehive.run__OBJ = _returnDict(
        {
            "title": "TheHive Run",
            "content": " ".join((
                "This page shows the details of a playbook execution as well as its output.",
                "While the execution is still running, you can refresh the page to see the latest output.",
                "At the moment, there is no way to stop an execution, short of restarting the tool.",
                "Completed executions can be deleted using the 'Delete' button at the top of the page. (Or in bulk in the admin page)",
            )),
        }
    )
