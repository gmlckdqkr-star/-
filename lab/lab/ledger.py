"""Trial ledger (sqlite). Every spec is a row: dedupe by spec hash, count N per family.
Bar results are stored per (spec hash, mode): verdict name, failed gate names and the dev-pool (<= 2014) numbers.
No holdout looks: the old per-family holdout budget is gone (lab never opens 2015+)."""
import json, os, sqlite3, time

HOME = os.environ.get('LAB_HOME', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'var'))


def _db():
    os.makedirs(HOME, exist_ok=True)
    c = sqlite3.connect(os.path.join(HOME, 'ledger.sqlite'))
    cols = [r[1] for r in c.execute('pragma table_info(runs)')]
    if 'holdout' in cols:      # a v0 ledger: it holds 2015+ holdout looks, which this lab must not read or extend
        c.close()
        raise RuntimeError(f'{HOME}/ledger.sqlite is a v0 ledger (runs.holdout column = 2015+ holdout looks); '
                           'point LAB_HOME at a new folder. lab does not migrate or read it.')
    c.execute('''create table if not exists runs(hash text primary key, name text, family text, known int,
                 ts text, summary text)''')
    c.execute('''create table if not exists bar(hash text, mode text, ts text, verdict text, failed text,
                 numbers text, primary key(hash, mode))''')
    return c


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def get(h):
    with _db() as c:
        r = c.execute('select summary from runs where hash=?', (h,)).fetchone()
    return json.loads(r[0]) if r else None


def family_n(family):
    with _db() as c:
        return c.execute('select count(*) from runs where family=?', (family,)).fetchone()[0]


def put(h, spec, summary):
    with _db() as c:
        c.execute('insert or replace into runs(hash, name, family, known, ts, summary) values(?,?,?,?,?,?)',
                  (h, spec.get('name'), spec.get('family', 'unset'), int(spec.get('known', -1)), _now(),
                   json.dumps(summary)))


def get_bar(h, mode):
    with _db() as c:
        r = c.execute('select verdict, failed, numbers from bar where hash=? and mode=?', (h, mode)).fetchone()
    return dict(verdict=r[0], failed=json.loads(r[1]), numbers=json.loads(r[2])) if r else None


def put_bar(h, mode, verdict, failed, numbers):
    with _db() as c:
        c.execute('insert or replace into bar values(?,?,?,?,?,?)',
                  (h, mode, _now(), verdict, json.dumps(failed, ensure_ascii=False),
                   json.dumps(numbers, ensure_ascii=False)))


def rows():
    with _db() as c:
        fam = c.execute('select family, count(*) from runs group by family').fetchall()
        bar = c.execute('select r.family, b.mode, b.verdict, count(*) from bar b join runs r on r.hash=b.hash '
                        'group by r.family, b.mode, b.verdict').fetchall()
    return fam, bar
