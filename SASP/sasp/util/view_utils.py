from ..sasp_exceptions import SASPObjectValidationException

def serialize_table(table:dict):
    validate_table(table)

    table['row_classes'] = table.get('row_classes', [])
    if isinstance(table['row_classes'], str):
        table['row_classes'] = [table['row_classes']]
    table['cell_classes'] = table.get('cell_classes', [])
    if isinstance(table['cell_classes'], str):
        table['cell_classes'] = [table['cell_classes']]
    
    table['class'] = " ".join(table["class"]) if 'class' in table else ''
    table['id'] = table["id"] if 'id' in table else ''

    if 'thead' in table:
        if 'class' not in table['thead']:
            table['thead']['class'] = ''
        else:
            table['thead']['class'] = " ".join(table["thead"]["class"])
        if 'id' not in table['thead']:
            table['thead']['id'] = ''
        else:
            table['thead']['id'] = table["thead"]["id"]
    
    if 'tfoot' in table:
        if 'class' not in table['tfoot']:
            table['tfoot']['class'] = ''
        else:
            table['tfoot']['class'] = " ".join(table["tfoot"]["class"])
        if 'id' not in table['tfoot']:
            table['tfoot']['id'] = ''
        else:
            table['tfoot']['id'] = table["tfoot"]["id"]

    for row in table['rows']:
        if 'class' in row:
            if isinstance(row['class'], str):
                row['class'] = [row['class']]
            row['class'] = " ".join(row["class"])
        elif table['row_classes']:
            row['class'] = " ".join(table["row_classes"])
        else:
            row['class'] = ''
        row['id'] = row["id"] if 'id' in row else ''
        
        for cell in row['cells']:
            cell['tag'] = cell.get('tag', 'td')
            if 'class' in cell:
                cell['class'] = " ".join(cell["class"])
            elif table['cell_classes']:
                cell['class'] = " ".join(table["cell_classes"])
            else:
                cell['class'] = ''
            cell['id'] = cell["id"] if 'id' in cell else ''
            cell['content'] = cell.get('content', '')
    
    return table


def validate_table(table:dict):
    if not isinstance(table, dict):
        raise SASPObjectValidationException("Table must be a dictionary.")
    if 'caption' in table:
        if not isinstance(table['caption'], str):
            raise SASPObjectValidationException("Table caption must be a string.")
    if 'thead' in table:
        if not 'columns' in table['thead']:
            raise SASPObjectValidationException("Table head must have a columns key.")
        if not isinstance(table['thead']['columns'], list):
            raise SASPObjectValidationException("Table head columns must be a list.")
        if len(table['thead']['columns']) == 0:
            raise SASPObjectValidationException("Table head must have at least one column.")
    if 'tfoot' in table:
        if not 'columns' in table['tfoot']:
            raise SASPObjectValidationException("Table foot must have a columns key.")
        if not isinstance(table['tfoot']['columns'], list):
            raise SASPObjectValidationException("Table foot columns must be a list.")
        if len(table['tfoot']['columns']) == 0:
            raise SASPObjectValidationException("Table foot must have at least one column.")
    if not 'rows' in table:
        raise SASPObjectValidationException("Table must have a rows key.")
    if not isinstance(table['rows'], list):
        raise SASPObjectValidationException("Table rows must be a list.")
    for row in table['rows']:
        if not 'cells' in row:
            raise SASPObjectValidationException("Table row must have a cells key.")
        if not isinstance(row['cells'], list):
            raise SASPObjectValidationException("Table row cells must be a list.")
        if len(row['cells']) == 0:
            raise SASPObjectValidationException("Table row must have at least one cell.")