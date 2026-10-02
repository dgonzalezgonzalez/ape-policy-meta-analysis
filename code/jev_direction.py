"""Outcome-direction annotation with result-blind, outcome-relevant source context.

Covariate annotations remain frozen from the table-notes route. Only five
direction questions use selected paragraphs from data/setting sections here.
"""
import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import requests
from paths import RAW, PROCESSED
from jev_enrich import MODEL, API, build_state
from jev_questions import load_key
from parse_sde import detex

FILE = RAW/'jev_direction_context.jsonl'
PREFIX = ('Assess ONLY the conventionally favourable direction of `selected_outcome` '
          'for the people or group it measures, holding other outcomes and policy costs aside. '
          'This is an outcome-direction proxy, not net welfare, policy success, or the sign of an estimate. ')
Q = {
    'administrative_detection': {'type':'noul', 'instructions':
        'Is the selected outcome primarily a count/rate of detection, reporting, arrests, convictions, penalties, litigation or enforcement actions, rather than the incidence of underlying harm or a directly measured burden on an identified beneficiary? Answer only this literal measurement question; do not evaluate whether the policy succeeds.'},
    'group_composition': {'type':'noul', 'instructions':
        'Is the selected outcome the fraction/share of a named demographic, nationality, party or sector in a total, such that the share can rise without an absolute improvement for that group? This includes group employment/enrollment shares, vote shares and foreign population shares. Do not include mortality/illness rates, attainment probabilities, or explicitly defined earnings gaps/ratios measuring income inequality.'},
    'gross_activity': {'type':'noul', 'instructions':
        'Is the selected outcome gross financial trading/transaction volume or an administrative workflow count (applications decided, permits processed), without measuring the amount of a final beneficial service accessed or a direct income/health/learning outcome? Do not include employment, earnings, completed housing supply or actual beneficial service enrollment. Answer only this literal measurement question.'},
    'higher_benefits': {'type': 'noul', 'instructions': PREFIX +
        'Is a higher value conventionally favourable? Higher income, employment, survival, learning or access to a clearly beneficial service can qualify. Outcome definitions and beneficiaries matter. Political vote shares, population composition, migration flows, tax revenue, administrative activity, and prices without a specified beneficiary have no automatic favourable ordering.'},
    'lower_benefits': {'type': 'noul', 'instructions': PREFIX +
        'Is a lower value conventionally favourable? Lower mortality, illness, victimization, unemployment or harmful pollution can qualify. Distinguish harmful incidents from their reporting or enforcement, and beneficial services from burdens. Lower spending, use, counts or prices without a beneficiary have no automatic favourable ordering.'},
    'direction_ambiguous': {'type': 'noul', 'instructions': PREFIX +
        'Does this measured outcome itself lack a conventional favourable ordering, because its meaning/beneficiary is unknown, it is political or compositional, or both high and low values are desirable in different circumstances? Do not mark it ambiguous merely because a policy has other costs, affects other outcomes or has imperfect identification. Judge the selected measured outcome by itself. A reporting/enforcement count can remain ambiguous even when underlying harm is undesirable.'},
    'goal_increase': {'type': 'noul', 'instructions':
        'Do the source descriptions explicitly identify increasing the selected outcome as a policy objective? A research question or hypothesized coefficient alone is insufficient. This question concerns stated intent, not beneficiary welfare.'},
    'goal_decrease': {'type': 'noul', 'instructions':
        'Do the source descriptions explicitly identify decreasing the selected outcome as a policy objective? A research question or hypothesized coefficient alone is insufficient. This question concerns stated intent, not beneficiary welfare.'}
}

BLOCKED = re.compile(r'(?i)\bSDE\b|standardiz|standard errors?|p[- ]?values?|t[- ]?statistic|'
                     r'summary statistics|\bresults?\b|\bfindings?\b|we find|I find|'
                     r'statistically|significan|estimated (?:effect|coefficient)|point estimate')


def context(record):
    path = RAW/'papers'/(record['paper_version_id']+'.tex')
    if not path.exists():
        return '', []
    source = path.read_text(encoding='utf-8')
    return extract_context(source, record)


