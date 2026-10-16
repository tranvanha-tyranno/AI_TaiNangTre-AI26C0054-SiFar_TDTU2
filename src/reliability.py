"""Small opt-in corrections; no dataset IDs, coordinates or reference answers."""
from copy import deepcopy
import re


GUIDANCE = '''Execution reminders:
lag is a STEP, never an expression: {"id":"previous","op":"lag","input":"rows","source":"M","column":"prior"}.
Filter valid numeric observations before lag, retain their chronological order, then filter null prior values before subtraction.
Every operator argument is an ARRAY, including unary is_number/number. For an N-digit identifier compare {"length":[{"trim":[{"col":"CODE"}]}]} with the digit count explicitly requested; bind CODE to the observed code column. Do not invent arithmetic wrappers.
For conditional counts, filter on the condition then aggregate count WITHOUT expr. count counts rows, not True values.
Derived columns belong only to that step and its descendants; sibling derive steps do not share columns.
If the requested identity is a section heading and the detail label is the filter category, output _section, not the repeated detail label. Inspect section_labels and the header before choosing.
Preview row section_row points to the observed preceding section_labels anchor; it is context, not a guaranteed semantic group. Output _section only after checking its actual label.
For percent change use calculate expr={"mul":[{"div":[{"sub":[{"ref":"new"},{"ref":"old"}]},{"ref":"old"}]},{"value":100}]}.
Percent decrease uses old-new instead; use actual scalar step IDs. Never put an object directly under div or mul.
Return steps as a JSON array, not a JSON-encoded string. Do not add a new validation phase or extra inspection without a specific missing source.
'''


def normalize(plan):
    """Lift an explicitly declared lag with identical source/destination only."""
    cloned = deepcopy(plan)
    changes = []
    for step in cloned.get('steps', []):
        if not isinstance(step, dict) or step.get('op') != 'derive':
            continue
        expr = step.get('expr')
        if not isinstance(expr, dict) or set(expr) != {'lag'}:
            continue
        lag = expr['lag']
        if (not isinstance(lag, dict) or not {'source','column'} <= set(lag)
                or set(lag) - {'source','column','offset'} or lag['column'] != step.get('column')
                or not isinstance(lag['source'], str)):
            continue
        step.pop('expr')
        step.update(op='lag', **lag)
        changes.append({'step':step.get('id'), 'kind':'explicit_lag_expression_to_step'})
    return cloned, changes


def preview(region, question, limit):
    """Expose existing section provenance alongside sampled detail rows."""
    result = region.preview(question, limit)
    anchors = iter(region.section_labels())
    upcoming = next(anchors, None)
    current = None
    for row in sorted(result['rows'], key=lambda row: row['row']):
        while upcoming and upcoming['row'] <= row['row']:
            current = upcoming
            upcoming = next(anchors, None)
        if current:
            row['section_row'] = current['row']
    return result


def format_numeric_components(result, contract):
    """Only explicit numeric tuple components; never normalize identity fields."""
    if contract.get('kind') != 'tuple' or not contract.get('integer'):
        return []
    from .tools.executor import number, PlanError
    changes=[]
    for index in contract.get('numeric_positions', []):
        if index >= len(result['values']): continue
        value=result['values'][index]
        if not isinstance(value,str) or not re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+',value): continue
        try: parsed=number(value)
        except PlanError: continue
        result['values'][index]=str(int(parsed))
        changes.append({'component':index,'kind':'explicit_integer_grouping','before':value,'after':str(int(parsed))})
    return changes
