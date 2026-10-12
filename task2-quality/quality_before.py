"""T2: before-quality metrics on W (winners before validity filtering)."""
import json, duckdb
from pathlib import Path
from helpers import ratio, new_run, sha256

con = duckdb.connect('work.duckdb')
con.execute(Path('typed.sql').read_text())
con.execute(Path('quality_before.sql').read_text())
one = lambda s: con.execute(s).fetchone()[0]
run_id = new_run()
COHORT_W = 'winners before row-validity filtering (W)'

def metric(rule, cohort, n, d, thr, sev, extra=None):
    r = ratio(n, d)
    rec = dict(rule_id=rule, dataset_id='raw-winners', run_id=run_id,
               contract_version='research-telemetry-v1', cohort=cohort,
               numerator=r['n'], denominator=r['d'], value=r['value'],
               status=r['status'], threshold=thr, severity=sev)
    if r['value'] is not None and thr is not None:
        rec['observed_status'] = 'PASS' if r['value'] >= thr else 'FAIL'
    rec.update(extra or {})
    return rec

W   = one("select count(*) from winners")
ke  = one("select count(*) from key_eligible")
tok = "select count(*) from w_flags where time_ok"
m = []
m.append(metric('Q_REQUIRED', COHORT_W, one("select count(*) from w_flags where req_ok"), W, 1.0, 'BLOCK'))
m.append(metric('Q_UNIQUE_KEY', 'key-eligible records before dedup',
                one("select count(distinct record_id) from key_eligible"), ke, 1.0, 'BLOCK',
                dict(duplicate_excess=ke - one("select count(distinct record_id) from key_eligible"))))
m.append(metric('Q_VALUE', COHORT_W, one("select count(*) from w_flags where temp_c between -30 and 60"), W, 1.0, 'BLOCK'))
m.append(metric('Q_REGISTRY', COHORT_W, one("select count(*) from w_flags where ref_ok"), W, 1.0, 'BLOCK'))
m.append(metric('Q_CHRONO', COHORT_W, one(tok), W, 1.0, 'BLOCK'))
m.append(metric('Q_TIMELY', 'chronologically valid rows (lag<=900s)',
                one("select count(*) from w_flags where time_ok and lag_s<=900"), one(tok), 0.95, 'BLOCK',
                dict(excluded_not_chronologically_valid=W - one(tok))))
# Reference metrics are reported on W here; recompute on the curated candidate in T3.
agree = one("""select count(*) filter (where abs(cast(w.temp_c as decimal(8,2)) - q.reference_c) <= 0.05)
               from qa_reference q join w_flags w using(record_id)
               where w.temp_c between -30 and 60""")
matched = one("""select count(*) from qa_reference q join w_flags w using(record_id)
                 where w.temp_c between -30 and 60""")
m.append(metric('Q_QA_AGREEMENT', 'QA ids matched in valid W rows', agree, matched, 0.95, 'BLOCK'))
m.append(metric('Q_QA_COVERAGE', 'all reference ids', matched, one("select count(*) from qa_reference"), 1.0, 'BLOCK'))

counts = dict(
    raw=one("select count(*) from typed"),
    parse_failures=one("select count(*) from typed where not parse_ok"),
    key_rejected=one("""select count(*) from typed where parse_ok and not
        (regexp_full_match(coalesce(record_id,''),'R[0-9]{6}') and ingest_ts is not null)"""),
    key_eligible=ke, winners_W=W, superseded_duplicates=ke - W)
assert counts['raw'] == counts['parse_failures'] + counts['key_rejected'] + counts['superseded_duplicates'] + W

report = dict(dataset_version='batch-01', as_of='2026-02-09T00:00:00Z', run_id=run_id,
              populations=counts, metrics=m,
              hashes=dict(envelopes=sha256('envelopes.csv'), typed_sql=sha256('typed.sql'),
                          quality_sql=sha256('quality_before.sql')))
Path('quality_before.json').write_text(json.dumps(report, indent=2))
for x in m:
    print(f"{x['rule_id']:15} {x['numerator']:>5}/{x['denominator']:<5} {x['value']:.4f}  {x.get('observed_status')}")
print(counts)
