"""Bounded local retrieval of reviewed procedures activated by offline logs."""
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .error_lessons import LESSONS

DEFAULT_MEMORY = Path(__file__).resolve().parents[1] / 'config' / 'error_memory.json'
POLICY = ('Retrieved failure-prevention procedures are advisory, not source data or answers. '
          'Apply only when the current question and workbook evidence support them. '
          'The original question, tool schema and validation remain authoritative. '
          'For review, audit these risks against evidence independently of the planner; '
          'plan-building procedures describe the audited plan, not your response. '
          'Review must return only verdict/issues in the review schema.')


def normalized(text):
    return unicodedata.normalize('NFKC', str(text)).casefold()


def load_memory(path=None):
    path = Path(path) if path else DEFAULT_MEMORY
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    if path.stat().st_size > 65536:
        raise ValueError('Error memory exceeds 64 KiB')
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'lessons'}
            or data['version'] != 1 or not isinstance(data['lessons'], list)):
        raise ValueError('Invalid error memory schema')
    seen = set()
    for item in data['lessons']:
        if (not isinstance(item, dict) or set(item) != {'id', 'support'}
                or not isinstance(item['id'], str) or item['id'] not in LESSONS or item['id'] in seen
                or type(item['support']) is not int or item['support'] < 1):
            raise ValueError('Memory accepts only unique reviewed lesson IDs and positive support counts')
        seen.add(item['id'])
    return data, hashlib.sha256(raw).hexdigest()


def retrieve(memory, question, contract=None, errors=(), previews=(), top_k=3, max_chars=3600):
    """Question semantics, table structure and repair errors; never ID/file lookup."""
    q = normalized(question)
    error_text = normalized('\n'.join(str(e) for e in errors))
    contract = contract or {}
    ranked = []
    for item in memory['lessons']:
        key = item['id']; rule = LESSONS[key]; reasons = []; score = 0
        question_match = re.search(rule['question'], q)
        if question_match:
            score += 3; reasons.append('question')
        # A relevant procedure supported by observed table structure should
        # outrank generic wording such as "answer as". Structure alone must
        # never activate an unrelated lesson.
        if (question_match and rule.get('preview_feature') == 'hierarchical_columns'
                and any(any(isinstance(path, list) and len(set(map(str, path))) >= 2
                            for path in p.get('column_hierarchy', {}).values())
                        for p in previews)):
            score += 5; reasons.append('hierarchical_columns')
        if error_text and re.search(rule['error'], error_text, re.I):
            score += 8; reasons.append('repair_error')
        if any(value in rule.get('contract', ()) for value in
               (contract.get('kind'), contract.get('reduction')) if value):
            score += 4; reasons.append('answer_contract')
        if key == 'section_identity' and score and any(p.get('section_labels') for p in previews):
            score += 2; reasons.append('section_structure')
        if score:
            ranked.append({'id': key, 'score': score, 'matched_by': reasons,
                           'guidance': rule['guidance']})
    ranked.sort(key=lambda item: (-item['score'], item['id']))
    chosen = []; used = 0
    for item in ranked:
        if len(chosen) >= min(5, max(0, int(top_k))): break
        # Bound the entire serialized retrieval payload, including policy.
        trial = {'policy': POLICY, 'lessons': [*chosen, item]}
        size = len(json.dumps({'retrieved_error_lessons': trial}, ensure_ascii=False))
        if size <= min(6000, max(0, int(max_chars))):
            chosen.append(item); used = size
    return chosen, used


def augment(request, memory, digest, question, contract, errors=(), previews=(),
            top_k=3, max_chars=3600):
    lessons, chars = retrieve(memory, question, contract, errors, previews, top_k, max_chars)
    metrics = {'memory_sha256': digest, 'lessons': [
        {k: item[k] for k in ('id', 'score', 'matched_by')} for item in lessons], 'chars': chars}
    if not lessons: return request, metrics
    # Only canonical text enters the model. Raw logs and exported metadata do not.
    payload = {'policy': POLICY, 'lessons': lessons}
    result = [*request, {'role': 'user', 'content': json.dumps(
        {'retrieved_error_lessons': payload}, ensure_ascii=False)}]
    return result, metrics
