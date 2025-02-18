## Release 1.0.0 - open source
### Features:
- The tool has undergone wide ranging rewrites, for better future development and maintenance
- Import/Export across platforms has been standardized
- pm4py dependency replaced with own implementation
- Mediawiki is now write only and no longer a central component of the program
- Object creation improved with more stringent validation
- Quick links for creating new elements
- Archive functionality now allows the sharing of archived playbooks
- Playbook automation disabled for open source release
### Update Instructions:
- This version requires a fresh install of the tool
- Export all playbooks from the old version
- Delete old database file at ```tools/wiki-tool/db.sqlite3```
- Run the setup script ```tools/wiki-tool/setup.py```
- Import the playbooks back into the tool

## Release 1.1
### Features:
- Playbook Execution Functionality
  - Live BPMN diagram during execution
  - Connection to Hive
- Program can now run without a Mediawiki instance
- New BPMN layout algorithm
- Configuration for external components (Mediawiki, MISP, Hive) can now be changed in settings
### Update Instructions:
- Install new libraries via pip `pip install -r requirements.txt`
- Run `python SASP/manage.py migrate`
- Run `python SASP/manage.py make_default_user`