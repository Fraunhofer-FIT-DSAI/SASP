import base64
import json
import re
import requests
from datetime import datetime

from ..external_apis.hive_cortex_api import HiveAPI
from ..sasp_exceptions import (VariableReadingException)

## Utility functions
# Unescape
def unencode(s):
    escaped = False
    result = ""
    for c in s:
        if escaped:
            result += c
            escaped = False
        elif c == "\\":
            escaped = True
        elif c == "_":
            result += " "
        else:
            result += c
    return result

## STIX Language Functions
def parse_object_with_expression(obj, expression):
        # Format: hive-case-field:field[index].subfield
        # Index is optional. If no brackets are present, the entire field is used.
        # Index can be a number, indicating the index of a list, or '*' indicating all elements of a list
        # Subfield is optional. If no dot is present, the entire field or list is used.
        # Subfield is assumed to be a string, for dictionary access
        # This can be chained, e.g. hive-case-field:field[index].subfield[index][index2].subfield
        # (Can it officialy? The documentation is unclear, but since we don't control the case fields, we need to be able to do this)

        if expression == "" or expression == None:
            return [obj]

        nested_fields = expression.split(".")
        active_values = [obj]
        for i,case_field in enumerate(nested_fields):
            new_active_values = []
            # Attempt to apply the path element to each active value
            # Get the field name and the index
            field_name = case_field.strip()
            index_list = []
            while field_name.endswith("]") and field_name.rfind("[") != -1:
                index = field_name.rfind("[")
                field_name,index = field_name[:index],field_name[index+1:-1]
                index_list.append(index)
            if index_list:
                index_list.reverse()

            for active_value in active_values:
                # Attempt to apply the field name to the active value
                try:
                    new_active_values.append(active_value[field_name])
                except TypeError:
                    pass
                except KeyError:
                    pass
            for index in index_list:
                new_new_active_values = []
                # Attempt to apply the index to each new active value
                for value in new_active_values:
                    try:
                        if index == "*":
                            new_new_active_values += value
                        else:
                            new_new_active_values.append(value[int(index)])
                    except TypeError:
                        pass
                    except IndexError:
                        pass
                new_active_values = new_new_active_values

            active_values = new_active_values
        return active_values

def get_variable_value(variable:str, context:dict, hive_case_id=None, hive_api:'HiveAPI'=None):
    """Returns the value of the given variable.

    Args:
        variable (str): The variable to get the value of.
        workflow_instance (WorkflowInstance): The workflow instance to get the value from.
    """

    # Case 1: CACAO Variable
    if variable.split(":")[0].startswith("$$") and variable.split(":")[0].endswith("$$"):
        var_name, _, field = variable.partition(":")
        
        if var_name in context:
            # string,uuid,integer,long,mac-addr,ipv4-addr,ipv6-addr,uri,sha256-hash,hexstring,dictionary
            # No float?
            variable = context[var_name]
            if variable["var_type"] == "dictionary" and field: # Only complex type supported
                return parse_object_with_expression(variable["var_value"], field)
            else:
                return [variable["var_value"]]
        else:
            return []
        
    if ":" in variable and variable.split(":")[0] == "hive-case-field":
        if hive_case_id is None:
            raise Exception("hive_case_id not provided")
        if hive_api is None:
            raise Exception("hive_api not provided")
        # Case 2: Hive Case Field
        field = variable.split(":")[1]
        object = hive_api.get_case(case_id=hive_case_id)
        return parse_object_with_expression(object, field)
    elif ":" in variable and variable.split(":")[0] == "hive-case-observable":
        if hive_case_id is None:
            raise Exception("hive_case_id not provided")
        if hive_api is None:
            raise Exception("hive_api not provided")
        # hive-case-observable:5678.tags[0]
        field = variable.split(":")[1] # 5678.tags[0]
        field_name = field.split(".",1)[0] # 5678
        if len(field.split(".",1)) > 1:
            field = field.split(".",1)[1] # tags[0]
        else:
            field = ""
        observables = hive_api.get_observable_by_case_and_artifact(case_id=hive_case_id, artifact_label=f"auto_label_{field_name}")
        if len(observables) == 0:
            raise VariableReadingException(f"Observable not found: {field_name}")
        elif len(observables) == 1:
            object = observables[0]
        else:
            object = sorted(observables, key=lambda x: x["_createdAt"])[-1]
        return parse_object_with_expression(object, field)
    elif ":" in variable and variable.split(":")[0] == "hive-analyzer-result":
        # TAG:DOCUMENATION: We enforce shape hive-analyzer-result:analyzer_name.analyzer_target.<path>
        # The combination of analyzer_name and analyzer_target should be unique (otherwise you'd have ran the same analyzer on the same target twice)
        # <path> navigates the returned object from DUMMY_get_analyzer_result
        # '.', '[', ']', ':', '\' are allowed in analyzer_name and analyzer_target when escaped with '\'
        # spaces are not allowed in analyzer_name and analyzer_target and can be substituted with '_'
        # Actual '_' characters have to be escaped with '\'
        if hive_case_id is None:
            raise Exception("hive_case_id not provided")
        if hive_api is None:
            raise Exception("hive_api not provided")
        field = variable.split(":",1)[1]
        analyzer_name = ""
        analyzer_target = ""
        # Find first unescaped '.'
        index = 0
        for i,c in enumerate(field):
            if c == "." and field[i-1] != "\\":
                analyzer_name = field[:i]
                index = i
                break
        # Find second unescaped '.'
        for i,c in enumerate(field[index+1:]):
            if c == "." and field[i+index] != "\\":
                analyzer_target = field[index+1:index+1+i]
                index += i+1
                break
        field = field[index+1:]
        analyzer_name = unencode(analyzer_name)
        analyzer_target = unencode(analyzer_target)
        try:
            observables = hive_api.get_observable_by_case_and_artifact(case_id=hive_case_id, artifact_label=f"auto_label_{analyzer_target}")
            analyzer_target = sorted(observables, key=lambda x: x["_createdAt"])[-1]["_id"]
        except Exception:
            pass

        object = hive_api.get_case_analyzer_result(case_id=hive_case_id, analyzer_idOrName=analyzer_name, observable_idOrName=analyzer_target)
        return parse_object_with_expression(object, field)
    elif ":" in variable and variable.split(":")[0] == "cortex-responder-result":
        raise Exception("cortex-responder-result not supported")
    else:
        raise Exception(f"Invalid variable: {variable}")


