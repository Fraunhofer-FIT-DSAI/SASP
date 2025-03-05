# Intro
This file contains documentation and specifications for using the automation component of SASP, specifically how to define commands to execute CORTEX analyzers and responders and how to express conditions that can make use of the results of those commands.
## Commands
<!-- Subject to change after tests -->
We use an extension of the openc2 language to define commands, since it is already supported in the cacao standard and provides a format for commands specifically.

The specification for the openc2 language can be found [here](https://docs.oasis-open.org/openc2/oc2ls/v1.0/cs02/oc2ls-v1.0-cs02.html#331-openc2-command).

Our extension of the openc2 language is as follows:  
To start an analyzer/responder, we use the action `start` with the target type `uri` and the target `uri` being the name of the analyzer/responder.  
In args, we specify the field `observable` on which an analyzer should be run in the format `hive-case-observable:<observable-label>`, where `<observable-label>` is a tag of form `auto_label_<observable-label>` that is attached to the observable.

For responders , we add the `cortex_args` field to the args object, which is an object that will be passed to the responder as its data field.

For example, to start the analyzer `whois`, on the `domain-name` observable, we would use the following command:
```json
{
    "action": "start",
    "target": {
        "uri": "whois"
    },
    "args": {
        "observable": "hive-case-observable:domain-name"
    }
}
```
And to start the Responder `NOKI_Reporter_1_0` with the argument `arg1` being the data of the observable labeled `exHash`, we would use this command:
```json
{
    "action": "start",
    "target": {
        "uri": "NOKI_Reporter_1_0"
    },
    "args": {
        "cortex_args": {
            "arg1" : "hive-case-observable:exHash.data"
        }
    }
}
```
## Conditions
For condition language, CACAO specifies the use of the [STIX pattern language](https://docs.oasis-open.org/cti/stix/v2.1/cs01/stix-v2.1-cs01.html#_e8slinrhxcc9).

A limitation of this grammar is however that it relies on the use of STIX objects to compare, which are not present in any CACAO fields.  
Our solution is to treat the results of analyzers and case fields as STIX objects. while stripping away STIX operators that rely on information not guaranteed to be present in the results of analyzers and case fields.

Particularly, we remove the following operators:
- a REPEATS x TIMES
- a WITHIN x SECONDS
- a START x STOP y
- [a] FOLLOWEDBY [b]
- FOLLOWEDBY (Observation Operator)

Aside from these operators all other aspects of the STIX pattern language are supported.

### Case Fields
Case fields can be accessed in the condition language by using the `hive-case-field` prefix, followed by the name of the field in the hive case and a path expression to navigate to the desired value.

For example, with a hive case containing the following fields:
```json
    "title": "Test Case",
    "description": "This is a test case",
    "status": "Open",
    "severity": "Low",
    "tags": ["test","case"],
    "owner": "test",
    "flag": False,
    "int_field": 1,
    "deep_field": {
        "subfield": "test",
        "sublist": [1,2,3],
        "subdict": {
            "subsubfield": "test",
            "subsublist": [4,5,6]
        },
        "chained_list": [
            [1,2,3],
            [4,5,6],
            [7,8,9]
        ]
    }
```
We can access the second value in the `chained_list` field by using the following path expression:
```json
"hive-case-field:deep_field.chained_list[1][1]"
```

Additionally, STIX uses the `*` character as an index wildcard, which can be used to match any index in a list, so for example the expression:
```json
"[hive-case-field:tags[*] = 'case']"
```
would evaluate to true.

### Case Observables
Case observables can be accessed in the condition language by using the `hive-case-observable` prefix. To identify the observable, we use a custom tag of the shape `auto_label_{unique-string}`, with `{unique-string}` replaced by the identifier, because observables do not have a name field and the unique identifier, the `id` field, is assigned at runtime and not known beforehand. If several observables have the same tag, the newest one will be used, so it is recommended to use unique tags for each observable per case.

Example:
```json
    [
        {
            '_id': '~16392',
            '_type': 'case_artifact',
            'attachment': {},
            'createdAt': 1689084450220,
            'dataType': 'file',
            'id': '~16392',
            tags: ['file', 'textfile', 'normal_tag', 'auto_label_1234']
        },
        {
            '_id': '~40964184',
            '_type': 'case_artifact',
            'createdAt': 1702563614995,
            'data': '192.168.1.1',
            'dataType': 'ip',
            'id': '~40964184',
            tags: ['file', 'textfile', 'normal_tag', 'auto_label_5678']
        },
        {
            '_id': '~40972376',
            '_type': 'case_artifact',
            'createdAt': 1702563618430,
            'data': '203.0.113.0',
            'dataType': 'ip',
            'id': '~40972376',
            tags: ['file', 'textfile', 'normal_tag', 'auto_label_5678']
        }
    ]
```
In this example, the expression `hive-case-observable:5678` would return the ip-address observable with the value `203.0.113.0`.

### Analyzer Results
Analyzer results can be accessed in the condition language by using the `hive-analyzer-result` prefix, followed by the name or id of the analyzer, a period, the `auto_label_{name}` of the observable (see Section [Case Observables](#Case-Observables)) the analyzer was run on, and a path expression to navigate to the desired value. e.g.: `hive-analyzer-result:whois.domain-name`.

Should either the analyzer or the observable name contain reserved characters, they can be escaped by using the `\` character. e.g.: `hive-analyzer-result:whois.domain\:name`.

You can also use the label to indicate the target observable `hive-analyzer-result:analyzer.observableTag` would match on observables with the tag `auto_label_observableTag`.

Should either the analyzer or the observable name contain a space, it must be substituted with the `_` character. e.g.: `hive-analyzer-result:whois.domain_name`, actual underscores in the name must also be escaped with the `\` character.

#### Alternative Syntax
Not yet implemented.

For ease of access, we also provide an alternative syntax for accessing analyzer results, that can be used if the analyzer was run by a command in the same playbook.  
In that case, the analyzer result can be accessed by using the `hive-analyzer-result-by-step` prefix, followed by the name or id of the step that ran the analyzer and the index of the command that ran the analyzer, in established path syntax. 
e.g. for step 
```json
{
    'step--1234': {
        "name": "run-analysis",
        "commands": [
            {
                "action": "start",
                "target": {
                    "uri": "whois"
                },
                "args": {
                    "observable": "hive-case-field:domain-name",
                    "cortex_args": [
                        "verbose"
                    ]
                }
            },
            '...'
        ]
    }
}
```
either the expression `hive-analyzer-result-by-step:step--1234[0]` or `hive-analyzer-result-by-step:run-analysis[0]` would return the result of the whois analyzer, in the same way as the expression `hive-analyzer-result:whois.domain-name`.

Warning: This syntax will always retrieve from the first version of an executed command. If the command was executed in a loop, there is no way to specify which version of the command should be used. (This might be changed in the future, but for the moment it is not a priority)

Should the step id or name contain a space, it must be substituted with the `_` character. e.g.: `hive-analyzer-result-by-step:run_analysis[0]`, actual underscores in the name must also be escaped with the `\` character.

### Responder Results
To be implemented using expression `cortex-responder-result`. (Because responders are not a simple combination of name and observable, this syntax might not happen and only the alternative syntax will be used.)

#### Alternative Syntax
For ease of access, we also provide an alternative syntax for accessing responder results, that can be used if the responder was run by a command in the same playbook.  
In that case, the responder result can be accessed by using the `cortex-responder-result-by-step` prefix, followed by the name or id of the step that ran the responder and the index of the command that ran the responder, in established path syntax. 
e.g. for step 
```json
{
    'step--1234': {
        "name": "quarantine",
        "commands": [
            {
                "action": "start",
                "target": {
                    "uri": "quarantine"
                },
                "args": {
                    "observable": "hive-case-field:domain-name",
                    "cortex_args": [
                        "verbose"
                    ]
                }
            },
            '...'
        ]
    }
}
```
either the expression `cortex-responder-result-by-step:step--1234[0]` or `cortex-responder-result-by-step:quarantine[0]` would return the result of the `quarantine` responder.

## Common Errors (aka errors I made while testing)
- Always remeber to leave space between variable operator and constant, e.g. `hive-case-field:field = 'value'` instead of `hive-case-field:field='value'`