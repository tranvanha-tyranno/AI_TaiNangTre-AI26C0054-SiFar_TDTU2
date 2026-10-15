"""Bounded, read-only workbook observations requested by the planner."""
from dataclasses import replace
from openpyxl.utils.cell import range_boundaries
from .tools.executor import PlanError
from .workbook_index import text


def observe(requests, regions, question, preview_rows=45):
    if not isinstance(requests, list) or not 1 <= len(requests) <= 3:
        raise PlanError('Inspection needs 1..3 requests per turn')
    index = {r.id: r for r in regions}
    observations, acquired = [], []
    for request in requests:
        if not isinstance(request, dict):
            raise PlanError('Inspection request must be an object')
        op = request.get('op')
        allowed = {'list_sheets': set(), 'inspect_table': {'table'},
                   'read_range': {'table', 'range'}, 'search_cells': {'text', 'sheet'}}
        if op not in allowed or set(request) - allowed[op] - {'op'}:
            raise PlanError('Unknown inspection operation or fields')
        if op == 'list_sheets':
            observations.append({'op': op, 'sheets': list(dict.fromkeys(r.sheet for r in regions))})
        elif op == 'search_cells':
            needle = request.get('text')
            if not isinstance(needle, str) or not 1 <= len(needle.strip()) <= 120:
                raise PlanError('search_cells.text must contain 1..120 characters')
            sheet = request.get('sheet')
            if sheet is not None and sheet not in {r.sheet for r in regions}:
                raise PlanError('Unknown search sheet')
            hits, seen = [], set()
            for region in regions:
                if sheet is not None and region.sheet != sheet:
                    continue
                for (row, col), value in region.cells.items():
                    key = (region.sheet, row, col)
                    if key not in seen and needle.casefold() in text(value).casefold():
                        seen.add(key)
                        if len(hits) < 20:
                            hits.append({'table': region.id, 'sheet': region.sheet,
                                         'row': row, 'column_index': col, 'value': text(value)[:300]})
            observations.append({'op': op, 'matches': hits, 'match_count': len(seen), 'truncated': len(seen) > 20})
        else:
            region = index.get(request.get('table'))
            if region is None:
                raise PlanError('Unknown table ID for inspection; use table_catalog')
            view = region
            if op == 'read_range':
                try:
                    c1, r1, c2, r2 = range_boundaries(request.get('range', ''))
                    valid = (region.start_row <= r1 <= r2 <= region.end_row and
                             region.start_col <= c1 <= c2 <= region.end_col)
                except (TypeError, ValueError):
                    valid = False
                if not valid:
                    raise PlanError('read_range must be an A1 range inside the selected table')
                if (r2-r1+1)*(c2-c1+1) > 600:
                    raise PlanError('read_range is limited to 600 cells; request a smaller range')
                view = replace(region, start_row=r1, end_row=r2, start_col=c1, end_col=c2)
            observations.append({'op': op, 'preview': view.preview(question, min(preview_rows, 60))})
            acquired.append(region)  # Executor retains the complete original region.
    return observations, acquired