def parse_observation_expression(expression, context, hive_case_id=None, hive_api:"HiveAPI"=None):
    """Parses the observation expression and returns a boolean value.
    expression contains one or more comparison expressions, separated by AND and OR.
    REPEATS x TIMES, WITHIN x SECONDS, START x STOP are not supported and probably never will be. (The stix objects to which they refer are not present in this use case)
    """
    # At this point there can be operators inside the brackets, expressions that have already been parsed, or keywords inside strings
    # so we need a state machine to parse the expression
    expression_string = expression.strip()
    comparison_expressions = []
    operators = []
    while expression_string != "":
        if expression_string.startswith("AND"):
            operators.append("AND")
            expression_string = expression_string[3:]
        elif expression_string.startswith("OR"):
            operators.append("OR")
            expression_string = expression_string[2:]
        elif expression_string.startswith("("):
            operators.append("(")
            expression_string = expression_string[1:]
        elif expression_string.startswith(")"):
            operators.append(")")
            expression_string = expression_string[1:]
        elif expression_string.startswith("FOLLOWEDBY"):
            raise Exception("FOLLOWEDBY not supported")
        elif expression_string.startswith("true"):
            comparison_expressions.append(True)
            expression_string = expression_string[4:]
        elif expression_string.startswith("false"):
            comparison_expressions.append(False)
            expression_string = expression_string[5:]
        elif expression_string.startswith("["):
            # Find the matching closing bracket (~~simple search, nested brackets not supported~~ it isn't but list indexes use brackets too, so find the matching closing bracket)
            start = 0
            end = 0
            in_string = False
            depth = -1 # The opening bracket is the first character, so we start at -1
            for i,c in enumerate(expression_string):
                if c == "[" and not in_string:
                    depth += 1
                elif c == "]" and not in_string:
                    if depth == 0:
                        end = i
                        break
                    else:
                        depth -= 1
                elif c == "'":
                    in_string = not in_string
            if end == 0:
                raise Exception(f"Invalid observation expression: {expression}")
            comparison_expressions.append(expression_string[start:end+1])
            expression_string = expression_string[end+1:]
        else:
            raise Exception(f"Invalid observation expression: {expression}")
        expression_string = expression_string.strip()


    # Step 2: Parse the comparison expressions
    comparison_results = []
    for comparison_expression in comparison_expressions:
        if isinstance(comparison_expression, bool):
            comparison_results.append(comparison_expression)
        else:
            comparison_results.append(parse_comparison_expression(comparison_expression[1:-1], context, hive_case_id=hive_case_id, hive_api=hive_api))
    
    # Step 3: Combine the results with logical operators, prioritizing AND over OR.
    while True:
        if "(" in operators:
            start = len(operators) - 1 - operators[::-1].index("(")
            end = start + operators[start:].index(")")
        else: # No brackets left, resolve remaining and/or operators
            while "AND" in operators:
                op_index = operators.index("AND")
                res_index = op_index - 1
                comparison_results[res_index] = comparison_results[res_index] and comparison_results[res_index+1]
                comparison_results.pop(res_index+1)
                operators.pop(op_index)
            while "OR" in operators:
                op_index = operators.index("OR")
                res_index = op_index - 1
                comparison_results[res_index] = comparison_results[res_index] or comparison_results[res_index+1]
                comparison_results.pop(res_index+1)
                operators.pop(op_index)
            break
        # Count AND and OR operators before the bracket
        result_index = operators[:start].count("AND") + operators[:start].count("OR")
        if "AND" in operators[start+1:end]:
            op_index = operators[start+1:end].index("AND") + start + 1 # Position of the AND operator in the operators list
            res_index = result_index + op_index - start - 1 # Position of the result in the comparison_results list
            comparison_results[res_index] = comparison_results[res_index] and comparison_results[res_index+1]
            comparison_results.pop(res_index+1)
            operators.pop(op_index)
            continue
        if "OR" in operators[start+1:end]:
            op_index = operators[start+1:end].index("OR") + start + 1
            res_index = result_index + op_index - start - 1 # Position of the result in the comparison_results list
            comparison_results[res_index] = comparison_results[res_index] or comparison_results[res_index+1]
            comparison_results.pop(res_index+1)
            operators.pop(op_index)
            continue
        operators.pop(start) # Remove the opening bracket
        operators.pop(start) # Remove the closing bracket


        
    return comparison_results[0]

