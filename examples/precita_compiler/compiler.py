"""PRECITA: offline exact-span passage checks. No semantic verification."""
import argparse
import hashlib
import json
import re
from pathlib import Path

NUMBER = re.compile(r'(?<![\w])[-+]?\d[\d,]*(?:\.\d+)?%?(?![\w])')

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def compile_passage(data):
    if not isinstance(data, dict) or set(data) != {'source', 'target', 'bindings'}:
        raise ValueError('expected source, target, bindings')
    source, target, bindings = data['source'], data['target'], data['bindings']
    if not isinstance(source, dict) or not isinstance(target, dict) or not isinstance(bindings, list):
        raise ValueError('invalid structure')
    for item in (source, target):
        if set(item) != {'id', 'version', 'author', 'text'} or not all(isinstance(v, str) and v for v in item.values()):
            raise ValueError('incomplete document identity')
    findings = []
    seen = set()
    for b in bindings:
        if not isinstance(b, dict) or set(b) != {'id', 'kind', 'original', 'rendered', 'attributed_to'}:
            raise ValueError('invalid binding')
        if not all(isinstance(v, str) and v for v in b.values()) or b['id'] in seen or b['kind'] not in {'quote', 'number', 'attribution'}:
            raise ValueError('invalid binding fields')
        seen.add(b['id'])
        flags = []
        if b['original'] not in source['text']:
            flags.append('ORIGINAL_NOT_FOUND')
        if b['rendered'] not in target['text']:
            flags.append('RENDERED_NOT_FOUND')
        if b['kind'] == 'quote' and b['original'] != b['rendered']:
            flags.append('QUOTE_CHANGED')
        if b['kind'] == 'number' and NUMBER.findall(b['original']) != NUMBER.findall(b['rendered']):
            flags.append('NUMBER_CHANGED')
        if b['attributed_to'] != source['author']:
            flags.append('ATTRIBUTION_MISMATCH')
        findings.append({'id': b['id'], 'status': 'HOLD' if flags else 'CHECKED', 'reasons': flags})
    if not bindings:
        findings.append({'id': 'coverage', 'status': 'HOLD', 'reasons': ['NO_BINDINGS']})
    return {'schema': 'precita-compiler/0.1', 'source_id': source['id'], 'source_version': source['version'],
            'source_sha256': sha(source['text']), 'target_id': target['id'], 'target_version': target['version'],
            'target_sha256': sha(target['text']), 'findings': findings, 'coverage_complete': False,
            'authority_verified': False, 'external_effects': 0,
            'claim_ceiling': 'Only explicitly declared exact spans checked; unbound omissions and semantic changes are not detected'}

def main():
    p = argparse.ArgumentParser(description='PRECITA exact-span handoff checker')
    p.add_argument('input', type=Path)
    args = p.parse_args()
    try:
        result = compile_passage(json.loads(args.input.read_text(encoding='utf-8')))
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({'status': 'HOLD', 'error': str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(x['status'] == 'CHECKED' for x in result['findings']) else 1

if __name__ == '__main__':
    raise SystemExit(main())
