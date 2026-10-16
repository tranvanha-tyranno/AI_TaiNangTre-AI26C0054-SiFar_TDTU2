"""Lossless cell deduplication inside one LLM request, never across requests.

Every table ID/header/bound/row is retained. References point to an earlier
view in the SAME request, same sheet, row and column, with an identical value.
"""
from copy import deepcopy
import json

NOTE=('\nContext encoding: view_id identifies a preview in this request. A row cells_from maps '
      'an earlier view_id to columns whose values are identical at the SAME row and columns. '
      'A view row_refs groups identical rows: copy only its listed columns from that earlier view for each listed row. '
      'row_order preserves original row order. cells contains remaining values. Table IDs and bounds are unchanged.')


def views(payload):
    for key in ('retrieved_tables','previews'):
        for view in payload.get(key,[]):
            if isinstance(view,dict) and isinstance(view.get('rows'),list): yield view
    for observation in payload.get('inspection_results',[]):
        if isinstance(observation,dict):
            view=observation.get('preview')
            if isinstance(view,dict) and isinstance(view.get('rows'),list): yield view


def prepare(messages):
    """Return packed messages plus metrics; retain original if net size grows."""
    packed=deepcopy(messages);before=0;after=0;removed=0;conflicts=0
    for message_index,message in enumerate(packed):
        if message.get('role')!='user': continue
        try: payload=json.loads(message['content'])
        except (TypeError,ValueError): continue
        if not isinstance(payload,dict): continue
        seen={};coordinate_values={}
        for index,view in enumerate(views(payload)):
            view_id=f'm{message_index}v{index}';view['view_id']=view_id
            sheet=view.get('sheet')
            if not isinstance(sheet,str): continue
            for row in view['rows']:
                if not isinstance(row,dict) or type(row.get('row')) is not int or not isinstance(row.get('cells'),dict): continue
                refs={}
                for column,value in list(row['cells'].items()):
                    before+=1
                    coordinate=(sheet,row['row'],column)
                    serialized=json.dumps(value,ensure_ascii=False,sort_keys=True,default=str)
                    key=(*coordinate,serialized)
                    if key in seen:
                        refs.setdefault(seen[key],[]).append(column)
                        del row['cells'][column];removed+=1
                    else:
                        seen[key]=view_id;after+=1
                        if coordinate in coordinate_values and coordinate_values[coordinate]!=serialized: conflicts+=1
                        coordinate_values[coordinate]=serialized
                if refs: row['cells_from']=refs
            # Group complete duplicate rows, instead of repeating a reference
            # for every single cell. No source value is regenerated or inferred.
            order=[r.get('row') for r in view['rows'] if isinstance(r,dict)]
            if len(order)==len(view['rows']) and len(order)==len(set(order)):
                groups={};retained=[]
                for row in view['rows']:
                    refs=row.get('cells_from',{})
                    if not row.get('cells') and len(refs)==1 and set(row)<={'row','cells','cells_from'}:
                        owner,columns=next(iter(refs.items()));key=(owner,tuple(columns))
                        groups.setdefault(key,[]).append(row['row'])
                    else: retained.append(row)
                if groups:
                    view['rows']=retained;view['row_order']=order
                    view['row_refs']=[{'view_id':owner,'rows':rows,'columns':list(columns)} for (owner,columns),rows in groups.items()]
        message['content']=json.dumps(payload,ensure_ascii=False)
    old_size=len(json.dumps(messages,ensure_ascii=False,default=str))
    if removed:
        system=next((m for m in packed if m.get('role')=='system'),None)
        if system is None: packed.insert(0,{'role':'system','content':NOTE.strip()})
        else: system['content']+=NOTE
    new_size=len(json.dumps(packed,ensure_ascii=False,default=str))
    applied=removed>0 and new_size<old_size
    return (packed if applied else messages),{'applied':applied,'cells_before':before,
        'cells_after':after if applied else before,'duplicate_cells_removed':removed if applied else 0,
        'conflicting_values_retained':conflicts,'request_chars_before':old_size,
        'request_chars_after':new_size if applied else old_size,
        'note':'Character counts include reference instructions; actual token savings require API measurement.'}
