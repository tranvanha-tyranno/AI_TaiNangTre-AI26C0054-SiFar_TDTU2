"""Preserve a review's verdict when only advisory size limits are exceeded."""


def bounded_review(review):
    if (not isinstance(review,dict) or set(review)!={'verdict','issues'}
            or review['verdict'] not in {'accept','revise'}
            or not isinstance(review['issues'],list)
            or not all(isinstance(s,str) and s.strip() for s in review['issues'])):
        return None, []
    changes=[]
    issues=review['issues']
    if len(issues)>5:
        changes.append({'kind':'review_issue_count','before':len(issues),'after':5})
    if any(len(s)>300 for s in issues[:5]):
        changes.append({'kind':'review_issue_length','limit':300})
    # Never convert revise to accept, or discard an issue because it was long.
    return {'verdict':review['verdict'],'issues':[s[:300] for s in issues[:5]]}, changes