def parse_comparison_expression(expression, context, hive_case_id=None, hive_api:'HiveAPI'=None):
    """Parses the comparison expression and returns a boolean value.
    Gets called only on the contents of square brackets in an observation expression.
    """
    expression_string = expression.strip()
    logic_operators = []
    comparison_expressions = []

    # Step 1: Parse the expression into comparison expressions and logical operators
    while expression_string != "":
        if expression_string.startswith("AND"):
            logic_operators.append("AND")
            expression_string = expression_string[3:]
        elif expression_string.startswith("OR"):
            logic_operators.append("OR")
            expression_string = expression_string[2:]
        elif expression_string.startswith("("):
            logic_operators.append("(")
            expression_string = expression_string[1:]
        elif expression_string.startswith(")"):
            logic_operators.append(")")
            expression_string = expression_string[1:]
        else: # Comparison expression
            expression = {
                "var": None,
                "constant": None,
                "operator": None,
                "negated": False
            }
            success = False
            # (NOT) EXISTS a
            if expression_string.startswith("NOT"):
                expression["negated"] = True
                expression_string = expression_string[3:].lstrip()
            if expression_string.startswith("EXISTS"):
                expression["operator"] = "EXISTS"
                expression_string = expression_string[6:].lstrip()
                if re.match(r"^\S*:\S*", expression_string):
                    index_next_space = expression_string.find(" ")
                    if index_next_space == -1:
                        expression["var"] = expression_string
                        expression_string = ""
                    else:
                        expression["var"] = expression_string[:index_next_space]
                        expression_string = expression_string[index_next_space:].lstrip()
                    comparison_expressions.append(expression)
                    success = True
            # a (NOT) comparison_operator b
            else:
                if re.match(r"^\S*", expression_string):
                    expression["var"] = expression_string[:expression_string.find(" ")]
                    expression_string = expression_string[expression_string.find(" "):].lstrip()
                    if expression_string.startswith("NOT"):
                        expression["negated"] = True
                        expression_string = expression_string[3:].lstrip()
                    for op in ["=", "!=", "<", ">", "<=", ">=", "IN", "LIKE", "MATCHES", "ISSUBSET", "ISSUPERSET"]:
                        if expression_string.startswith(op):
                            expression["operator"] = op
                            expression_string = expression_string[len(op):].lstrip()
                            break
                    if expression["operator"] in {"IN", "ISSUBSET", "ISSUPERSET"}:
                        if expression_string.startswith("("): # Find the end of the list
                            expression["constant"] = expression_string[:expression_string.find(")")+1].strip()
                            expression_string = expression_string[expression_string.find(")")+1:].lstrip()
                            comparison_expressions.append(expression)
                            success = True
                    elif expression_string.startswith("'"): # Find the end of the string
                        expression["constant"] = expression_string[:expression_string[1:].find("'")+2].strip()
                        expression_string = expression_string[expression_string[1:].find("'")+2:].lstrip()
                        comparison_expressions.append(expression)
                        success = True
                    elif expression_string.startswith("true"):
                        expression["constant"] = "true"
                        expression_string = expression_string[4:].lstrip()
                        comparison_expressions.append(expression)
                        success = True
                    elif expression_string.startswith("false"):
                        expression["constant"] = "false"
                        expression_string = expression_string[5:].lstrip()
                        comparison_expressions.append(expression)
                        success = True
                    elif re.match(r"^\S*", expression_string): # Find the end of the number(?)
                        if " " in expression_string:
                            expression["constant"] = expression_string[:expression_string.find(" ")].strip()
                        else:
                            expression["constant"] = expression_string.strip()
                        expression_string = expression_string[len(expression["constant"]):].lstrip()
                        comparison_expressions.append(expression)
                        success = True
            if not success:
                raise Exception(f"Invalid comparison expression: {expression}")
        expression_string = expression_string.lstrip()

    # Step 2: Parse the comparison expressions
    comparison_results = []
    for comparison_expression in comparison_expressions:
        variable, constant, operator, negated = comparison_expression["var"], comparison_expression["constant"], comparison_expression["operator"], comparison_expression["negated"]
        # Resolve the variable
        variable = get_variable_value(variable, context, hive_case_id=hive_case_id, hive_api=hive_api)
        # Resolve the constant
        if constant:
            values = []
            if operator in {"IN", "ISSUBSET", "ISSUPERSET"}:
                values = [x.strip() for x in constant[1:-1].split(",")]
            else:
                values = [constant]
            for i,value in enumerate(values):
                # boolean
                if value.lower() == "true":
                    values[i] = True
                    continue
                elif value.lower() == "false":
                    values[i] = False
                    continue
                # binary (base64)
                if value.startswith("b'") and value.endswith("'"):
                    values[i] = base64.b64decode(value[2:-1])
                    continue
                # hex
                if value.startswith("h'") and value.endswith("'"):
                    values[i] = bytes.fromhex(value[2:-1])
                    continue
                # integer
                if value.isdigit():
                    try:
                        values[i] = int(value)
                        continue
                    except ValueError:
                        pass
                # float
                if re.match(r"^\d+\.\d+$", value):
                    try:
                        values[i] = float(value)
                        continue
                    except ValueError:
                        pass
                # string
                if value.startswith("'") and value.endswith("'"):
                    values[i] = value[1:-1]
                    # Escape characters
                    values[i] = values[i].replace("\\\\","\\")
                    values[i] = values[i].replace("\\'","'")
                    continue
                # timestamp
                if value.startswith("t'") and value.endswith("'"):
                    # load timestamp with format RFC3339
                    values[i] = datetime.strptime(value[2:-1], "%Y-%m-%dT%H:%M:%S.%fZ")
                    continue
                raise Exception(f"Invalid constant: {constant}")
            if len(values) == 1:
                constant = values[0]
            else:
                constant = values
        # Execute the comparison
        if operator == "=":
            comparison_results.append(any([v == constant for v in variable]))
        elif operator == "!=":
            comparison_results.append(any([v != constant for v in variable]))
        elif operator == "<":
            comparison_results.append(any([v < constant for v in variable]))
        elif operator == ">":
            comparison_results.append(any([v > constant for v in variable]))
        elif operator == "<=":
            comparison_results.append(any([v <= constant for v in variable]))
        elif operator == ">=":
            comparison_results.append(any([v >= constant for v in variable]))
        elif operator == "IN":
            comparison_results.append(any([v in constant for v in variable]))
        elif operator == "LIKE":
            pattern = re.escape(constant).replace("_",".").replace("%",".*")
            comparison_results.append(any([re.match(pattern, v) for v in variable]))
        elif operator == "MATCHES":
            comparison_results.append(any([re.match(constant, v) for v in variable]))
        elif operator == "ISSUBSET":
            result = False
            for v in variable:
                try:
                    if set(v).issubset(set(constant)):
                        result = True
                        break
                except TypeError:
                    pass
            comparison_results.append(result)
        elif operator == "ISSUPERSET":
            result = False
            for v in variable:
                try:
                    if set(v).issuperset(set(constant)):
                        result = True
                        break
                except TypeError:
                    pass
            comparison_results.append(result)
        elif operator == "EXISTS":
            comparison_results.append(any([v is not None for v in variable]))
        else:
            raise Exception(f"Invalid comparison operator: {operator}")
        if negated:
            comparison_results[-1] = not comparison_results[-1]
        
    # Step 3: Combine the results with logical operators, prioritizing AND over OR.
    while True:
        if "(" in logic_operators:
            start = len(logic_operators) - 1 - logic_operators[::-1].index("(")
            end = start + logic_operators[start:].index(")")
        else: # No brackets left, resolve remaining and/or logic_operators
            while "AND" in logic_operators:
                op_index = logic_operators.index("AND")
                res_index = op_index - 1
                comparison_results[res_index] = comparison_results[res_index] and comparison_results[res_index+1]
                comparison_results.pop(res_index+1)
                logic_operators.pop(op_index)
            while "OR" in logic_operators:
                op_index = logic_operators.index("OR")
                res_index = op_index - 1
                comparison_results[res_index] = comparison_results[res_index] or comparison_results[res_index+1]
                comparison_results.pop(res_index+1)
                logic_operators.pop(op_index)
            break
        # Count AND and OR operators before the bracket
        result_index = logic_operators[:start].count("AND") + logic_operators[:start].count("OR")
        if "AND" in logic_operators[start+1:end]:
            op_index = logic_operators[start+1:end].index("AND") + start + 1 # Position of the AND operator in the operators list
            res_index = result_index + op_index - start - 1 # Position of the result in the comparison_results list
            comparison_results[res_index] = comparison_results[res_index] and comparison_results[res_index+1]
            comparison_results.pop(res_index+1)
            logic_operators.pop(op_index)
            continue
        if "OR" in logic_operators[start+1:end]:
            op_index = logic_operators[start+1:end].index("OR") + start + 1
            res_index = result_index + op_index - start - 1 # Position of the result in the comparison_results list
            comparison_results[res_index] = comparison_results[res_index] or comparison_results[res_index+1]
            comparison_results.pop(res_index+1)
            logic_operators.pop(op_index)
            continue
        logic_operators.pop(start) # Remove the opening bracket
        logic_operators.pop(start) # Remove the closing bracket
        
    return comparison_results[0]

