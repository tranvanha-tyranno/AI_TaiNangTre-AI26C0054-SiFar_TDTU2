"""Record reproducible input/code identities and safe execution settings."""
import hashlib
from pathlib import Path
import subprocess


def fingerprint(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def run_context(root,queries_path,xlsx_dir,queries,settings,mode,concurrency,model):
    root=Path(root)
    source={str(p.relative_to(root)).replace('\\','/'):fingerprint(p)
            for p in [root/'main.py',*sorted((root/'src').rglob('*.py'))]}
    try:
        revision=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,timeout=2)
        revision=revision.stdout.strip() if revision.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired): revision=None
    keys=['max_tokens_plan','llm_seed','max_cost_per_question','max_api_calls','max_plan_repairs',
          'question_timeout','run_timeout','max_prompt_price_per_million',
          'max_completion_price_per_million','max_workbook_cells','retrieval_top_k','preview_rows',
          'max_inspection_rounds','semantic_review','pipeline_variant','v3_max_api_calls','v3_max_repairs','v3_max_inspections',
          'lite_max_api_calls','lite_context_chars','v3_base_variant','v3_deduplicate_context','v3_reliability',
          'v3_error_memory','error_memory_path','error_memory_top_k','error_memory_max_chars']
    memory_context={}
    if settings.get('v3_base_variant') and settings.get('v3_error_memory',False):
        from .error_memory import load_memory
        memory,digest=load_memory(settings.get('error_memory_path'))
        memory_context={'error_memory_sha256':digest,'error_memory_lesson_ids':[r['id'] for r in memory['lessons']]}
    return {'git_revision':revision,'source_sha256':source,'model':model,'mode':mode,'concurrency':concurrency,**memory_context,
            'settings':{k:settings[k] for k in keys if k in settings},
            'queries_sha256':fingerprint(queries_path),
            'workbook_sha256':{name:fingerprint(Path(xlsx_dir)/name) for name in sorted({q['file_name'] for q in queries})}}
