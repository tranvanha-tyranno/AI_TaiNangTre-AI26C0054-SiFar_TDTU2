"""Static column lineage. Never reconnect branches or invent missing columns."""
from openpyxl.utils import get_column_letter
from .tools.executor import PlanError


def columns_in(value):
    if isinstance(value, dict):
        if set(value) == {'col'}:
            yield value['col']
        for child in value.values():
            yield from columns_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from columns_in(child)


def check_columns(plan, regions):
    tables = {r.id: r for r in regions}
    schemas = {}

    def require(columns, source, step):
        if any(not isinstance(col, str) for col in columns):
            raise PlanError(f'Column lineage {step}: column names must be strings.')
        available = schemas.get(source)
        if available is None:
            return
        missing = set(columns) - available
        if missing:
            producers = {col: [s for s, cols in schemas.items() if cols is not None and col in cols]
                         for col in sorted(missing)}
            raise PlanError(f'Column lineage {step}: missing {sorted(missing)} in input {source}; '
                            f'available={sorted(available)}; earlier providers={producers}. '
                            'Use a valid dependency chain; independent derive branches do not share columns.')

    for step in plan['steps']:
        name, op, source = step['id'], step['op'], step.get('input')
        schema = schemas.get(source)
        if op not in {'calculate', 'record'}:
            require(list(columns_in([step.get('expr'), step.get('where')])), source, name)
        if op == 'read':
            r = tables[step['table']]
            schema = {get_column_letter(c) for c in range(r.start_col, r.end_col + 1)}
            schema |= {'_row', '_sheet', '_section', '_section_row'}
        elif op in {'derive', 'lag'}:
            if not isinstance(step.get('column'), str):
                raise PlanError(f'Column lineage {name}: derived column name must be a string.')
            if op == 'lag':
                require([step.get('source')], source, name)
            schema = schema | {step.get('column')} if schema is not None else None
        elif op in {'select', 'unpivot', 'fill_down'}:
            require(step.get('columns', []) + step.get('keep_columns', []), source, name)
            if op == 'select':
                schema = set(step.get('columns', []))
            elif op == 'unpivot':
                schema = set(step.get('keep_columns', [])) | {'column', 'label', 'value', '_row'}
        elif op in {'sort', 'group'}:
            keys = [k.get('column') for k in step.get('by', [])] if op == 'sort' else step.get('by', [])
            require(keys, source, name)
            if op == 'group':
                schema = set(keys) | {step.get('column', 'value')}
        elif op == 'join':
            require([step.get('left_on')], step.get('left'), name)
            require([step.get('right_on')], step.get('right'), name)
            # Outer joins and metadata vary; let the executor establish their schema.
            schema = None
        elif op == 'concat':
            schema = None
        elif op == 'record':
            schema = set(step.get('fields', {}))
        elif op == 'collect':
            schema = {'value'}
        elif op in {'cell', 'calculate', 'aggregate', 'sum_columns'}:
            schema = None
        schemas[name] = schema
    output = plan['output']
    require(output.get('columns', []), output['step'], 'output')
    return {name: sorted(cols) if cols is not None else None for name, cols in schemas.items()}