def parse_if_condition(condition, context, hive_case_id=None, hive_api:"HiveAPI"=None):
    """Parses the condition string and returns a boolean value.
    """

    condition_string = condition

    return parse_observation_expression(condition_string, context, hive_case_id=hive_case_id, hive_api=hive_api)

def validate_if_condition(condition):
    """Validates the condition string.
    This is only a regex check, so it can't detect all errors.
    """
    
    # Comparison expression (top level, square brackets around observation expressions are literal)
    # [ObservationExpression] AND|OR [ObservationExpression] AND|OR [ObservationExpression] ...
    # ObservationExpression (square brackets around variable, constant are not literal)
    # (NOT) EXISTS [Variable]
    # [Variable] (NOT) IN ( [Constant], [Constant], ... )
    # [Variable] (NOT) ISSUBSET ( [Constant], [Constant], ... )
    # [Variable] (NOT) ISSUPERSET ( [Constant], [Constant], ... )
    # [Variable] (NOT) =|!=|<|>|<=|>=|LIKE|MATCHES [Constant]

    if not re.match(r"^\[.*\]$", condition): # String must be surrounded by square brackets
        raise Exception(f"Invalid condition: {condition}")
    observation_expressions = []
    depth = 0
    start = 0
    for i,c in enumerate(condition):
        if c == "[":
            if depth == 0:
                start = i
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                observation_expressions.append(condition[start:i+1])
    # Extracted observation expressions
    for expression in observation_expressions:
        condition.replace(expression, "OBSERVATION_EXPRESSION", 1)
    # At this point a proper condition should be "OBSERVATION_EXPRESSION AND|OR OBSERVATION_EXPRESSION AND|OR OBSERVATION_EXPRESSION ..."
    switch = 0 # 0 = OBSERVATION_EXPRESSION, 1 = " ", 2 = AND|OR, 3 = " "
    idx = 0
    while True:
        if switch == 0:
            if not condition[idx:].startswith("OBSERVATION_EXPRESSION"):
                raise Exception(f"Invalid condition: {condition}")
            switch = 1
            idx += len("OBSERVATION_EXPRESSION")
        elif switch == 1:
            if not condition[idx:].startswith(" "):
                raise Exception(f"Invalid condition: {condition}")
            switch = 2
            idx += 1
        elif switch == 2:
            match_ = re.match(r"^AND|OR", condition[idx:])
            if not match_:
                raise Exception(f"Invalid condition: {condition}")
            switch = 3
            idx += len(match_.group(0))
        elif switch == 3:
            if not condition[idx:].startswith(" "):
                raise Exception(f"Invalid condition: {condition}")
            switch = 0
            idx += 1
        if idx == len(condition):
            break
        if idx > len(condition):
            raise Exception(f"Idx out of range: {condition}")
    if switch != 1:
        raise Exception(f"Invalid condition: {condition}")