def extract_context(source, record):
    """Select context without following result-table inputs or admitting results."""
    # Never follow table inputs or read results, abstract, introduction or conclusion.
    source = re.sub(r'(?m)(?<!\\)%.*$', '', source)
    sections = list(re.finditer(r'\\section\*?(?:\[[^]]*\])?\{([^}]+)\}', source))
    selected = []
    terms = set(re.findall(r'[a-z]{4,}', (record.get('outcome_label','')+' '+
                                         (record.get('outcome_definition') or '')).lower()))
    terms -= {'main','baseline','pooled','overall','outcome','variable','defined','measure', 'measured'}
    for i, match in enumerate(sections):
        title = detex(match.group(1))
        if not re.search(r'(?i)data|setting|institutional|background|policy context|measurement', title):
            continue
        if re.search(r'(?i)result|robust|conclusion|discussion|standardiz', title):
            continue
        block = source[match.end():sections[i+1].start() if i+1<len(sections) else len(source)]
        block = re.sub(r'\\begin\{(equation\*?|align\*?|tabular\*?|table\*?|figure\*?)\}.*?\\end\{\1\}', '', block, flags=re.S)
        block = re.sub(r'\\(?:input|include|includegraphics|bibliography)(?:\[[^]]*\])?\{[^}]+\}', '', block)
        for position, paragraph in enumerate(re.split(r'\n\s*\n', block)):
            text = detex(paragraph).strip()
            if len(text)<60 or BLOCKED.search(text):
                continue
            if re.search(r'\d', text) and re.search(r'(?i)effect|estimate|coefficient|impact|increase|decrease|rose|fell|percentage points|\bpp\b', text):
                continue
            words = set(re.findall(r'[a-z]{4,}', text.lower()))
            overlap = len(terms & words)
            definition = bool(re.search(r'(?i)outcome|dependent variable|defined|measure|employment|income|mortality|population', text))
            score = 3*overlap + 2*definition + bool(re.search(r'(?i)data|measurement', title))
            selected.append((score, i, position, title, text))
    chosen = sorted(sorted(selected, key=lambda p:(-p[0],p[1],p[2]))[:7], key=lambda p:(p[1],p[2]))
    used, texts, total = [], [], 0
    for _, _, _, title, text in chosen:
        if total + len(text)>5000:
            continue
        texts.append(title+': '+text);total+=len(text)
        if title not in used:used.append(title)
    return '\n'.join(texts), used


def fingerprint(record):
    state = build_state(record)
    extra, sections = context(record)
    if extra:state['outcome_and_setting_context']=extra
    assert not BLOCKED.search(extra)
    body = {'model':MODEL, 'questions':Q, 'state':state}
    sha=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    return sha, body, {'sections':sections,'context_characters':len(extra),
                       'context_sha256':hashlib.sha256(extra.encode()).hexdigest()}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int);args=parser.parse_args()
    selected={r['paper_version_id'] for r in json.loads((RAW/'source_records.json').read_text(encoding='utf-8')) if r['has_numeric_sde']}
    records=[r for r in json.loads((PROCESSED/'parsed_full.json').read_text(encoding='utf-8')) if r['paper_version_id'] in selected]
    cached={(r['paper_version_id'],r['request_sha256']) for r in
            [json.loads(s) for s in FILE.read_text(encoding='utf-8').splitlines()] if r.get('answers')} if FILE.exists() else set()
    todo=[r for r in records if (r['paper_version_id'],fingerprint(r)[0]) not in cached]
    if args.limit:todo=todo[:args.limit]
    print('Missing contextual direction requests:',len(todo),flush=True)
    if not todo:return
    key=load_key()
    def work(record):
        import time
        sha,body,info=fingerprint(record)
        for attempt in range(4):
            response=requests.post(API,headers={'Authorization':'Bearer '+key},json=body,timeout=90)
            if response.status_code in (429,500,502,503,504):
                time.sleep(2**attempt);continue
            response.raise_for_status();obj=response.json()
            if set(obj.get('answers',{}))!=set(Q):raise ValueError('Incomplete direction response')
            return {'paper_version_id':record['paper_version_id'],'request_sha256':sha,
                    'model':obj.get('model'),'answers':obj['answers'],'usage':obj.get('usage'),
                    'accessed_at':datetime.now(timezone.utc).isoformat(),**info}
        raise RuntimeError('Direction retries exhausted')
    with FILE.open('a',encoding='utf-8') as fh, ThreadPoolExecutor(max_workers=8) as executor:
        for i,row in enumerate(executor.map(work,todo),1):
            fh.write(json.dumps(row)+'\n');fh.flush()
            if i%50==0 or i==len(todo):print('Contextual directions',i,'/',len(todo),flush=True)


if __name__=='__main__':main()
