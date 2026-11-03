"""Trial ledger (sqlite). Every run is a row: dedupe by spec hash, count N per family, cap holdout looks."""
import json, os, sqlite3, time

HOME = os.environ.get('LAB_HOME', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'var'))
HOLDOUT_LOOKS_PER_FAMILY = int(os.environ.get('LAB_HOLDOUT_LOOKS', '5'))


def _db():
    os.makedirs(HOME, exist_ok=True)
    c = sqlite3.connect(os.path.join(HOME, 'ledger.sqlite'))
    c.execute('''create table if not exists runs(hash text primary key, name text, family text, known int,
                 ts text, summary text, holdout text)''')
    return c


def get(h):
    with _db() as c:
        r = c.execute('select summary, holdout from runs where hash=?', (h,)).fetchone()
    return (json.loads(r[0]), r[1]) if r else None


def family_n(family):
    with _db() as c:
        return c.execute('select count(*) from runs where family=?', (family,)).fetchone()[0]


def holdout_looks(family):
    with _db() as c:
        return c.execute("select count(*) from runs where family=? and holdout in ('PASS','REJECT')",
                         (family,)).fetchone()[0]


def put(h, spec, summary, holdout):
    with _db() as c:
        c.execute('insert or replace into runs values(?,?,?,?,?,?,?)',
                  (h, spec.get('name'), spec.get('family', 'unset'), int(spec.get('known', -1)),
                   time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), json.dumps(summary), holdout))
