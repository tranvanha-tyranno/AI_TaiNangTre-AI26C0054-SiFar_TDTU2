"""Reference-only evaluator for synthetic fixtures; not imported by the solver."""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


def number(value): return Decimal(str(value))
def normalized(value):
    if isinstance(value, datetime): return value.date().isoformat()
    if isinstance(value, date): return value.isoformat()
    return value


def evaluate(expr, source):
    if not isinstance(expr,dict): return expr
    kind,payload=next(iter(expr.items()))
    if kind=="field": return source["__row__"][payload]
    if kind=="records": return [{k:evaluate(v,source) for k,v in row.items()} for row in payload]
    if kind=="winner":
        return payload["right_label"] if evaluate(payload["right"],source)>evaluate(payload["left"],source) else payload["left_label"]
    if kind=="derive":
        rows=evaluate(payload["data"],source)
        result=[]
        for row in rows:
            derived=dict(row)
            for key,expression in payload["fields"].items():
                derived[key]=evaluate(expression,{**source,"__row__":derived})
            result.append(derived)
        return result
    if kind=="previous":
        rows=sorted(evaluate(payload["data"],source),key=lambda row:row[payload["order"]])
        return [{**row,"previous":rows[i-1][payload["value"]]} for i,row in enumerate(rows) if i]
    if kind=="parse":
        value=evaluate(payload,source)
        if value is None or str(value).strip() in {"", "..", "—", "(-8-)"}: return None
        text=str(value).strip().replace("$", "").replace(",", "").replace("%", "")
        return -number(text[1:-1]) if text.startswith("(") and text.endswith(")") else number(text)
    if kind=="length": return len(str(evaluate(payload,source)))
    if kind=="abs": return abs(number(evaluate(payload,source)))
    if kind=="list": return [evaluate(v,source) for v in payload]
    if kind=="format": return format_answer(evaluate(payload["value"],source),payload.get("decimals"))
    if kind=="cell": return source.get(payload)
    if kind=="range": return [source.get(f"{payload['sheet']}!{payload['column']}{r}") for r in range(payload['first'],payload['last']+1)]
    if kind=="table": return [{name:source.get(f"{payload['sheet']}!{col}{r}") for name,col in payload['columns'].items()}
                              for r in range(payload['first'],payload['last']+1)]
    if kind=="column": return [row[payload["name"]] for row in evaluate(payload["data"],source)]
    if kind=="filter":
        def keep(row):
            for key,condition in payload["conditions"].items():
                value=normalized(row[key])
                if not isinstance(condition,dict):
                    if value!=condition: return False
                else:
                    for comparator,target in condition.items():
                        if comparator=="not_blank":
                            if (value is not None and value!="")!=target: return False
                        elif value is None: return False
                        elif not {"gt":lambda:value>target,"ge":lambda:value>=target,
                                  "lt":lambda:value<target,"le":lambda:value<=target,
                                  "eq":lambda:value==target,"ne":lambda:value!=target}[comparator](): return False
            return True
        return [row for row in evaluate(payload["data"],source) if keep(row)]
    if kind=="join":
        left,right=evaluate(payload["left"],source),evaluate(payload["right"],source)
        key=payload["key"]
        lookup={row[key]:row for row in right}
        assert len(lookup)==len(right),"Reference join must have unique right keys"
        return [{**row,**lookup[row[key]]} for row in left if row[key] in lookup]
    if kind=="rank":
        rows=evaluate(payload["data"],source)
        for key,direction in reversed(payload["by"]):
            rows=sorted(rows,key=lambda r:normalized(r[key]),reverse=direction=="desc")
        rows=rows[payload["offset"]:payload["offset"]+payload["limit"]]
        return [row[col] for row in rows for col in payload["columns"]]
    if kind in {"count","sum","mean","min","max","distinct_count"}:
        values=evaluate(payload,source)
        if kind=="count": return len(values)
        if kind=="distinct_count": return len(set(map(normalized,values)))
        values=[number(v) for v in values if v is not None and v!=""]
        if kind=="sum": return sum(values,Decimal(0))
        if kind=="mean": return sum(values)/len(values)
        return min(values) if kind=="min" else max(values)
    values=[evaluate(v,source) for v in payload]
    if kind in {"days","age"}:
        start,end=[date.fromisoformat(str(normalized(v))) for v in values]
        if kind=="days": return (end-start).days
        return end.year-start.year-((end.month,end.day)<(start.month,start.day))
    a,b=values
    if kind in {"gt","lt","eq"}:
        a,b=normalized(a),normalized(b)
        return {"gt":lambda:a>b,"lt":lambda:a<b,"eq":lambda:a==b}[kind]()
    a,b=number(a),number(b)
    return {"add":lambda:a+b,"sub":lambda:a-b,"mul":lambda:a*b,"div":lambda:a/b}[kind]()


def format_answer(value,decimals=None):
    if isinstance(value,list): return ", ".join(format_answer(v,decimals) for v in value)
    if isinstance(value,bool): return "Yes" if value else "No"
    if isinstance(value,(date,datetime)): return normalized(value)
    if isinstance(value,(int,float,Decimal)):
        value=number(value)
        if decimals is not None:
            return format(value.quantize(Decimal(1).scaleb(-decimals),rounding=ROUND_HALF_UP),f".{decimals}f")
        return str(int(value)) if value==value.to_integral_value() else format(value,"f").rstrip("0").rstrip(".")
    return str(value)
