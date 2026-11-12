"""XV1 sealed block evaluator, version 6 (see PREREG_XV1_STRUCTURE.md).

Accounts
  design    ONE continuous account on the design calendar = the evaluator calendar with every row of the sealed blocks
            (10 and 12) removed and the remaining rows joined in order. Signal, weights and features are computed once,
            causally, on the full calendar and then indexed by the design rows; the return of a removed row never reaches
            the engine. It scores every DESIGN and WEAK block for candidate, reference and the holds. A join is the start
            of a block, so the 63 unscored rows of that block cover it. Up to 2015-12-31 it is the full-calendar account.
  main      the full calendar in one account. Run only inside open_g3(); scores blocks 10 and 12 only.
Score       V = liquidation value of the account (equity minus 22% tax on every realised and unrealised gain not yet taxed);
            x_k = ln(V_k / V_{k-1}) on scored rows (row rank inside its block >= 63).
            d  = candidate minus reference.
            d* = candidate minus the static-equivalent benchmark (reference plus the candidate's MEAN extra holdings held
                 constantly): the part of d that comes from WHEN the candidate holds, not from how much it holds on average.
Outputs     scalars per non-sealed block and per registered set only. No equity level, peak, cumulative figure or array ever
            leaves this module (design-block sub-block means of paired differences are the one exception: they are design
            material and are needed for the family-wise test).
Candidate   make(view) -> dict(B, bfn, bp, fstep[, G, Wt, mode, inc, RB, up, dn]); view.c is the ov.Ctx of the calendar rows, view.x the
            registered extra inputs aligned to those rows. Nothing else may be read (no dates, no row numbers, no files, no
            module-level arrays). The evaluator sets every engine term.
Two sides    The object handed to candidate code holds COPIES. The engine reads its own arrays (class _Eng: returns, cash rate,
            features, the design rows, v1's shadow levels), which candidate code never receives. Candidate source is checked
            by an import / name gate before a batch is registered and imports a small stand-in for this module (ref, std.ident).
            The full-calendar call of a configuration is made ONCE: the same result is tested (prefix, scale) and scored."""
import os, re, sys, ast, json, time, types, hashlib, weakref, builtins, warnings, contextlib
import numpy as np, pandas as pd
from scipy import stats as sps
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_xv1')   # own cache: the shared one collides with other sessions
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import jp, ov, bk, beng, rx
import mkt, md
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xeng, xdata

CAL_START, ACC_START, CAL_END = '1984-01-03', '1986-01-02', '2026-08-31'
REG_END = '2026-08-31'                 # the registered calendar end (the block table is checked only on this calendar)
A_END, OLD_END = '2015-12-31', '2014-12-31'
Y0, BLEN, EMB, NB = 1986, 3, 63, 14
SEALED = (10, 12)                      # 2016-18, 2022-24
ACTIVE_MIN = 20                        # active rows that make an active block
FAM_CORR = 0.7                         # |correlation| of design sub-block means at or above which two configurations are one family
DESIGN = (1, 3, 5, 7, 9, 11, 13)
WEAK = (0, 2, 4, 6, 8)
ENGINE = dict(cspr=10.0)               # idle cash earns nothing (owner rule 2026-11-11); everything else = beng.F1
STRESS = dict(base={}, cost2=dict(cost=0.006), delay3=dict(delay=3), delay1=dict(delay=1), tax0=dict(tax=0.0))
G1_STRESS = ('cost2', 'delay3', 'delay1', 'tax0')
D_MIN_G1, D_MIN_G3 = 0.010, 0.005      # smallest set score d (log growth per year) for G1 and for CONFIRMED
DRAWS = 200000                         # sign-flip draws of the family-wise test
OUT = '/mnt/project-files/research/xv1/'
REG_OUT = '/mnt/project-files/research/xv1/'    # the one registered output folder (self-tests point OUT elsewhere, in a test world)
WORLD = None                           # None = the real calendar. t_world sets 'old' (<= 2014) or 'synth' (made-up values after 2014)
FEE, SPREAD = 0.0095, 0.0075           # modelled funds: yearly fee, yearly spread per borrowed unit (3x: 0.0245 = beng.F1['er3'])
LVL_OK = ('lvl:_VIX3M@ext', 'lvl:_VIX9D@ext', 'lvl:_TYX@ext', 'lvl:_FVX@ext')   # level inputs that carry no price height
EXACT_SF = 20                          # sign-flip check: all 2^A assignments up to this many active sub-blocks
T0_WARM_MAX = 756                      # a registered T0 lies at most this many calendar rows after the first row on which every input exists
G2_MIN_ROWS = 252                      # fewer scored WEAK rows on or after T0: G2 is not available (and the configuration cannot be opened)
W_ACT = 0.01                           # an extra holding makes a row active only from this total actual weight on (a tiny sleeve does not)
G3_END = '2031-01-01'                  # no G3 opening on or after this date
F1 = dict(delay=2, cost=0.003, tax=0.22, W0=10000000.0, harvest=3, hthr=1.0, cspr=0.02, er3=0.0245, step=0.5, fstep=0.5)   # beng.F1 as registered
WARM = ov.WARM
assert WARM == xeng.WARM == beng.WARM
_FROZEN = dict(CAL_START='1984-01-03', ACC_START='1986-01-02', CAL_END='2026-08-31', REG_END='2026-08-31', A_END='2015-12-31',
               OLD_END='2014-12-31', Y0=1986, BLEN=3, EMB=63, NB=14, SEALED=(10, 12), ACTIVE_MIN=20, FAM_CORR=0.7,
               DESIGN=(1, 3, 5, 7, 9, 11, 13), WEAK=(0, 2, 4, 6, 8), ENGINE=dict(cspr=10.0),
               STRESS=dict(base={}, cost2=dict(cost=0.006), delay3=dict(delay=3), delay1=dict(delay=1), tax0=dict(tax=0.0)),
               G1_STRESS=('cost2', 'delay3', 'delay1', 'tax0'), D_MIN_G1=0.010, D_MIN_G3=0.005, DRAWS=200000,
               OUT=REG_OUT, FEE=0.0095, SPREAD=0.0075, EXACT_SF=20, WARM=int(WARM), T0_WARM_MAX=756, G2_MIN_ROWS=252,
               LVL_OK=('lvl:_VIX3M@ext', 'lvl:_VIX9D@ext', 'lvl:_TYX@ext', 'lvl:_FVX@ext'), W_ACT=0.01, G3_END='2031-01-01',
               F1=dict(delay=2, cost=0.003, tax=0.22, W0=10000000.0, harvest=3, hthr=1.0, cspr=0.02, er3=0.0245, step=0.5, fstep=0.5), CARRY=5)


class Void(Exception):
    """a configuration that cannot be scored; it stays in its batch and the batch level is not refunded"""


def _guard():
    """In the real world every registered constant must have its registered value (the self-tests change SEALED, DESIGN,
    CAL_END or OUT only after t_world has declared a test world, in which no real row after 2014 can be built)."""
    if WORLD is not None: return
    g = globals()
    for k, val in _FROZEN.items():
        if k == 'CARRY': continue
        if g[k] != val: raise PermissionError('registered constant %s was changed' % k)
    if dict(beng.F1) != _FROZEN['F1']: raise PermissionError('engine terms (beng.F1) changed')
    if xdata.CARRY != _FROZEN['CARRY']: raise PermissionError('carry limit of the extra inputs changed')
    if abs(beng.F1['er3'] - (FEE + 2 * SPREAD)) > 1e-15: raise PermissionError('fund model terms changed')


def _writable():
    """a test world never writes into the registered folder"""
    if WORLD is not None and os.path.realpath(OUT) == os.path.realpath(REG_OUT): raise PermissionError('a test world does not write into the registered folder')


_SCOPE = [0]
@contextlib.contextmanager
def scope():
    """Evaluator entry points (and the checks script) run inside this. Outside it no calendar after 2014-12-31 is built or
    read and no registered input is aligned to such a calendar (in every world)."""
    _SCOPE[0] += 1
    try: yield
    finally: _SCOPE[0] -= 1


def _scoped(f):
    import functools
    @functools.wraps(f)
    def w(*a, **k):
        with scope(): return f(*a, **k)
    return w


_INCALL = [0]                          # > 0 while candidate code runs (the shadow levels answer only then)
_G3_RUN = [None]                       # the hash of the opening in progress, set by _open_g3 while the main account may run
_G3_PRE = [None]                       # the hash whose main view open_g3 tests (v6: only after its G3-OPEN line)


def _registered():
    """the structure is registered: HASHES.json of the registered folder names the text whose sha256 is ledger line 0"""
    if OUT != REG_OUT or not os.path.exists(OUT + 'HASHES.json'): return False
    try:
        reg = json.load(open(OUT + 'HASHES.json')); L = read_ledger()
        txt = hashlib.sha256(open(OUT + 'PREREG_XV1_STRUCTURE.md', 'rb').read()).hexdigest()
    except Exception: return False
    return bool(L) and L[0].get('kind') == 'registration' and L[0].get('sha256') == reg.get('prereg_sha256') == txt


def kind_of(b):
    """'D' design, 'W' weak validation (<= 2014, already seen), 'S' sealed."""
    if b % 2 == 1: return 'D'
    return 'S' if b in SEALED else 'W'


def years_of(b): return '%d-%02d' % (Y0 + BLEN * b, min(Y0 + BLEN * b + BLEN - 1, int(CAL_END[:4])) % 100)


# ------------------------------------------------------------------------------------------------ calendar and views
_FR = {}
def frame(end=None):
    """X of the MS1 real-path chain on the calendar rows CAL_START..end. A real calendar after 2014 is built only in the
    real world, with the registered constants, after registration, and only to the registered end or to A_END."""
    end = end or CAL_END
    if end > OLD_END and not _SCOPE[0]: raise PermissionError('outside an evaluator entry point no calendar after %s is read' % OLD_END)
    if end not in _FR:
        if end > OLD_END:
            if WORLD is not None: raise PermissionError('test world %r: no real calendar after %s is built' % (WORLD, OLD_END))
            _guard()
            if end not in (REG_END, A_END): raise PermissionError('only the registered calendar ends are built')
            if not _registered(): raise PermissionError('the structure is not registered: no real calendar after %s (tests use t_world.old() or t_world.synth())' % OLD_END)
        R, M = jp.calendar(CAL_START, end); _FR[end] = jp.mkX(R, M, 'NDX')
    return _FR[end]


def extras(names, idx):
    """registered extra inputs as full-length arrays aligned to the calendar idx (fresh copies)."""
    if len(idx) and idx[-1] > pd.Timestamp(OLD_END) and not _SCOPE[0]: raise PermissionError('outside an evaluator entry point no input after %s is read' % OLD_END)
    for k in names:
        if k.startswith('lvl:') and k not in LVL_OK: raise PermissionError('level input %s is not on the allow-list (a price height names an era)' % k)
    return {k: np.array(xdata.get(k, idx), dtype=np.float64) for k in names}


class _ROCache(dict):
    """the Ctx cache of a candidate view: every array stored in it is write-protected"""
    def __setitem__(s, k, a):
        if isinstance(a, np.ndarray): a.setflags(write=False)
        dict.__setitem__(s, k, a)


class _Eng:
    """Evaluator side of a view: the arrays the engine reads (index return, cash rate, features), the rows of the design
    account, the registered inputs and v1's shadow levels. Built from the frame, never handed to candidate code."""
    def __init__(s, X, F, i0, extra, account):
        s.c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); s.c.ii = None; s.T = s.c.T; s.account = account
        s.r = np.ascontiguousarray(s.c.r[0]); s.rf = np.ascontiguousarray(s.c.rf[0])
        s.rb = None if s.c.rb is None else np.ascontiguousarray(s.c.rb[0])
        s.feat = np.ascontiguousarray(bk.features(s.c)[0])
        blk = np.asarray((X.index[i0 + WARM:].year - Y0) // BLEN)
        s.keep = np.r_[np.arange(WARM), WARM + np.flatnonzero(~np.isin(blk, SEALED))]   # view rows of the design account
        s.x = {k: np.array(a[i0:len(X)], dtype=np.float64) for k, a in (extra or {}).items()}
        s._shadow = None; s.touched = set()             # which of m / ref_target / ref_held candidate code asked for
        for a in [s.r, s.rf, s.feat, s.keep] + list(s.x.values()): a.setflags(write=False)

    def shadow(s):
        """v1 alone in a shadow account, base terms (level paths only; warm-up rows are 0). In a design view the rows of the
        design account carry v1's levels in the design account (the account the candidate is scored in) and the removed
        rows carry its levels in the full-calendar account; in a main view every row carries the full-calendar account."""
        if s._shadow is None:
            m = _refm(s.c, s.T); rec = _run_eng(s, m)
            tg = np.r_[np.zeros(WARM), rec[:, 2]]; hd = np.r_[np.zeros(WARM), np.maximum(rec[:, 1], 0.0)]
            if s.account == 'design' and len(s.keep) < s.T:
                rd = _run_eng(s, m, s.keep); kd = s.keep[WARM:]
                tg[kd] = rd[:, 2]; hd[kd] = np.maximum(rd[:, 1], 0.0)
            s._shadow = (np.ascontiguousarray(tg), np.ascontiguousarray(hd))
            for a in s._shadow: a.setflags(write=False)
        return s._shadow


_ENG = weakref.WeakKeyDictionary()                 # view -> its evaluator side (candidate code cannot reach this table)
def _eng(v): return _ENG[v]


class View:
    """What candidate code may read: c (ov.Ctx, P = 1), m (the macro levels y10, y3m, cs of the REF chain), x (dict of
    registered extra inputs), feat, ref_target and ref_held, all on the same T rows (WARM warm-up rows, then the account
    days). Every array is a copy made for this object and is write-protected; the calendar position (c.ii), the dates, the
    kind of account and the list of design rows are not on it. The engine never reads from this object."""
    def __init__(s, X, extra=None, account='design'):
        _guard()
        i0 = int(X.index.searchsorted(pd.Timestamp(ACC_START))) - WARM; F = ov.flags_hist(X)
        _ENG[s] = _Eng(X, F, i0, extra, account)
        s.c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); s.c.ii = None; s.c._c = _ROCache()
        s.T = s.c.T
        s.x = {k: np.array(a[i0:len(X)], dtype=np.float64) for k, a in (extra or {}).items()}
        s._m = {k: np.array(X[k].values[i0:len(X)], dtype=np.float64) for k in ('y10', 'y3m', 'cs')}   # macro levels of the REF chain
        s._feat = None
        for a in _inputs(s): a.setflags(write=False)                                 # candidate code cannot change an input in place

    @property
    def m(s):
        _ENG[s].touched.add('m'); return s._m

    @property
    def feat(s):
        if s._feat is None: s._feat = np.array(_ENG[s].feat); s._feat.setflags(write=False)
        return s._feat

    @property
    def ref_target(s):
        """level v1 wants after its brake, decided at the close of row t (in force two rows later)"""
        if WORLD is None and not _INCALL[0]: raise PermissionError('the shadow levels are read only by candidate code')
        _ENG[s].touched.add('ref'); a = np.array(_ENG[s].shadow()[0]); a.setflags(write=False); return a

    @property
    def ref_held(s):
        """level v1 actually holds on row t"""
        if WORLD is None and not _INCALL[0]: raise PermissionError('the shadow levels are read only by candidate code')
        _ENG[s].touched.add('ref'); a = np.array(_ENG[s].shadow()[1]); a.setflags(write=False); return a


def _inputs(v):
    return [a for a in [v.c.r, v.c.rf, v.c.lvl, v.c.vix, v.c.rb] + list(v.c.F.values()) + list(v.x.values()) + list(v._m.values()) if isinstance(a, np.ndarray)]


def _digest(v):
    """fingerprint of everything on a candidate view: values, identities and write flags of its input arrays"""
    h = hashlib.sha1()
    for a in _inputs(v): h.update(a.tobytes()); h.update(b'%d,%d;' % (id(a), int(a.flags.writeable)))
    h.update(repr((v.T, sorted(v.x), sorted(v.c.F), sorted(v._m))).encode())
    return h.hexdigest()


def acc_dates(X):
    i0 = int(X.index.searchsorted(pd.Timestamp(ACC_START))) - WARM
    return X.index[i0 + WARM:]


BLOCK_TABLE = (  # (b, first row, first scored row, last row, rows): part of the registered text, from the calendar dates only
    (0, '1986-01-02', '1986-04-03', '1988-12-30', 759), (1, '1989-01-03', '1989-04-04', '1991-12-31', 758),
    (2, '1992-01-02', '1992-04-01', '1994-12-30', 759), (3, '1995-01-03', '1995-04-03', '1997-12-31', 759),
    (4, '1998-01-02', '1998-04-03', '2000-12-29', 756), (5, '2001-01-02', '2001-04-03', '2003-12-31', 752),
    (6, '2004-01-02', '2004-04-02', '2006-12-29', 755), (7, '2007-01-03', '2007-04-04', '2009-12-31', 756),
    (8, '2010-01-04', '2010-04-06', '2012-12-31', 754), (9, '2013-01-02', '2013-04-04', '2015-12-31', 756),
    (10, '2016-01-04', '2016-04-05', '2018-12-31', 754), (11, '2019-01-02', '2019-04-03', '2021-12-31', 757),
    (12, '2022-01-03', '2022-04-04', '2024-12-31', 753), (13, '2025-01-02', '2025-04-04', '2026-08-31', 416))


def check_calendar(cal, upto=None):
    """stop if the calendar does not reproduce the registered block table. The registered calendar is checked in full, the
    calendar cut at A_END on blocks 0-9; a test world with another calendar end skips it."""
    last = str(cal.dates[-1].date())
    if upto is None: upto = NB if last == _FROZEN['REG_END'] else (10 if last == _FROZEN['A_END'] else 0)
    got = {r['b']: (r['first'], r['first_scored'], r['last'], r['rows']) for r in cal.table()}
    for b, f, fs, l, n in BLOCK_TABLE[:upto]:
        if got.get(b) != (f, fs, l, n): raise RuntimeError('calendar does not match the registered block table at block %d' % b)


class Cal:
    """block calendar of the account days"""
    def __init__(s, dates):
        s.dates = dates; s.n = len(dates)
        s.blk = ((dates.year - Y0) // BLEN).astype(int)
        first = np.r_[True, s.blk[1:] != s.blk[:-1]]
        start = np.maximum.accumulate(np.where(first, np.arange(s.n), 0))
        s.rank = np.arange(s.n) - start              # 0-based trading-day number inside the block
        s.scored = s.rank >= EMB                     # the first EMB rows of every block are not scored

    def rows(s, b): return np.flatnonzero(s.blk == b)

    def table(s):
        """block boundaries: dates and counts only"""
        out = []
        for b in range(NB):
            r = s.rows(b)
            if not len(r): continue
            out.append(dict(b=b, kind=kind_of(b), years=years_of(b), first=str(s.dates[r[0]].date()),
                            first_scored=str(s.dates[r[min(EMB, len(r) - 1)]].date()), last=str(s.dates[r[-1]].date()),
                            rows=int(len(r)), scored=int(max(len(r) - EMB, 0))))
        return out


# ------------------------------------------------------------------------------------------------ candidates
def ref(v):
    B, bfn, bp, fs = std.s085(v.c); return dict(B=np.ascontiguousarray(np.asarray(B, dtype=np.float64).reshape(-1)), bfn=bfn, bp=bp, fstep=fs)


def _refm(c, T):
    """v1 on the evaluator's own context"""
    B, bfn, bp, fs = std.s085(c)
    if bfn is not _REFB or not np.array_equal(np.asarray(bp, dtype=np.float64), _REFP) or fs != _REFS: raise RuntimeError('v1 is not the registered rule')
    return _norm(dict(B=B, bfn=bfn, bp=bp, fstep=fs), T)


def hold3(v): return dict(B=np.full(v.T, 3.0), bfn=std.ident, bp=np.zeros(1), fstep=0.5)


def hold1(v):
    """1x index hold (0.2%/yr cost) as one extra instrument at constant weight 1: bought once, never rebalanced, taxed like the rest."""
    g = v.c.r[0] - 0.002 / 252
    return dict(B=np.zeros(v.T), bfn=std.ident, bp=np.zeros(1), fstep=0.5, G=g[:, None], Wt=np.ones((v.T, 1)), mode=1, inc=0)


def lev(r1, rf, L):
    """modelled daily-reset fund on a 1x daily return (the evaluator's own copy of the rule in cand/cbase.py):
    L = 3, 2: L r1 - (L - 1) rf - (FEE + SPREAD (L - 1)) / 252;  L = -1: -r1 + rf - FEE / 252;  L = 1: r1 - 0.002 / 252."""
    if L == 1: return r1 - 0.002 / 252
    if L < 0: return L * r1 + rf - FEE / 252
    return L * r1 - (L - 1) * rf - (FEE + SPREAD * (L - 1)) / 252


def _deny(*a, **k): raise PermissionError('a data reader was called from candidate code')


@contextlib.contextmanager
def _sandbox():
    """while candidate code runs: output streams closed, warnings dropped, numpy's error state set to its defaults with no
    call-back, data readers replaced by functions that raise"""
    spots = [(mkt, '_panel'), (mkt, 'fred'), (mkt, 'pser'), (md, 'load'), (md, 'kf'), (jp, 'calendar'), (jp, 'build'), (np, 'load'), (np, 'save'),
             (np, 'fromfile'), (np, 'loadtxt'), (np, 'genfromtxt'), (pd, 'read_csv'), (xdata, 'get'), (xdata, 'read_chips')]
    old = [getattr(o, n) for o, n in spots]; err, call = np.geterr(), np.geterrcall()
    with open(os.devnull, 'w') as nul, contextlib.redirect_stdout(nul), contextlib.redirect_stderr(nul), warnings.catch_warnings():
        warnings.simplefilter('ignore')                  # v6: no warning text or count leaves a candidate call
        for o, n in spots: setattr(o, n, _deny)
        np.seterr(divide='warn', over='warn', under='ignore', invalid='warn'); np.seterrcall(None); _INCALL[0] += 1   # no state survives in numpy's global slots
        try: yield
        finally:
            _INCALL[0] -= 1; np.seterr(**err); np.seterrcall(call)
            for (o, n), f in zip(spots, old): setattr(o, n, f)


_REFB, _REFP, _REFS = rx.av23s, np.asarray(rx.P_av23s(.85), dtype=np.float64), 0.1     # v1's brake, its parameters, its order step
def _norm(m, T):
    """normalise and validate what candidate code returned. Anything outside the rules raises Void."""
    def bad(why): raise Void('output rule: ' + why)
    if type(m) is not dict or any(k not in m for k in ('B', 'bfn', 'bp', 'fstep')): bad('missing B, bfn, bp or fstep')
    for k, a in m.items():                               # plain values only: numbers, number arrays, lists / tuples of them, the brake function
        if k == 'bfn' or a is None: continue
        if isinstance(a, np.ndarray):
            if a.dtype.kind not in 'biuf': bad('array of type %s' % a.dtype.kind)
        elif type(a) in (list, tuple):
            if not all(type(x) in (int, float, bool) or isinstance(x, (np.number, np.bool_, np.ndarray)) for x in np.ravel(np.asarray(a, dtype=object))): bad('list of non-numbers')
        elif not (type(a) in (int, float, bool) or isinstance(a, (np.number, np.bool_))): bad('value of type %s' % type(a).__name__)
    o = dict(B=np.ascontiguousarray(np.asarray(m['B'], dtype=np.float64).reshape(-1)), bfn=m['bfn'],
             bp=np.asarray(m['bp'], dtype=np.float64).reshape(-1), fstep=float(m['fstep']), mode=m.get('mode', 0), inc=m.get('inc', 0))
    if len(o['B']) != T: bad('length of B')
    if not (np.isfinite(o['B']).all() and o['B'].min() >= 0 and o['B'].max() <= 3): bad('B outside 0..3 or not finite')
    if o['mode'] not in (0, 1) or o['inc'] not in (0, 1): bad('mode or inc not 0 / 1')
    o['mode'] = int(o['mode']); o['inc'] = int(o['inc'])
    if o['bfn'] is _REFB:                                # v1's brake: exactly its parameters and its order step
        if not (o['bp'].shape == _REFP.shape and np.array_equal(o['bp'], _REFP) and o['fstep'] == _REFS): bad('brake parameters or order step differ from v1')
    elif o['bfn'] is std.ident:
        if not (np.isfinite(o['fstep']) and o['fstep'] > 0 and np.isfinite(o['bp']).all()): bad('order step')
    else: bad('a brake other than v1 or none')
    G, W = m.get('G'), m.get('Wt')
    if G is None: G = np.zeros((T, 1)); W = np.zeros((T, 1))
    try: G = np.asarray(G, dtype=np.float64).reshape(T, -1); W = np.asarray(W, dtype=np.float64).reshape(T, -1)
    except Exception: bad('shape of G or Wt')
    if G.shape != W.shape: bad('shape of G and Wt')
    W = np.where(np.isnan(W), 0.0, W); J = G.shape[1]
    if not (np.isfinite(W).all() and W.min() >= 0 and W.max() <= 1 and W.sum(axis=1).max() <= 1 + 1e-9): bad('weight outside 0..1, not finite, or weights of a row above 1')
    gn = np.isnan(G)
    if not (np.isfinite(G[~gn]).all() and (G[~gn] > -1).all()): bad('instrument return not finite or at or below -100%')
    RB = m.get('RB')
    try: RB = np.zeros((T, J)) if RB is None else np.nan_to_num(np.asarray(RB, dtype=np.float64).reshape(T, J))
    except Exception: bad('shape of RB')
    if not np.isin(RB, (0.0, 1.0)).all(): bad('rebalance flag not 0 / 1')
    o['RB'] = np.ascontiguousarray(RB)
    try:
        o['up'] = np.full(J, xeng.OFF) if m.get('up') is None else np.asarray(m['up'], dtype=np.float64).reshape(J)
        o['dn'] = np.full(J, xeng.OFF) if m.get('dn') is None else np.asarray(m['dn'], dtype=np.float64).reshape(J)
    except Exception: bad('shape of the bands')
    if not (np.isfinite(o['up']).all() and np.isfinite(o['dn']).all() and o['up'].min() >= 0 and o['dn'].min() >= 0): bad('band below 0 or not finite')
    for j in range(J):                                  # a weight may never rest on an instrument that does not exist yet
        if gn[:, j].any():
            on = (W[:, j] != 0).astype(float); held = np.convolve(on, np.ones(5), 'full')[:T] > 0
            if (held & gn[:, j]).any(): raise Void('output rule: weight on a missing instrument')
    o['Graw'] = np.ascontiguousarray(G); o['G'] = np.ascontiguousarray(np.where(gn, 0.0, G)); o['Wt'] = np.ascontiguousarray(W)
    return o


def _call(make, v):
    """run candidate code inside the sandbox on a candidate view; its inputs must come back untouched"""
    d0 = _digest(v)
    try:
        with _sandbox(): m = make(v)
    except (KeyboardInterrupt, Void): raise              # the operator's stop (candidate code has no name for it); a gate or load Void as it is
    except BaseException as e: raise Void('error in candidate code: ' + type(e).__name__)
    if _digest(v) != d0: raise Void('candidate code changed or replaced an input')
    try: return _norm(m, v.T)
    except Void: raise
    except Exception: pass
    raise Void('output rule: an output is not a plain number array')


_ONE_X = tuple('ret:' + k for k in ('SOXX', 'SMH', 'TLT', 'IEF', 'SHY', 'GLD', 'SPY', 'QQQ', 'IWM', 'IYR', 'DIA', 'VTI', 'EFA', 'EEM',
                                    'HYG', 'LQD', 'AGG', 'XLK', 'XLE', 'XLF', 'XLV', 'XLU', 'XLP', 'XLI', 'XLY', 'XLB', 'XLC', 'XLRE'))
_LEV = {'ret:SOXL': (3,), 'ret:USD': (2,), 'ret:TQQQ': (3,), 'ret:QLD': (2,), 'ret:PSQ': (-1,), 'ret:TMF': (3,), 'ret:TNA': (3,),
        'ret:TECL': (3,), 'ret:FAS': (3,), 'ret:ERX': (2, 3), 'ret:DRN': (3,)}     # v6: leverage of each registered fund (ERX: 3x to 2020, 2x after)
def _is_1x(k): return k in ('ndx', 'bond', 'chips', 'semis') or k.startswith('kf:') or k.split('@')[0] in _ONE_X


def _g_check(v, m):
    """Every instrument return the candidate hands to the engine must be one it could have held: a registered return input,
    the modelled fund (L = 3, 2, 1, -1) on the index, on the chain's bond return, on a registered 1x return input or on the
    splice of two of them, or the splice of a registered fund return with such a model of the fund's own leverage (v6: a
    model never rests on a leveraged or inverse series, and a real fund is never spliced with a model of other leverage). Checked on the full view against the
    evaluator's own arrays; a column that matches none of these voids the configuration."""
    e = _eng(v); one = {'ndx': e.r}
    if e.rb is not None: one['bond'] = e.rb
    one.update({k: a for k, a in e.x.items() if not (k.startswith('lvl:') or k.startswith('cal:'))})
    unl = {k: a for k, a in one.items() if _is_1x(k)}                               # v6: a fund is modelled only on an unlevered series
    base = dict(unl)
    for a in unl:
        for b in unl:
            if a != b: base[a + '|' + b] = None                                       # splice of two 1x series, built when needed
    act = {None: None}; act.update({k: a for k, a in e.x.items() if k.split('@')[0] in _LEV or k.split('@')[0] in _ONE_X})
    def bser(k):
        if base[k] is None: a, b = k.split('|'); base[k] = np.where(np.isnan(one[a]), one[b], one[a])
        return base[k]
    def eq(x, y): return bool(np.all((np.isnan(x) & np.isnan(y)) | (np.abs(x - y) <= 1e-12)))
    how = []
    for j in range(m['Graw'].shape[1]):
        if not (m['Wt'][:, j] != 0).any(): how.append(None); continue               # never held: its return is never used
        g = m['Graw'][:, j]; ok = np.flatnonzero(~np.isnan(g)); found = None
        I = np.unique(np.r_[ok[:8], ok[-8:], ok[::max(len(ok) // 48, 1)]]) if len(ok) else np.zeros(0, dtype=int)
        for k, a in one.items():
            if eq(g, a): found = ('input', k); break
        if found is None:
            for L in (3, 2, 1, -1):
                for k in base:
                    mod = lev(bser(k), e.rf, L)
                    for ka, a in act.items():
                        if ka is not None and L not in _LEV.get(ka.split('@')[0], (1,)): continue    # v6: the real fund's own leverage only
                        c = mod[I] if a is None else np.where(np.isnan(a[I]), mod[I], a[I])
                        if eq(g[I], c) and eq(g, mod if a is None else np.where(np.isnan(a), mod, a)): found = (ka, k, L); break
                    if found: break
                if found: break
        if found is None: raise Void('instrument check: return column %d is not a registered input, a modelled fund on one, or their splice' % j)
        how.append(found)
    return how


def _run_eng(e, m, rows=None, **stress):
    """the account on the given view rows, joined in order (None = every row of the view), from the evaluator's own arrays"""
    k = dict(ENGINE); k.update(stress); k['fstep'] = m['fstep']; q = slice(None) if rows is None else rows
    return xeng.run(e.r[q], e.rf[q], m['B'][q], e.feat[q], m['bfn'], m['bp'], G=m['G'][q], Wt=m['Wt'][q],
                    mode=m['mode'], inc=m['inc'], RB=m['RB'][q], up=m['up'], dn=m['dn'], **k)


def _run(v, m, rows=None, **stress): return _run_eng(_eng(v), m, rows, **stress)


def _x(V):
    x = np.full(len(V), np.nan); x[1:] = np.log(V[1:] / V[:-1]); return x


# ------------------------------------------------------------------------------------------------ accounts (internal)
def _blocks_of(e, m, rec, rows, cal, blocks):
    """per-block material on the scored rows: x (daily log growth of V), level in force, total weight of the extras, actual
    weight of the 3x fund (a0) and of each extra (aw), daily return of each extra (g), whether it exists on the row (gok), the
    3x fund's return (r3), dates. rows = view rows of the account days of rec (after the warm-up)."""
    if not (np.isfinite(rec[:, 4]).all() and (rec[:, 4] > 0).all()): raise Void('account value not finite or not positive')
    days = rows - WARM; x = _x(rec[:, 4]); out = {}
    r3 = 3 * e.r[rows] - 2 * e.rf[rows] - beng.F1['er3'] / 252
    for b in blocks:
        p = np.flatnonzero(cal.blk[days] == b); sc = p[cal.rank[days[p]] >= EMB]
        if not len(p): continue
        out[int(b)] = dict(x=x[sc], lev=rec[sc, 1], w=rec[sc, 5], a0=rec[sc, 6], aw=rec[sc, 7:], g=m['G'][rows[sc]],
                           gok=~np.isnan(m['Graw'][rows[sc]]), r3=r3[sc], date=cal.dates[days[sc]])
    return out


def _prepare(make, names=(), end=None, account='design'):
    """THE full-calendar call of a configuration: frame, registered inputs, candidate view, the candidate's output (validated,
    instruments checked). Everything that tests or scores the configuration afterwards uses this one result."""
    _guard(); X = frame(end or CAL_END); E = extras(names, X.index); v = View(X, E, account); m = _call(make, v); _g_check(v, m)
    return dict(X=X, E=E, v=v, m=m)


def _design_account(make=None, names=(), end=None, pre=None, **stress):
    """every non-sealed block from the design account (one continuous account on the calendar without the sealed rows)"""
    pre = pre or _prepare(make, names, end); X, v, m = pre['X'], pre['v'], pre['m']; e = _eng(v)
    if e.account != 'design': raise PermissionError('not a design view')
    cal = Cal(acc_dates(X)); check_calendar(cal)
    rec = _run_eng(e, m, e.keep, **stress)
    return _blocks_of(e, m, rec, e.keep[WARM:], cal, [b for b in range(NB) if b not in SEALED])


def _main_account(make=None, names=(), pre=None, **stress):
    """the sealed blocks from the main account (full calendar). Runs only while a G3 opening is in progress: the last
    ledger line must be a G3-OPEN line that has no verdict yet (open_g3 writes it, under its lock)."""
    L = read_ledger()
    if _G3_RUN[0] is None or not L or L[-1].get('kind') != 'G3-OPEN' or L[-1].get('cfg') != _G3_RUN[0]: raise PermissionError('sealed block')
    pre = pre or _prepare(make, names, None, 'main'); X, v, m = pre['X'], pre['v'], pre['m']; e = _eng(v)
    if e.account != 'main': raise PermissionError('not a main view')
    cal = Cal(acc_dates(X)); check_calendar(cal)
    rec = _run_eng(e, m, None, **stress)
    return _blocks_of(e, m, rec, np.arange(WARM, e.T), cal, SEALED)


def _open_blocks(make=None, names=(), **kw): return _design_account(make, names, **kw)


# ------------------------------------------------------------------------------------------------ statistics
def ann(xs):
    """annualised log growth of a list of per-block arrays (days pooled)"""
    n = sum(len(x) for x in xs)
    return float(252.0 * sum(float(np.sum(x)) for x in xs) / n) if n else float('nan')


def sub_means(d, L):
    """means of consecutive sub-blocks of L rows; leftover rows join the last sub-block"""
    k = max(len(d) // L, 1); j = np.minimum(np.arange(len(d)) // L, k - 1)
    return np.bincount(j, weights=d, minlength=k) / np.bincount(j, minlength=k)


def test_t(ds, L):
    """test T: one-sided Student t on the sub-block means of the paired daily differences (sub-blocks stay inside a calendar block)"""
    m = np.concatenate([sub_means(d, L) for d in ds if len(d)]); k = len(m)
    sd = float(m.std(ddof=1)) if k > 1 else 0.0
    if sd <= 0: return 0.0, 1.0, k, float(m.mean()), 0.0
    se = sd / np.sqrt(k); t = float(m.mean() / se)
    return t, float(sps.t.sf(t, k - 1)), k, float(m.mean()), se


def p_t(ds): return max(test_t(ds, 63)[1], test_t(ds, 126)[1])


def sub_sums(d, L=63):
    k = max(len(d) // L, 1); j = np.minimum(np.arange(len(d)) // L, k - 1)
    return np.bincount(j, weights=d, minlength=k)


def p_sf(ds, seed=0, act=None):
    """sign-flip check for differences that live in a few episodes. The sums of the active 63-row sub-blocks get random
    signs; p = share of sign assignments whose total is at least the observed total (all 2^A assignments up to A = EXACT_SF
    = 20 active sub-blocks, so the sealed set, which has 20 sub-blocks, never needs a seed; otherwise 100,000 drawn ones).
    Active sub-block: with `act` (per block, the boolean array of active rows) a sub-block that contains an active row; the
    other sub-blocks are not flipped, however small their sums (after the first divergence two accounts differ a little on
    every row). Without `act`: a sub-block whose sum is not 0. v6: the result is at least 2^-A_eff, A_eff = (sum |s|)^2 /
    sum s^2 (the effective number of active sub-blocks), so many tiny active sub-blocks around one or two large ones do
    not buy a small p."""
    s = []
    for i, d in enumerate(ds):
        if not len(d): continue
        ss = sub_sums(d)
        if act is None: s.append(ss[ss != 0])
        else:
            k = len(ss); j = np.minimum(np.arange(len(d)) // 63, k - 1)
            s.append(ss[np.bincount(j, weights=np.asarray(act[i], dtype=float), minlength=k) > 0])
    s = np.concatenate(s) if s else np.zeros(0); A = len(s)
    if A == 0 or not np.any(s): return 1.0
    floor = 2.0 ** -(float(np.abs(s).sum()) ** 2 / float(np.sum(s * s)))   # v6: 2^-A_eff, A_eff = (sum |s|)^2 / sum s^2
    return max(floor, _p_sf_count(s, seed))


def _p_sf_count(s, seed):
    A = len(s); obs = float(s.sum()); tol = 1e-12 * float(np.abs(s).sum())
    if A <= EXACT_SF:
        cnt = 0; hi = s[10:]; nh = len(hi)                    # the first 10 signs enumerated in one block, the rest in a loop
        lo = (((np.arange(2 ** min(A, 10))[:, None] >> np.arange(min(A, 10))) & 1) * 2.0 - 1.0) @ s[:10]
        for u in range(2 ** nh):
            off = float((((u >> np.arange(nh)) & 1) * 2.0 - 1.0) @ hi) if nh else 0.0
            cnt += int(np.sum(lo + off >= obs - tol))
        return cnt / float(2 ** A)
    g = np.random.default_rng(seed); cnt = 0
    for _ in range(20):
        S = g.integers(0, 2, (5000, A)) * 2.0 - 1.0; cnt += int(np.sum(S @ s >= obs - tol))
    return (1 + cnt) / (100000 + 1)


def p_test(ds, seed=0, act=None):
    """test T as used by G3: the larger of the Student-t p (L = 63 and 126) and the sign-flip p"""
    return max(p_t(ds), p_sf(ds, seed, act))


def ci90(ds):
    """two-sided 90% interval of the annualised paired difference (the wider of L = 63 and 126)"""
    best = None
    for L in (63, 126):
        t, p, k, mu, se = test_t(ds, L); h = float(sps.t.ppf(0.95, k - 1)) * se if k > 1 else float('inf')
        c = (252 * (mu - h), 252 * (mu + h))
        if best is None or c[1] - c[0] > best[1] - best[0]: best = c
    return [float(best[0]), float(best[1])]


def te_of(ds):
    d = np.concatenate([x for x in ds if len(x)])
    return float(np.sqrt(252.0) * d.std(ddof=1)) if len(d) > 1 else 0.0


def max_t(M, draws=DRAWS, seed=0):
    """family-wise adjusted p-values (single-step max-t, sign flips of whole sub-blocks, common to all configurations).
    M (k, N): sub-block means of the paired differences of N configurations on the same k design sub-blocks."""
    k, N = M.shape; ssq = (M * M).sum(0)
    def tt(mu):
        var = (ssq - k * mu * mu) / (k - 1); ok = var > 0
        return np.where(ok, mu / np.sqrt(np.where(ok, var, 1.0) / k), 0.0)
    t0 = tt(M.mean(0)); g = np.random.default_rng(seed); cnt = np.zeros(N); done = 0
    while done < draws:
        c = min(2000, draws - done); S = g.integers(0, 2, (c, k)) * 2.0 - 1.0
        mx = tt(S @ M / k).max(1)
        cnt += (mx[None, :] >= t0[:, None]).sum(1); done += c
    return t0, (1 + cnt) / (draws + 1)


# ------------------------------------------------------------------------------------------------ public measurements
_REF = {}
def _ref_blocks(stress='base'):
    if stress not in _REF:
        if 'pre' not in _REF: _REF['pre'] = _prepare(ref)
        _REF[stress] = _design_account(pre=_REF['pre'], **STRESS[stress])
    return _REF[stress]


def _levels(o):
    lv = o['lev']; u, n = np.unique(np.round(lv, 2), return_counts=True)
    return dict(share={('%.1f' % a): round(float(c) / len(lv), 4) for a, c in zip(u, n)}, changes=int(np.sum(lv[1:] != lv[:-1])),
                mean_level=round(float(lv.mean()), 4), dd_inblock=round(float(np.expm1(_dd(o['x']))), 4))


def _dd(x):
    """largest drawdown of the curve re-based to 1 on the first scored row of the block"""
    c = np.cumsum(x); return float(np.min(c - np.maximum.accumulate(np.r_[0.0, c])[1:])) if len(c) else 0.0


@_scoped
def reference_table():
    """first measurement: v1, 1x hold and 3x hold on every DESIGN and WEAK block. Scalars only. (The 1x hold is an extra
    instrument: the engine's yearly loss harvest and deduction step-up exist for the 3x fund only, so the 1x row has none.)"""
    _check_env(); R = _ref_blocks(); H1 = _open_blocks(hold1); H3 = _open_blocks(hold3); rows = []
    R0 = _ref_blocks('tax0'); H10 = _open_blocks(hold1, **STRESS['tax0']); H30 = _open_blocks(hold3, **STRESS['tax0'])
    for b in sorted(R):
        r = dict(b=b, years=years_of(b), kind=kind_of(b), account='design', n=int(len(R[b]['x'])),
                 v1=ann([R[b]['x']]), hold1=ann([H1[b]['x']]), hold3=ann([H3[b]['x']]))
        r.update(_levels(R[b])); rows.append(r)
    sets = {}
    post = lambda o, b: o[b]['x'][o[b]['date'] >= pd.Timestamp('2015-01-01')]
    for nm, bl, f in (('design', DESIGN, None), ('weak', WEAK, None), ('design_post2014', (9, 11, 13), post)):
        g = lambda o: [f(o, b) if f else o[b]['x'] for b in bl]
        a, h1, h3 = g(R), g(H1), g(H3)
        dA = [x - y for x, y in zip(a, h3)]; dB = [x - y for x, y in zip(a, h1)]
        a0, h10, h30 = g(R0), g(H10), g(H30)
        dA0 = [x - y for x, y in zip(a0, h30)]; dB0 = [x - y for x, y in zip(a0, h10)]
        sets[nm] = dict(n=int(sum(len(x) for x in a)), v1=ann(a), hold1=ann(h1), hold3=ann(h3),
                        D_A_v1_minus_3x=dict(d=ann(dA), ci90=ci90(dA)), D_B_v1_minus_1x=dict(d=ann(dB), ci90=ci90(dB)),
                        tax0=dict(v1=ann(a0), hold1=ann(h10), hold3=ann(h30),
                                  D_A_v1_minus_3x=dict(d=ann(dA0), ci90=ci90(dA0)), D_B_v1_minus_1x=dict(d=ann(dB0), ci90=ci90(dB0))))
    return dict(blocks=rows, sets=sets)


@_scoped
def model_check():
    """modelled 3x fund against the actual TQQQ on the scored rows of non-sealed blocks where the fund exists. Scalars only."""
    _check_env(); X = frame(CAL_END); idx = X.index; cal = Cal(acc_dates(X)); i0 = len(idx) - cal.n
    a = extras(('ret:TQQQ',), idx)['ret:TQQQ'][i0:]; r = X['r'].values[i0:]; rf = X['rf'].values[i0:]
    m = 3 * r - 2 * rf - beng.F1['er3'] / 252; out = []
    for b in range(NB):
        if b in SEALED: continue
        rr = cal.rows(b); sc = rr[cal.rank[rr] >= EMB]
        if not len(sc) or np.isnan(a[sc]).all(): continue
        miss = int(np.isnan(a[sc]).sum()); big = int(np.nansum(np.abs(a[sc] - m[sc]) > 0.05))
        ok = miss == 0 and big == 0
        gap = float(252 * np.mean(np.log1p(a[sc]) - np.log1p(m[sc]))) if ok else None
        out.append(dict(b=b, years=years_of(b), n=int(len(sc)), rows_without_fund=miss, rows_gap_over_5pp=big, gap_actual_minus_model=gap))
    return out


# ------------------------------------------------------------------------------------------------ configurations, batches, gates
_BAN_NAME = {'open', 'exec', 'eval', 'compile', 'getattr', 'setattr', 'delattr', 'hasattr', 'globals', 'locals', 'vars', 'dir', 'input',
             'breakpoint', 'memoryview', 'id', 'type', 'object', 'super', 'print', 'help', 'exit', 'quit', 'classmethod', 'staticmethod', 'property'}
_BAN_ATTR = {'sys', 'os', 'modules', 'setflags', 'flags', 'ctypes', 'tofile', 'dump', 'dumps', 'save', 'savez', 'savez_compressed', 'savetxt',
             'load', 'loadtxt', 'fromfile', 'genfromtxt', 'memmap', 'random', 'base', 'data', 'ii', 'keep', 'account', 'lib', 'testing', 'f2py',
             # v6: string formatting walks attributes inside a string; frames, generators, coroutines and tracebacks reach globals
             'format', 'format_map', 'vformat', 'gi_frame', 'gi_code', 'gi_yieldfrom', 'gi_suspended', 'cr_frame', 'cr_code', 'cr_await',
             'cr_origin', 'ag_frame', 'ag_code', 'ag_await', 'f_globals', 'f_locals', 'f_back', 'f_builtins', 'f_code', 'f_trace',
             'tb_frame', 'tb_next', 'co_consts', 'co_code', 'co_names', 'func_globals', 'mro', 'seterr', 'seterrcall', 'geterrcall'}
_NP_OK = {   # the numpy attributes candidate code may use (one level: np.X, never np.X.Y)
    'abs', 'absolute', 'all', 'any', 'append', 'arange', 'argmax', 'argmin', 'argsort', 'array', 'array_equal', 'asarray',
    'ascontiguousarray', 'bincount', 'bool_', 'c_', 'ceil', 'clip', 'column_stack', 'concatenate', 'convolve', 'copy', 'cos',
    'cumprod', 'cumsum', 'diff', 'errstate', 'exp', 'expm1', 'float32', 'float64', 'floor', 'fmax', 'fmin', 'full',
    'full_like', 'hstack', 'inf', 'int32', 'int64', 'interp', 'isfinite', 'isin', 'isnan', 'log', 'log10', 'log1p', 'log2',
    'logical_and', 'logical_not', 'logical_or', 'max', 'maximum', 'mean', 'median', 'min', 'minimum', 'nan', 'nan_to_num',
    'nanmax', 'nanmean', 'nanmedian', 'nanmin', 'nanstd', 'nansum', 'newaxis', 'nonzero', 'ones', 'ones_like', 'pi', 'power',
    'prod', 'r_', 'ravel', 'repeat', 'reshape', 'roll', 'round', 'searchsorted', 'sign', 'sin', 'sort', 'sqrt', 'square',
    'stack', 'std', 'sum', 'tanh', 'tile', 'unique', 'var', 'vstack', 'where', 'zeros', 'zeros_like'}
_ERRSTATE_KW = {'divide', 'invalid', 'over', 'under', 'all'}


_BI_OK = ('ArithmeticError', 'Exception', 'FloatingPointError', 'IndexError', 'KeyError', 'StopIteration', 'ValueError',
          'ZeroDivisionError', 'abs', 'all', 'any', 'bool', 'dict', 'divmod', 'enumerate', 'filter', 'float', 'frozenset', 'int',
          'isinstance', 'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'pow', 'range', 'reversed', 'round', 'set', 'slice',
          'sorted', 'str', 'sum', 'tuple', 'zip')   # v6: the only built-ins candidate code gets (no open, hash, id, print, exit, import machinery)
_STD_MODS = set(sys.stdlib_module_names) | set(sys.builtin_module_names)
_YEAR = re.compile(r'(19|20)\d\d')
LIT_INT_MAX = 999                       # v6: an integer literal above this is refused (row numbers and years are not written into a rule)
LIT_SEQ_MAX = 64                        # v6: a list / tuple / set / dict display with more elements is refused (no data tables in code)


def _read_src(path):
    """v6: the bytes of a candidate file and of every file of its own folder it imports, directly or through another of them.
    Read once per configuration object: the gate, the hash and the executed code all come from these bytes (no import
    system, no sys.path, no __pycache__, no package folder is involved)."""
    d = os.path.dirname(path); main = os.path.splitext(os.path.basename(path))[0]; src = {}; todo = [(main, path)]
    while todo:
        nm, f = todo.pop()
        if nm in src: continue
        with open(f, 'rb') as fh: src[nm] = fh.read()
        try: tree = ast.parse(src[nm])
        except SyntaxError: continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    q = os.path.join(d, a.name + '.py')
                    if a.name not in ('numpy', 'xv1') and '.' not in a.name and a.name not in src and os.path.isfile(q): todo.append((a.name, q))
    return main, src


def _docstrings(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
            out.add(id(n.body[0].value))
    return out


def gate(path):
    """Source gate of a candidate file and of the helper files it imports. Returns the list of violations (empty = clean)."""
    main, src = _read_src(path); return _gate_src(main, src)


def _gate_src(main, src):
    """v6 allow-list. Allowed: module-level `import numpy`, `import xv1` and `import <helper>` (a file of the candidate's own
    folder whose name is not a standard-library or built-in module name); of xv1 only xv1.ref and xv1.std.ident; of numpy
    only the attributes in _NP_OK, one level deep (np.X); of a helper file only its own functions and names, one level
    deep; of the built-ins only _BI_OK. Not allowed: any other import, a from-import, an import inside a function, a
    module name used as a value, a class definition, a name or attribute that begins with '_' (other than the file's own
    module-level names) or contains '__', the attributes in _BAN_ATTR, assigning to or deleting any attribute, np.errstate
    with an argument other than divide / invalid / over / under / all, `global` / `nonlocal`, an integer literal above
    LIT_INT_MAX, a string literal (other than a docstring) that contains a year 19xx / 20xx, and a list / tuple / set /
    dict display with more than LIT_SEQ_MAX elements."""
    out = []; trees = {}
    for nm, b in sorted(src.items()):
        try: trees[nm] = ast.parse(b)
        except SyntaxError as e: out.append('%s.py:%s syntax error' % (nm, e.lineno))
    for nm, tree in sorted(trees.items()):
        tag = nm + '.py'; doc = _docstrings(tree)
        own = set(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
        own |= set(t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name))
        bound = set(n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
        bound |= set(a.arg for n in ast.walk(tree) if isinstance(n, ast.arguments) for a in n.args + n.kwonlyargs + n.posonlyargs)
        bound |= set(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        par = {}
        for n in ast.walk(tree):
            for ch in ast.iter_child_nodes(n): par[ch] = n
        alias = {}; helper = {}
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                if par.get(n) is not tree: out.append('%s:%d import inside a function' % (tag, n.lineno)); continue
                if isinstance(n, ast.ImportFrom): out.append('%s:%d from-import' % (tag, n.lineno)); continue
                for a in n.names:
                    isf = a.name not in ('numpy', 'xv1') and a.name in src and a.name != nm
                    if not (a.name in ('numpy', 'xv1') or isf): out.append('%s:%d import of %s' % (tag, n.lineno, a.name))
                    if isf and (a.name in _STD_MODS or not re.fullmatch(r'[a-z][a-z0-9_]*', a.name)): out.append('%s:%d helper name %s is a standard module name or not plain' % (tag, n.lineno, a.name))
                    alias[a.asname or a.name] = a.name
                    if isf and a.name in trees: helper[a.asname or a.name] = set(x.asname or x.name for y in ast.walk(trees[a.name]) if isinstance(y, ast.Import) for x in y.names)
            elif isinstance(n, (ast.Global, ast.Nonlocal)): out.append('%s:%d global / nonlocal' % (tag, n.lineno))
            elif isinstance(n, ast.ClassDef): out.append('%s:%d class definition' % (tag, n.lineno))
        for n in ast.walk(tree):
            if isinstance(n, ast.Name):
                if n.id in _BAN_NAME: out.append('%s:%d name %s' % (tag, n.lineno, n.id))
                if '__' in n.id: out.append('%s:%d name %s' % (tag, n.lineno, n.id))
                if n.id.startswith('_') and n.id not in own and not isinstance(n.ctx, ast.Store): out.append('%s:%d name %s' % (tag, n.lineno, n.id))
                if hasattr(builtins, n.id) and n.id not in _BI_OK and n.id not in bound and n.id not in alias: out.append('%s:%d built-in %s is not allowed' % (tag, n.lineno, n.id))
                if n.id in alias:
                    a1 = par.get(n)
                    if not (isinstance(a1, ast.Attribute) and a1.value is n): out.append('%s:%d module %s used as a value' % (tag, n.lineno, n.id)); continue
                    a2 = par.get(a1)
                    if alias[n.id] == 'xv1':
                        ok = a1.attr == 'ref' or (a1.attr == 'std' and isinstance(a2, ast.Attribute) and a2.attr == 'ident')
                        if not ok: out.append('%s:%d xv1 used for something other than xv1.ref / xv1.std.ident' % (tag, n.lineno))
                        if a1.attr == 'ref' and isinstance(a2, ast.Attribute) and a2.value is a1: out.append('%s:%d attribute of xv1.ref' % (tag, n.lineno))
                        if a1.attr == 'std' and isinstance(par.get(a2), ast.Attribute) and par.get(a2).value is a2: out.append('%s:%d attribute of xv1.std.ident' % (tag, n.lineno))
                    else:
                        if isinstance(a2, ast.Attribute) and a2.value is a1: out.append('%s:%d chained attribute %s.%s.%s' % (tag, n.lineno, n.id, a1.attr, a2.attr))
                        if alias[n.id] == 'numpy' and a1.attr not in _NP_OK: out.append('%s:%d numpy attribute %s is not on the allow-list' % (tag, n.lineno, a1.attr))
                        if n.id in helper and (a1.attr in helper[n.id] or a1.attr in ('np', 'numpy', 'xv1')): out.append('%s:%d module of a helper reached: %s.%s' % (tag, n.lineno, n.id, a1.attr))
            elif isinstance(n, ast.Attribute):
                if n.attr.startswith('_') or '__' in n.attr or n.attr in _BAN_ATTR: out.append('%s:%d attribute %s' % (tag, n.lineno, n.attr))
                if isinstance(n.ctx, (ast.Store, ast.Del)): out.append('%s:%d assignment to an attribute (%s)' % (tag, n.lineno, n.attr))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'errstate':
                if n.args or any(k.arg not in _ERRSTATE_KW for k in n.keywords): out.append('%s:%d np.errstate with an argument other than %s' % (tag, n.lineno, sorted(_ERRSTATE_KW)))
            elif isinstance(n, ast.Constant):
                if type(n.value) is int and abs(n.value) > LIT_INT_MAX: out.append('%s:%d integer literal above %d' % (tag, n.lineno, LIT_INT_MAX))
                if type(n.value) in (str, bytes) and id(n) not in doc and _YEAR.search(n.value if type(n.value) is str else n.value.decode('latin-1')): out.append('%s:%d string literal with a year' % (tag, n.lineno))
            elif isinstance(n, (ast.List, ast.Tuple, ast.Set)) and len(n.elts) > LIT_SEQ_MAX: out.append('%s:%d display of more than %d elements' % (tag, n.lineno, LIT_SEQ_MAX))
            elif isinstance(n, ast.Dict) and len(n.keys) > LIT_SEQ_MAX: out.append('%s:%d display of more than %d elements' % (tag, n.lineno, LIT_SEQ_MAX))
    return out


def _param_bad(x, path='params'):
    """v6: the literal rules of the gate applied to a configuration's parameter values"""
    if isinstance(x, bool) or x is None or isinstance(x, float): return []
    if isinstance(x, int): return ['%s: integer above %d' % (path, LIT_INT_MAX)] if abs(x) > LIT_INT_MAX else []
    if isinstance(x, str): return ['%s: string with a year' % path] if _YEAR.search(x) else []
    if isinstance(x, (list, tuple)):
        out = ['%s: more than %d elements' % (path, LIT_SEQ_MAX)] if len(x) > LIT_SEQ_MAX else []
        for i, y in enumerate(x): out += _param_bad(y, '%s[%d]' % (path, i))
        return out
    if isinstance(x, dict):
        out = ['%s: more than %d elements' % (path, LIT_SEQ_MAX)] if len(x) > LIT_SEQ_MAX else []
        for k, y in x.items(): out += _param_bad(k, path + ' key') + _param_bad(y, '%s[%r]' % (path, k))
        return out
    return ['%s: value of type %s' % (path, type(x).__name__)]


def _facade():
    """what `import xv1` gives candidate code: v1 itself and the no-brake function, nothing of the evaluator"""
    m = types.ModuleType('xv1'); m.ref = ref; m.std = types.SimpleNamespace(ident=std.ident); return m


class Config:
    """one configuration = candidate source file + function + parameter values + registered inputs + T0"""
    def __init__(s, family, name, file, func, params=None, names=(), t0=None, **_):
        s.family, s.name, s.file, s.func = family, name, os.path.realpath(file), func
        s.params = dict(params or {}); s.names = tuple(names); s.t0 = t0

    def _src(s):
        if getattr(s, '_s', None) is None: s._s = _read_src(s.file)
        return s._s

    @property
    def hash(s):
        """v6: sha256 of the names and sha256 of the candidate file and of every helper file it imports (the very bytes that
        are gated and executed), and of the configuration (computed once per object; load_batch builds new objects and
        compares them with the registered values)"""
        if getattr(s, '_h', None) is None:
            main, src = s._src()
            body = json.dumps(dict(main=main, files=[[k, hashlib.sha256(b).hexdigest()] for k, b in sorted(src.items())],
                                   func=s.func, params=s.params, names=list(s.names), t0=s.t0), sort_keys=True)
            s._h = hashlib.sha256(body.encode()).hexdigest()
        return s._h

    def _code(s):
        if getattr(s, '_co', None) is None:
            main, src = s._src(); bad = _gate_src(main, src)
            if bad: raise Void('source gate: ' + bad[0])
            try: s._co = {k: compile(b, '<candidate %s>' % k, 'exec', dont_inherit=True) for k, b in src.items()}
            except Exception as e: raise Void('error while loading candidate code: ' + type(e).__name__)
        return s._co

    def _load(s):
        """v6: a newly executed copy of the candidate module and of its helper modules, run from the gated and hashed bytes,
        with only the built-ins in _BI_OK and an import function that serves numpy, the stand-in for xv1 and the helper
        modules of this load. Nothing of an earlier copy is shared; sys.modules and sys.path are not touched."""
        main, _ = s._src(); co = s._code(); mods = {}; fac = _facade(); bi = {k: getattr(builtins, k) for k in _BI_OK}
        def imp(name, glb=None, loc=None, fromlist=(), level=0):
            if level or '.' in name: raise ImportError('import of ' + name)
            if name == 'numpy': return np
            if name == 'xv1': return fac
            if name in mods: return mods[name]
            if name not in co or name == main: raise ImportError('import of ' + name)
            return run(name)
        bi['__import__'] = imp
        def run(name):
            m = types.ModuleType(name); m.__dict__['__builtins__'] = bi; mods[name] = m; exec(co[name], m.__dict__); return m
        try:
            with _sandbox(): return run(main)
        except KeyboardInterrupt: raise
        except BaseException as e: raise Void('error while loading candidate code: ' + type(e).__name__)

    def make(s, v):
        """the candidate's output on view v, from a newly executed copy of its module (no state from earlier calls)"""
        return getattr(s._load(), s.func)(v, **s.params)

    def fresh(s):
        """the candidate as a function of the view (every call executes a new copy of its module)"""
        return s.make


    def to_dict(s):
        return dict(family=s.family, name=s.name, file=s.file, func=s.func, params=s.params, names=list(s.names), t0=s.t0, hash=s.hash)


def register_batch(configs):
    """write the next batch file and its ledger line. Must happen before any configuration of the batch is scored. The batch
    number is the next one in the ledger (it sets the level 0.05 / 2^k and cannot be chosen); a configuration that was scored
    before, a source that fails the gate and a level input off the allow-list are refused. Returns (k, sha256)."""
    _guard(); _check_env(); _writable(); L = read_ledger(); os.makedirs(OUT, exist_ok=True)
    k = 1 + sum(1 for e in L if e.get('kind') == 'batch'); path = OUT + 'BATCH_%d.json' % k
    if os.path.exists(path): raise FileExistsError(path)
    hs = [c.hash for c in configs]
    if len(set(hs)) != len(hs) or len(set(c.name for c in configs)) != len(configs): raise ValueError('duplicate configuration')
    if set(hs) & set(e.get('cfg') for e in L if e.get('kind') == 'score'): raise PermissionError('a configuration of this batch was scored before')
    fam = {}                                             # one source function = one family, over all batches (labels may only merge functions)
    for j in range(1, k):
        for d in json.load(open(OUT + 'BATCH_%d.json' % j)):
            if d['hash'] in hs: raise PermissionError('a configuration of this batch is in batch %d' % j)
            fam[(os.path.realpath(d['file']), d['func'])] = d['family']
    for c in configs:
        if fam.setdefault((c.file, c.func), c.family) != c.family: raise PermissionError('one source function under two family labels: %s' % c.name)
    if WORLD is None and not _checks_passed(): raise PermissionError('the data and parity checks have not passed under the registered hashes')
    for c in configs:
        bad = _gate_src(*c._src()) + _param_bad(c.params)                     # v6: the very bytes that are hashed and executed
        if bad: raise PermissionError('source gate, %s: %s' % (c.name, '; '.join(bad[:5])))
        if any(n.startswith('lvl:') and n not in LVL_OK for n in c.names): raise PermissionError('level input off the allow-list: %s' % c.name)
    body = json.dumps([c.to_dict() for c in configs], indent=1, sort_keys=True)
    with open(path, 'w') as f: f.write(body)
    sha = hashlib.sha256(body.encode()).hexdigest()
    ledger(dict(kind='batch', batch=k, sha256=sha, n=len(configs)))
    return k, sha


def load_batch(k):
    """the configurations of registered batch k, its sha256 and its ledger line"""
    body = open(OUT + 'BATCH_%d.json' % k).read(); sha = hashlib.sha256(body.encode()).hexdigest()
    line = [e for e in read_ledger() if e.get('kind') == 'batch' and e.get('batch') == k and e.get('sha256') == sha]
    if len(line) != 1: raise PermissionError('batch %d is not registered with this content' % k)
    cfgs = [Config(**d) for d in json.loads(body)]
    for c, d in zip(cfgs, json.loads(body)):
        if c.hash != d['hash']: raise PermissionError('configuration %s changed after registration' % d['name'])
    return cfgs, sha, line[0]


def _paired(cand, refb, blocks, t0=None):
    ds = []
    for b in blocks:
        d = cand[b]['x'] - refb[b]['x']
        if t0 is not None: d = d[cand[b]['date'] >= pd.Timestamp(t0)]
        ds.append(d)
    return ds


def _neutral(cand, refb, blocks, t0=None, info=None):
    """d*: daily differences against the static-equivalent benchmark of the set, on the scored rows on or after T0. The
    benchmark holds, constantly: kappa times the reference account, delta0 of the 3x fund, and w_j of each extra instrument
    (on the rows where the instrument exists); the rest is cash that earns nothing.
      kappa, delta0 = least-squares line of the candidate's actual 3x-fund weight on the reference's (a_cand = kappa a_ref + delta0;
                      kappa = 1 if the reference's weight does not vary), so a candidate that scales v1, adds a constant
                      amount of the fund or dilutes v1 with a sleeve is matched without v1's own timing being counted;
      w_j           = mean actual weight of extra j over the rows on which it exists.
      m_t = ln(1 + kappa (exp(x_REF,t) - 1) + delta0 R3_t + sum_j w_j G_j,t);   d*_t = x_cand,t - m_t.
    A candidate that only holds more, less or other things on average has d* near 0; d* keeps what comes from WHEN it holds."""
    sel = {}
    for b in blocks:
        sel[b] = np.ones(len(cand[b]['x']), dtype=bool) if t0 is None else np.asarray(cand[b]['date'] >= pd.Timestamp(t0))
    n = sum(int(sel[b].sum()) for b in blocks)
    if n == 0: return [np.zeros(0) for b in blocks]
    ac = np.concatenate([cand[b]['a0'][sel[b]] for b in blocks]); ar = np.concatenate([refb[b]['a0'][sel[b]] for b in blocks])
    va = float(np.mean((ar - ar.mean()) ** 2))
    kap = float(np.mean((ac - ac.mean()) * (ar - ar.mean())) / va) if va > 1e-12 else 1.0
    d0 = float(ac.mean() - kap * ar.mean())
    ex = sum(cand[b]['gok'][sel[b]].sum(axis=0) for b in blocks)
    wj = sum(cand[b]['aw'][sel[b]].sum(axis=0) for b in blocks) / np.maximum(ex, 1)
    if info is not None: info.update(kappa=kap, delta0=d0, w=[float(x) for x in np.atleast_1d(wj)])
    out = []
    for b in blocks:
        k = sel[b]; c = d0 * cand[b]['r3'][k] + cand[b]['g'][k] @ wj
        out.append(cand[b]['x'][k] - np.log(np.maximum(1.0 + kap * np.expm1(refb[b]['x'][k]) + c, 1e-12)))
    return out


def _active_rows(cand, refb, blocks, t0=None):
    """active rows per block (boolean arrays): scored rows on or after T0 on which the candidate holds a different level
    than the reference or holds extra instruments with a total actual weight of at least W_ACT (a non-zero paired
    difference alone does not count: after the first divergence the two accounts differ slightly on every row; nor does a
    sleeve below W_ACT)"""
    out = []
    for b in blocks:
        a = (cand[b]['lev'] != refb[b]['lev']) | (cand[b]['w'] >= W_ACT) | (refb[b]['w'] >= W_ACT)
        out.append(a if t0 is None else a[cand[b]['date'] >= pd.Timestamp(t0)])
    return out


def _active(cand, refb, blocks, t0=None): return [int(np.sum(a)) for a in _active_rows(cand, refb, blocks, t0)]


def _harm(d, active, k):
    """harm bound of one block: active block (>= 20 active rows) with d_b < -k x TE_b x sqrt(252 / n_b), TE_b from the block's own rows"""
    if active < ACTIVE_MIN or len(d) < 2: return False, 0.0
    lim = -k * te_of([d]) * np.sqrt(252.0 / len(d))
    return bool(ann([d]) < lim), float(lim)


def _gate_stats(ds, act, blocks, harm_k=2.0):
    n = int(sum(len(d) for d in ds)); rows = []; harm = False
    for b, d, a in zip(blocks, ds, act):
        if not len(d): continue
        h, lim = _harm(d, a, harm_k); harm |= h
        rows.append(dict(b=b, n=int(len(d)), active=a, d=ann([d]), te=te_of([d]), harm_limit=lim, harm=h))
    return dict(n=n, d=ann(ds), te=te_of(ds), t63=test_t(ds, 63)[0], p=p_t(ds), active_days=int(sum(act)),
                active_blocks=int(sum(a >= ACTIVE_MIN for a in act)), harm=harm, blocks=rows)


def _corr(a, b):
    """|correlation| of two vectors of design sub-block means (0 when one of them is constant)"""
    if np.std(a) == 0 or np.std(b) == 0: return 0.0
    return abs(float(np.corrcoef(a, b)[0, 1]))


def _sub_of(h):
    """design sub-block means of a scored configuration, from the batch result files"""
    k = 1
    while os.path.exists(OUT + 'results/batch_%d.json' % k):
        sm = json.load(open(OUT + 'results/batch_%d.json' % k))['sub_means']
        if h in sm: return np.asarray(sm[h])
        k += 1
    raise PermissionError('no design sub-block means for this configuration')


def _pre_t0(C, R, t0):
    """before T0 the candidate must equal the reference exactly (account rows of the blocks given)"""
    if t0 is None: return 0
    return sum(int(np.sum((C[b]['x'] - R[b]['x'])[C[b]['date'] < pd.Timestamp(t0)] != 0)) for b in C)


def _pre_t0_sig(pre, t0):
    """the same rule on the signal, on every account row of the view before T0 (sealed rows included): the base level is
    v1's, no weight, no rebalance flag. Returns the number of rows that break it."""
    if t0 is None: return 0
    X, v, m = pre['X'], pre['v'], pre['m']; e = _eng(v)
    k = int(X.index.searchsorted(pd.Timestamp(t0))) - (len(X) - e.T)
    if k <= WARM: return 0
    rB = _refm(e.c, e.T)['B']
    return int(np.sum((m['B'][WARM:k] != rB[WARM:k]) | (m['Wt'][WARM:k] != 0).any(axis=1) | (m['RB'][WARM:k] != 0).any(axis=1)))


def _span(cand, refb, blocks, t0=None):
    """scored rows of the set from the first active row on (0 if the configuration is never active)"""
    a = _active_rows(cand, refb, blocks, t0); a = np.concatenate(a) if a else np.zeros(0, dtype=bool)
    return int(len(a) - np.argmax(a)) if a.any() else 0


def _t0_ok(pre, t0):
    """a registered T0 may not lie more than T0_WARM_MAX calendar rows after the first row on which every registered input
    and the chain's own late-starting input (VIX) exist: the start of the record cannot be picked"""
    if t0 is None: return True
    X, v = pre['X'], pre['v']; e = _eng(v)
    arrs = list(e.x.values()) + [np.asarray(e.c.vix, dtype=np.float64).reshape(-1)]
    first = max(int(np.argmax(~np.isnan(a))) if (~np.isnan(a)).any() else e.T for a in arrs)
    return int(X.index.searchsorted(pd.Timestamp(t0))) - (len(X) - e.T) <= first + T0_WARM_MAX


def _g1_of(h, L=None):
    """the G1 record of a configuration, read from the results file of its batch; the file must be the one whose sha256 the
    ledger holds (a ledger line written by hand has no such file behind it)"""
    L = read_ledger() if L is None else L
    ks = [e['batch'] for e in L if e.get('kind') == 'g1' and e.get('cfg') == h]
    if not ks: raise PermissionError('no G1 record for this configuration')
    body = open(OUT + 'results/batch_%d.json' % ks[-1], 'rb').read(); sha = hashlib.sha256(body).hexdigest()
    if not any(e.get('kind') == 'batch-done' and e.get('batch') == ks[-1] and e.get('sha256') == sha for e in L):
        raise PermissionError('the results file of batch %d is not the one in the ledger' % ks[-1])
    o = json.loads(body)['results'].get(h)
    if o is None: raise PermissionError('no G1 record for this configuration')
    return o


def _shape(sub):
    """skewness and lag-1 autocorrelation of sub-block means (reported with every G1 line: the stated error rates assume
    sub-block sums that are symmetric around 0 and independent under the null)"""
    x = np.asarray(sub, dtype=float); x = x - x.mean(); sd = float(x.std())
    if sd <= 0 or len(x) < 3: return 0.0, 0.0
    return float(np.mean(x ** 3) / sd ** 3), float(np.sum(x[1:] * x[:-1]) / np.sum(x * x))


def _design(c, stress=True, pre=None):
    """G1 material of one configuration on D7 (scalars) and its L = 63 sub-block means of d and of d* (design material).
    The candidate's output is the one of `pre` in every run: its signals are held fixed under the stress terms."""
    pre = pre or _prepare(c.make, c.names)
    C = _design_account(pre=pre); R = _ref_blocks()
    if not _t0_ok(pre, c.t0): raise Void('T0 later than its inputs plus %d rows' % T0_WARM_MAX)
    if _pre_t0(C, R, c.t0) or _pre_t0_sig(pre, c.t0): raise Void('differs from the reference before T0')
    ds = _paired(C, R, DESIGN, c.t0); o = _gate_stats(ds, _active(C, R, DESIGN, c.t0), DESIGN)
    o['n_span'] = _span(C, R, DESIGN, c.t0)
    plain = not c.names and not (pre['m']['Wt'] != 0).any() and not _eng(pre['v']).touched
    o['g0'] = 'required' if plain else 'not available'   # the simulation screen exists only for a rule on the index chain alone
    inf = {}; dn = _neutral(C, R, DESIGN, c.t0, inf); o['d_star'] = ann(dn); o['t63_star'] = test_t(dn, 63)[0]; o['benchmark'] = inf
    on = {b: (np.ones(len(C[b]['x']), dtype=bool) if c.t0 is None else np.asarray(C[b]['date'] >= pd.Timestamp(c.t0))) for b in DESIGN}
    cat = lambda f: np.concatenate([f(b)[on[b]] for b in DESIGN])                    # rows on or after T0
    o['cand'] = ann([C[b]['x'][on[b]] for b in DESIGN]); o['ref'] = ann([R[b]['x'][on[b]] for b in DESIGN])
    o['extra_weight_mean'] = float(np.mean(cat(lambda b: C[b]['w']))) if sum(on[b].sum() for b in DESIGN) else 0.0
    o['level_mean'] = float(np.mean(cat(lambda b: C[b]['lev']))) if sum(on[b].sum() for b in DESIGN) else 0.0
    o['fund_weight_mean_minus_ref'] = float(np.mean(cat(lambda b: C[b]['a0'] - R[b]['a0']))) if sum(on[b].sum() for b in DESIGN) else 0.0
    if stress:
        for sname in G1_STRESS:
            Cs = _design_account(pre=pre, **STRESS[sname]); o['d_' + sname] = ann(_paired(Cs, _ref_blocks(sname), DESIGN, c.t0))
    full = lambda dd: np.concatenate([np.r_[np.zeros(len(C[b]['x']) - len(d)), d] for b, d in zip(DESIGN, dd)])   # rows before T0 count as 0
    cut = np.cumsum([len(C[b]['x']) for b in DESIGN])[:-1]
    sub = np.concatenate([sub_means(d, 63) for d in np.split(full(ds), cut)])
    subn = np.concatenate([sub_means(d, 63) for d in np.split(full(dn), cut)])
    o['skew63'], o['ac1_63'] = _shape(sub)
    return o, sub, subn


def _advanced_before(k, L):
    """(family label, design sub-block means) of every configuration that advanced at G1 in a batch before k"""
    return [(e.get('family'), _sub_of(e['cfg'])) for e in L if e.get('kind') == 'g1' and e.get('advance') and e.get('batch', 0) < k]


@_scoped
def run_batch(k, stress=True):
    """Score every configuration of registered batch k on D7 and apply G1. Scalars only (plus the design sub-block means).
    A configuration that breaks a rule (source gate, raw-level, prefix or level-scale test, output rules, an error in its own
    code) is void: it is not scored and the batch level is not refunded. A batch is scored once; a run that was interrupted
    before its results file was written is resumed (finished configurations are kept in results/partial_k/)."""
    _guard(); _check_env(); _writable(); cfgs, sha, line = load_batch(k); L = read_ledger(); done = OUT + 'results/batch_%d.json' % k
    if os.path.exists(done):
        if any(e.get('kind') == 'batch-done' and e.get('batch') == k for e in L): raise PermissionError('batch %d is already scored: read %s' % (k, done))
        os.remove(done)                                  # interrupted between the results file and its ledger line: rebuilt from the partial files
    alpha = 0.05 / 2 ** k; seed = int(hashlib.sha256((sha + json.dumps(line, sort_keys=True)).encode()).hexdigest()[:8], 16)
    part = OUT + 'results/partial_%d/' % k; os.makedirs(part, exist_ok=True); env = _env_tag()
    raw = raw_extras_test([n for c in cfgs for n in c.names], seed=seed); res = {}; subs = {}; subn = {}
    for c in cfgs:
        h = c.hash; cp = part + h + '.json'
        if not any(e.get('kind') == 'score' and e.get('cfg') == h and e.get('batch') == k for e in L): ledger(dict(kind='score', cfg=h, set='design', batch=k))
        got = json.load(open(cp)) if os.path.exists(cp) else None
        if got is None or got.get('env') != env:
            try:
                if any(n in raw['failed'] for n in c.names): raise Void('raw-level test of an extra input')
                pre = _prepare(c.fresh(), c.names)                   # the one full-calendar call (newly executed module): tested below, then scored
                if prefix_test(None, c.names, n_rand=60, seed=seed, fresh=c.fresh, pre=pre)['result'] != 'PASS': raise Void('prefix test')
                if scale_test(c.fresh(), c.names, pre=pre) != 'PASS': raise Void('level-scale test')
                o, sub, sn = _design(c, stress, pre)
                got = dict(env=env, o=o, sub=[float(x) for x in sub], subn=[float(x) for x in sn])
            except Void as e: got = dict(env=env, o=dict(void=str(e) if WORLD is not None else str(e).split(':')[0]), sub=None, subn=None)   # v6: real calendar = the category only
            json.dump(got, open(cp, 'w'))
        res[h] = got['o']; res[h].update(family=c.family, name=c.name, calendar=bool(any(n.startswith('cal:') for n in c.names)))
        if got['sub'] is not None: subs[h] = np.asarray(got['sub']); subn[h] = np.asarray(got['subn'])
    live = list(subs)
    if live:
        t0, pf = max_t(np.stack([subs[h] for h in live], axis=1), DRAWS, seed)
        t1, pn = max_t(np.stack([subn[h] for h in live], axis=1), DRAWS, seed + 1)
        for h, a, b, a1, b1 in zip(live, t0, pf, t1, pn): res[h].update(t63_family=float(a), p_family=float(b), t63_star_family=float(a1), p_star_family=float(b1))
    for h in live:
        o = res[h]
        o['g1'] = dict(a=bool(o['d'] >= D_MIN_G1 and o['active_blocks'] >= 3 and min(o['n'], o['n_span']) >= 1500), b=bool(not o['harm']), c=bool(o['p_family'] <= alpha),
                       d=bool(all(o['d_' + sn] > 0 for sn in G1_STRESS)) if stress else None)
        o['g1_pass'] = all(v for v in o['g1'].values() if v is not None) and stress
        o['kind'] = 'timing' if (o['d_star'] > 0 and o['p_star_family'] <= alpha) else 'exposure'
    key = lambda h: (res[h]['kind'] != 'timing', res[h]['p_family'], -res[h]['t63_family'], h)
    prev = _advanced_before(k, L); adv = []          # at most one configuration per family goes on (timing kind first), over all batches
    for h in sorted([h for h in live if res[h]['g1_pass']], key=key):
        if all(res[g]['family'] != res[h]['family'] and _corr(subs[g], subs[h]) < FAM_CORR for g in adv) and \
           all(f != res[h]['family'] and _corr(sm, subs[h]) < FAM_CORR for f, sm in prev): adv.append(h)
    out = dict(batch=k, sha256=sha, alpha=alpha, n=len(cfgs), raw_extras_test=raw, results=res, sub_means={h: [float(x) for x in subs[h]] for h in live})
    for h in res: res[h]['advance'] = h in adv
    json.dump(out, open(done + '.tmp', 'w'), indent=1)
    have = set(e.get('cfg') for e in read_ledger() if e.get('kind') == 'g1' and e.get('batch') == k)
    for h in res:
        if h not in have:
            ledger(dict(kind='g1', cfg=h, batch=k, family=res[h]['family'], passed=bool(res[h].get('g1_pass', False)), advance=res[h]['advance'],
                        type=res[h].get('kind'), calendar=res[h]['calendar']))
    os.replace(done + '.tmp', done)                      # the results file appears only after every G1 line is in the ledger
    if not any(e.get('kind') == 'batch-done' and e.get('batch') == k for e in read_ledger()):
        ledger(dict(kind='batch-done', batch=k, sha256=_sha(done)))
    return out


def g0_line(c, passed, code_sha256):
    """ledger line of the simulation screen G0 (its function lives in its own reviewed file; this records the outcome)"""
    _guard(); _check_env(); h = c.hash; L = read_ledger(); o = _g1_of(h, L)
    if not (o.get('g1_pass') and o.get('advance')) or o.get('g0') != 'required': raise PermissionError('G0 is not due for this configuration')
    if any(e.get('kind') == 'g0' and e.get('cfg') == h for e in L): raise PermissionError('G0 already recorded')
    ledger(dict(kind='g0', cfg=h, passed=bool(passed), code=code_sha256))


def _g0_clear(h, o, L):
    """G0 is passed, or does not exist for this configuration"""
    return o.get('g0') == 'not available' or any(e.get('kind') == 'g0' and e.get('cfg') == h and e.get('passed') for e in L)


@_scoped
def weak_eval(c):
    """G2 (old-data no-harm check) on W5: only for a configuration that passed G1 and was selected (and G0 where it exists),
    and only once. With fewer than G2_MIN_ROWS scored WEAK rows on or after T0 the check does not exist: the line says so,
    nothing is read, and the configuration cannot be opened."""
    _guard(); _check_env(); h = c.hash; L = read_ledger(); g1 = _g1_of(h, L)
    if not (g1.get('g1_pass') and g1.get('advance')): raise PermissionError('no G1 pass for this configuration')
    if not _g0_clear(h, g1, L): raise PermissionError('G0 is required and not passed')
    if any(e.get('kind') in ('score', 'g2') and e.get('cfg') == h and e.get('set', 'weak') == 'weak' for e in L):
        raise PermissionError('weak blocks already read for this configuration')
    cal = Cal(acc_dates(frame())); ok = cal.scored & np.isin(cal.blk, WEAK)
    if c.t0 is not None: ok &= np.asarray(cal.dates >= pd.Timestamp(c.t0))
    if int(ok.sum()) < G2_MIN_ROWS:
        ledger(dict(kind='g2', cfg=h, passed=False, available=False)); return dict(g2_pass=False, available=False, n=int(ok.sum()))
    ledger(dict(kind='score', cfg=h, set='weak'))
    C = _design_account(c.fresh(), c.names); R = _ref_blocks()
    o = _gate_stats(_paired(C, R, WEAK, c.t0), _active(C, R, WEAK, c.t0), WEAK)
    o['set_limit'] = float(-1.0 * o['te'] * np.sqrt(252.0 / o['n'])) if o['n'] else 0.0
    o['g2_pass'] = bool(o['d'] >= o['set_limit'] and not o['harm'])        # no-harm check: the reference was chosen on these blocks
    ledger(dict(kind='g2', cfg=h, passed=o['g2_pass'], available=True))
    return o


def authorise_g3(c, owner_message_id):
    """record the owner's authorisation of a G3 opening (the id of the owner's own message, and where the ledger stood). Only
    for a configuration that passed G1 and was selected, passed G0 where it exists and passed G2."""
    _guard(); _check_env(); h = c.hash; L = read_ledger(); g1 = _g1_of(h, L)
    if not (isinstance(owner_message_id, str) and owner_message_id.startswith('cmsg_') and len(owner_message_id) > 10): raise PermissionError('not a message id')
    if not (g1.get('g1_pass') and g1.get('advance')): raise PermissionError('no G1 pass')
    if not _g0_clear(h, g1, L): raise PermissionError('G0 is required and not passed')
    if not any(e.get('kind') == 'g2' and e.get('cfg') == h and e.get('passed') for e in L): raise PermissionError('no G2 pass')
    ledger(dict(kind='owner-auth', cfg=h, message=owner_message_id, at=len(L)))


def close_g3(owner_message_id):
    """the owner closes G3 for good (no further opening); the release function then reports the opened configurations"""
    _guard(); _check_env()
    if not (isinstance(owner_message_id, str) and owner_message_id.startswith('cmsg_')): raise PermissionError('not a message id')
    ledger(dict(kind='G3-CLOSED', message=owner_message_id))


def _markers():
    p = OUT + 'G3_OPENINGS.log'
    return open(p).read().split() if os.path.exists(p) else []


@_scoped
def open_g3(c):
    """one G3 opening: blocks 10 and 12 from the main account (full calendar). Output: one word. One opening at a time: the
    lock file G3.lock is created first and removed at the end (after a crash it is removed by hand, and the retry rule applies)."""
    _guard(); _check_env(); _writable(); lock = OUT + 'G3.lock'
    try: os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError: raise PermissionError('another opening is in progress (G3.lock exists)')
    try: return _open_g3(c)
    finally: os.remove(lock)


def _input_free(c, t0):
    """True if the candidate's level, weights and flags from T0 on do not depend on any input: every input (index return,
    cash rate, macro levels, registered inputs and through them the v1 shadow levels) after T0 is replaced by noise on the
    calendar that ends 2015-12-31, and B, Wt and RB from T0 on stay bit-identical"""
    pre = _prepare(c.fresh(), c.names, A_END); X, E, m = pre['X'], pre['E'], pre['m']; i0 = len(X) - pre['v'].T
    r = i0 + WARM if t0 is None else max(i0 + WARM, int(X.index.searchsorted(pd.Timestamp(t0))))
    for sd in (1, 2):
        Xn, En = _noise(X, E, r, np.random.default_rng(sd)); mn = _call(c.fresh(), View(Xn, En)); q = r - i0 + 1
        if any(_same(mn[k][q:], m[k][q:]) for k in ('B', 'Wt', 'RB')): return False
    return True


def _g3_word(c, g1, prem, seed):
    """the verdict of one opening: one word, nothing else leaves"""
    Cs = _main_account(pre=prem); Rs = _main_account(ref, ())
    ds = _paired(Cs, Rs, SEALED, c.t0); rows = _active_rows(Cs, Rs, SEALED, c.t0); act = [int(np.sum(a)) for a in rows]; d = ann(ds)
    dn = _neutral(Cs, Rs, SEALED, c.t0)
    if d <= 0 or any(_harm(x, a, 1.0)[0] for x, a in zip(ds, act)): return 'FAIL'
    if d >= D_MIN_G3 and p_test(ds, seed, rows) <= 0.05 / 3:
        timing = g1.get('kind') == 'timing' and not g1.get('calendar') and not any(n.startswith('cal:') for n in c.names)
        return 'CONFIRMED' if (timing and ann(dn) > 0 and p_test(dn, seed + 1, rows) <= 0.05 / 3) else 'CONSISTENT'
    return 'INCONCLUSIVE'


def _open_g3(c):
    h = c.hash; L = read_ledger(); g1 = _g1_of(h, L)
    if time.strftime('%Y-%m-%d', time.gmtime()) >= G3_END: raise PermissionError('the G3 budget has ended (%s)' % G3_END)
    if any(e.get('kind') == 'G3-CLOSED' for e in L): raise PermissionError('G3 is closed for good')
    if not (g1.get('g1_pass') and g1.get('advance')): raise PermissionError('no G1 pass')
    if not _g0_clear(h, g1, L): raise PermissionError('G0 is required and not passed')
    g2 = [i for i, e in enumerate(L) if e.get('kind') == 'g2' and e.get('cfg') == h and e.get('passed')]
    if not g2: raise PermissionError('no G2 pass')
    if not any(e.get('kind') == 'owner-auth' and e.get('cfg') == h and i > g2[0] for i, e in enumerate(L)): raise PermissionError('no owner authorisation after the G2 pass')
    opened = [e['cfg'] for e in L if e.get('kind') == 'G3-OPEN']; mk = _markers()
    if len(mk) > len(opened) or mk != opened[:len(mk)]: raise PermissionError('the ledger shows fewer openings than the marker file')
    if any(e.get('kind') == 'G3-VERDICT' and e.get('cfg') == h for e in L): raise PermissionError('already opened')
    if h in opened:
        if opened.count(h) >= 2: raise PermissionError('retry already used')
    elif len(set(opened)) >= 3: raise PermissionError('the three openings are spent')
    pre = _prepare(c.fresh(), c.names)
    C = _design_account(pre=pre); R = _ref_blocks(); te = te_of(_paired(C, R, DESIGN, c.t0))
    ma = _prepare(c.fresh(), c.names, A_END)['m']
    fixed = float(np.std(np.concatenate([C[b]['lev'] for b in DESIGN]))) == 0 and float(np.ptp(ma['Wt'], axis=0).max()) == 0 and not ma['RB'].any()
    if te <= 0 or fixed or _input_free(c, c.t0): raise PermissionError('a configuration whose level does not depend on any input may not be opened')
    if h not in opened:
        fam = {e['cfg']: e.get('family') for e in L if e.get('kind') == 'g1'}; mine = _sub_of(h)
        for g in set(opened):
            if fam.get(g) == fam.get(h) or _corr(mine, _sub_of(g)) >= FAM_CORR: raise PermissionError('same family as an opened configuration')
    ledger(dict(kind='G3-OPEN', cfg=h, retry=h in opened))                       # v6: logged BEFORE the candidate first runs on the main view
    with open(OUT + 'G3_OPENINGS.log', 'a') as f: f.write(h + '\n'); f.flush(); os.fsync(f.fileno())
    word = None; prem = None; _G3_RUN[0] = h; _G3_PRE[0] = h; seed = int(h[:8], 16)
    try:
        prem = _prepare(c.fresh(), c.names, None, 'main')
        if _pre_t0_sig(prem, c.t0) or prefix_test(None, c.names, n_rand=60, seed=seed, fresh=c.fresh, account='main', pre=prem)['result'] != 'PASS':
            word = 'FAIL'                                # a check of the main view failed: the opening is used and the verdict is FAIL
        else: word = _g3_word(c, g1, prem, seed)
    except BaseException: word = None                    # nothing of the error (type, text, frames) is kept
    finally: _G3_RUN[0] = None; _G3_PRE[0] = None
    del prem
    if word is None:
        ledger(dict(kind='G3-ABORT', cfg=h))
        raise RuntimeError('G3 run stopped (the opening is used; the retry rule applies)')
    ledger(dict(kind='G3-VERDICT', cfg=h, verdict=word))
    return word


# ------------------------------------------------------------------------------------------------ causality test
def _noise(X, E, r, g):
    """copy of X and of the extra inputs with every row after position r replaced by noise"""
    Xn = X.copy(); n = len(X) - r - 1
    if n <= 0: return Xn, E
    Xn.iloc[r + 1:, Xn.columns.get_loc('r')] = np.clip(g.normal(0, 0.03, n), -0.5, 0.5)
    for c in ('rf', 'y10', 'y3m', 'cs', 'vix'):
        last = Xn[c].values[r]; last = 0.0 if np.isnan(last) else last
        w = last + np.cumsum(g.normal(0, 0.1 if c != 'rf' else 1e-5, n))
        Xn.iloc[r + 1:, Xn.columns.get_loc(c)] = np.round(w, 2) if _on_grid(X[c].values[:r + 1]) else w   # v6: the noise keeps the grid of the real series
    Xn['rb'] = mkt.bond10(Xn); Xn['p'] = (1 + Xn['r']).cumprod()
    En = {}
    for k, a in E.items():
        b = a.copy()
        if k.startswith('lvl:'):
            last = a[r] if np.isfinite(a[r]) else 0.0; w = last + np.cumsum(g.normal(0, 0.1, n))
            b[r + 1:] = np.round(w, 2) if _on_grid(a[:r + 1]) else w
        else: b[r + 1:] = g.normal(0, 0.05, n)
        En[k] = b
    return Xn, En


def _on_grid(a):
    """True if the last 252 known values of a series all lie on the 0.01 grid (a level quoted in hundredths)"""
    a = np.asarray(a, dtype=np.float64); a = a[np.isfinite(a)][-252:]
    return bool(len(a)) and bool(np.all(np.abs(a * 100 - np.round(a * 100)) < 1e-6))


def _same(a, b): return int(a.shape != b.shape) if a.shape != b.shape else int(np.sum(~((a == b) | (np.isnan(a) & np.isnan(b)))))


def prefix_test(make=None, names=(), end=None, n_rand=60, seed=0, noise=True, step=0, n_event=1000, fresh=None, account='design', pre=None):
    """A candidate may not read anything after the row it decides on. For each cut row the calendar is (a) cut after it and
    (b) kept but filled with noise after it; signal, weights, instrument returns, features and EVERY column of the account
    path on the rows up to the cut must be bit-identical to the full run (`pre`: the same full-calendar result that is scored).
    Cuts: the last row of every block, account rows 0, 62, 63 and 259 and n_rand drawn rows from the whole account (both
    variants), and, with deletion only, every `step`-th row and the event rows (the row itself and the row before): level
    events = rows on which the candidate's signal or v1's own signal changes and the first and last row of every run in which
    the candidate's level differs from v1's; weight events = rows on which a target weight or a rebalance flag of a column
    that is ever held changes (v6: columns never held do not make events). All event rows are cut up to n_event: the level
    events first, then the weight events; above n_event a uniform draw (level events first). With `fresh`, the cut runs use a newly executed
    copy of the candidate module and of its helpers. A candidate that raises on a cut fails that cut. PASS / FAIL and counts."""
    if account == 'main' and WORLD is None and _G3_PRE[0] is None: raise PermissionError('the main view is tested only by open_g3')
    pre = pre or _prepare(make, names, end, account); X, E, v, m = pre['X'], pre['E'], pre['v'], pre['m']; e = _eng(v)
    if e.account != account: raise PermissionError('view of the other account')
    rec = _run_eng(e, m); i0 = len(X) - e.T; cal = Cal(acc_dates(X)); g = np.random.default_rng(seed)
    ends = set([int(cal.rows(b)[-1]) for b in range(NB) if len(cal.rows(b))][:-1])
    drawn = set(int(q) for q in g.integers(0, cal.n - 1, n_rand)) | set(q for q in (0, 62, 63, 259) if q < cal.n - 1)
    rB = _refm(e.c, e.T)['B']; held = (m['Wt'] != 0).any(axis=0)                # v6: columns never held are never read by the engine
    lv = np.zeros(e.T, dtype=bool); lv[1:] = m['B'][1:] != m['B'][:-1]; lv[1:] |= rB[1:] != rB[:-1]
    dif = m['B'] != rB; turn = np.flatnonzero(dif[1:] != dif[:-1]) + 1; lv[turn] = True; lv[turn - 1] = True
    wt = np.zeros(e.T, dtype=bool)
    if held.any(): wt[1:] = (m['Wt'][1:, held] != m['Wt'][:-1, held]).any(axis=1) | (m['RB'][1:, held] != m['RB'][:-1, held]).any(axis=1)
    def rows_of(ev): q = np.flatnonzero(ev) - WARM; return q[(q >= 0) & (q < cal.n - 1)]
    qa = rows_of(lv); qb = np.setdiff1d(rows_of(wt), qa)                          # level events first, then weight / flag events
    if len(qa) >= n_event: evq = g.choice(qa, n_event, replace=False)
    else: evq = np.union1d(qa, qb if len(qa) + len(qb) <= n_event else g.choice(qb, n_event - len(qa), replace=False))
    events = set(int(q) for q in evq) | set(int(q) - 1 for q in evq if q >= 1)
    cuts = sorted(ends | drawn | events | (set(range(0, cal.n - 1, step)) if step else set()))
    cells = 0; bad = 0; ncut = 0; mk = fresh() if fresh is not None else make
    for q in cuts:
        r = i0 + WARM + q                                # calendar row of the cut
        variants = [(X.iloc[:r + 1], {k: a[:r + 1] for k, a in E.items()})]
        if noise and (q in ends or q in drawn): variants.append(_noise(X, E, r, g))
        for Xc, Ec in variants:
            vc = View(Xc, Ec, account); T = q + WARM + 1; ncut += 1
            try: mc = _call(mk, vc)
            except Void: bad += 1; cells += 1; continue
            n = _same(mc['B'][:T], m['B'][:T]) + _same(mc['Graw'][:T], m['Graw'][:T]) + _same(mc['Wt'][:T], m['Wt'][:T]) + \
                _same(mc['RB'][:T], m['RB'][:T]) + _same(mc['up'], m['up']) + _same(mc['dn'], m['dn']) + \
                _same(_eng(vc).feat[:T], e.feat[:T]) + _same(mc['bp'], m['bp']) + int(mc['fstep'] != m['fstep']) + \
                int(mc['mode'] != m['mode']) + int(mc['inc'] != m['inc']) + int(mc['bfn'] is not m['bfn'])
            rc = _run_eng(_eng(vc), mc, slice(0, T))
            n += _same(rc, rec[:q + 1])
            cells += n; bad += int(n > 0)
    if WORLD is None: return dict(result='PASS' if bad == 0 else 'FAIL')   # counts depend on sealed rows: only test worlds see them
    return dict(result='PASS' if bad == 0 else 'FAIL', cuts=ncut, failed_cuts=bad, differing_cells=int(cells))


def scale_test(make, names=(), end=None, pre=None):
    """Level-scale test: the index level handed to candidate code (view.c.lvl) is multiplied by 2 and by 0.5 (exact in
    binary arithmetic). Every output of the candidate and the features must stay bit-identical: a rule may use ratios of
    the level, never its absolute height (a threshold on the height would pick out an era without naming a date). It covers
    the index level only; other ways to read the calendar position (a row counter, a count on a calendar field, an own
    cumulative level compared with its first value) are excluded by reading the candidate source at review."""
    pre = pre or _prepare(make, names, end); X, E, v, m = pre['X'], pre['E'], pre['v'], pre['m']; bad = 0
    for f in (2.0, 0.5):
        vs = View(X, E); lv = vs.c.lvl * f; lv.setflags(write=False); vs.c.lvl = lv; vs.c._c.clear()
        try: ms = _call(make, vs)
        except Void: return 'FAIL'
        bad += sum(_same(ms[k], m[k]) for k in ('B', 'Graw', 'Wt', 'RB', 'up', 'dn', 'bp')) + _same(np.ascontiguousarray(bk.features(vs.c)[0]), _eng(v).feat)
        bad += int(ms['fstep'] != m['fstep']) + int(ms['mode'] != m['mode']) + int(ms['inc'] != m['inc'])
    return 'PASS' if bad == 0 else 'FAIL'


def _raw_index(name):
    """dates of the raw rows behind a registered input (None for a calendar field)"""
    if name == 'chips': return [xdata._c['chips'].index] if 'chips' in xdata._c else []
    if name == 'semis': return _raw_index('chips') + _raw_index('ret:SOXX')
    if ':' not in name: return []
    kind, rest = name.split(':', 1); key, _, tag = rest.partition('@')
    if kind == 'kf': return [xdata._c['kf'].index] if 'kf' in xdata._c else []
    if kind in ('ret', 'lvl'): return [xdata.px(key, 4 if kind == 'ret' else 3, xdata._file(tag)).index]
    return []


def raw_extras_test(names, end=None, n_rand=12, seed=0):
    """Raw-level causality of the registered extra inputs. The raw readers behind xdata are wrapped in memory; every raw row
    dated after a cut is (a) deleted and (b) replaced by noise, and (c) the input is rebuilt on the calendar cut at that row;
    the aligned arrays up to the cut must be bit-identical. Cuts: block ends, drawn rows, the rows around every start, end or
    gap of an input and around every calendar row inside a series' life that has no raw row (a carried-forward value).
    Returns PASS / FAIL per name and counts only."""
    names = tuple(sorted(set(names)))
    if not names: return dict(result='PASS', rebuilds=0, failed={}) if WORLD is not None else dict(result='PASS', failed=[])
    X = frame(end or CAL_END); idx = X.index; cal = Cal(acc_dates(X)); i0 = len(idx) - cal.n; g = np.random.default_rng(seed)
    xdata._c.clear(); base = extras(names, idx)
    cuts = set([int(cal.rows(b)[-1]) for b in range(NB) if len(cal.rows(b))][:-1]) | set(int(q) for q in g.integers(0, cal.n - 1, n_rand))
    tr = set()                                           # rows around every start, end, gap or carried value of an input (where a fill could reach back)
    for k in names:
        nn = np.isnan(base[k]); t = list(np.flatnonzero(nn[1:] != nn[:-1]) + 1 - i0)
        for ri in _raw_index(k):
            if len(ri): t += list(np.flatnonzero((idx >= ri[0]) & (idx <= ri[-1]) & ~idx.isin(ri)) - i0)
        for o in range(-xdata.CARRY - 1, xdata.CARRY + 2): tr |= set(int(q) + o for q in t)
    tr = sorted(q for q in tr if 0 <= q < cal.n - 1)
    if len(tr) > 600: tr = [int(q) for q in g.choice(tr, 600, replace=False)]
    cuts = sorted(cuts | set(tr))
    st = dict(cut=None, mode='del', g=None)
    def perturb(s):
        c = st['cut']
        if st['mode'] == 'del': return s[s.index <= c]
        s = s.copy(); k = np.asarray(s.index > c); n = int(k.sum())
        if n and isinstance(s, pd.DataFrame): s.iloc[k, :] = st['g'].normal(0, 0.05, (n, s.shape[1]))
        elif n: s[k] = np.abs(s[~k].iloc[-1] if (~k).any() else 1.0) * np.exp(np.cumsum(st['g'].normal(0, 0.05, n)))
        return s
    o_pser, o_chips, o_kf = mkt.pser, xdata.read_chips, xdata.md.kf; bad = {k: 0 for k in names}; runs = 0
    try:
        for q in cuts:
            n = i0 + q + 1
            xdata._c.clear(); got = extras(names, idx[:n]); runs += 1                  # (c) the calendar itself cut at the row
            for k in names: bad[k] += int(_same(got[k], base[k][:n]) > 0)
            mkt.pser = lambda k, col, f='panel_f32.npz.xz': perturb(o_pser(k, col, f)); xdata.read_chips = lambda: perturb(o_chips())
            xdata.md.kf = lambda: perturb(o_kf())
            for mode in ('del', 'noise'):
                st.update(cut=cal.dates[q], mode=mode, g=np.random.default_rng(q)); xdata._c.clear(); got = extras(names, idx); runs += 1
                for k in names: bad[k] += int(_same(got[k][:n], base[k][:n]) > 0)
            mkt.pser, xdata.read_chips, xdata.md.kf = o_pser, o_chips, o_kf
    finally:
        mkt.pser, xdata.read_chips, xdata.md.kf = o_pser, o_chips, o_kf; xdata._c.clear()
    failed = {k: v for k, v in bad.items() if v}
    if WORLD is None: return dict(result='PASS' if not failed else 'FAIL', failed=sorted(failed))   # names only: counts depend on sealed rows
    return dict(result='PASS' if not failed else 'FAIL', rebuilds=runs, failed=failed)


# ------------------------------------------------------------------------------------------------ ledger and hashes
def read_ledger():
    """the ledger, with its hash chain verified: every line names the hash of the file as it was before the line was added.
    An edited, shortened-and-continued or re-ordered ledger raises."""
    p = OUT + 'LEDGER.jsonl'
    if not os.path.exists(p): return []
    out = []; h = hashlib.sha256(); first = True
    for raw in open(p, 'rb').read().splitlines(keepends=True):
        e = json.loads(raw)
        if e.get('prev') != ('' if first else h.hexdigest()[:16]): raise PermissionError('the ledger hash chain is broken at line %d' % len(out))
        h.update(raw); first = False; out.append(e)
    if WORLD is None and out and out[0].get('kind') != 'registration': raise PermissionError('ledger line 0 is not the registration')
    return out


def ledger(entry):
    """append-only, hash-chained (the chain is verified before every append)"""
    _writable(); os.makedirs(OUT, exist_ok=True); p = OUT + 'LEDGER.jsonl'; L = read_ledger()
    if WORLD is None and not L and entry.get('kind') != 'registration': raise PermissionError('the first ledger line must be the registration')
    prev = hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else ''
    entry = dict(entry); entry['ts'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()); entry['prev'] = prev
    with open(p, 'a') as f: f.write(json.dumps(entry, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())


DATA_FILES = ['/mnt/project-files/research/data/' + f for f in (
    'panel_f32.npz.xz', 'panel_ext_f32.npz.xz', 'macro_n/raw/DBAA.csv', 'macro_n/raw/DAAA.csv', 'macro_n/raw/BAA.csv',
    'macro_n/raw/AAA.csv', 'deep_history/raw/TB3MS.csv', 'macro_regime/raw/SHILLER_ie_data_current.xls',
    'deep_history/clean/SPX_TR_daily_1927_2014.csv', 'deep_history/clean/TBILL_daily_1927_2014.csv')] + [
    '/mnt/project-files/research/c3_multi/data/kf_sel.bin.xz', '/mnt/project-files/research/c3_brake/code/agents/alt/fin_params.json', xdata.CHIPS]
CORE = [os.path.join(os.path.dirname(os.path.realpath(__file__)), f) for f in ('xv1.py', 'xeng.py', 'xdata.py')]


def _sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _consts(): return json.loads(json.dumps(_FROZEN, sort_keys=True))


def env_hashes():
    """sha256 of every data file of the chain, of the evaluator files and of every project code file loaded so far, the
    package versions and the registered constants. (Candidate files and their helpers are covered by the configuration hashes.)"""
    code = set(CORE) | set(os.path.realpath(m.__file__) for m in list(sys.modules.values())
                           if getattr(m, '__file__', None) and '/project-files/' in os.path.realpath(m.__file__))
    import numba, scipy, llvmlite
    pk = dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, numba=numba.__version__, scipy=scipy.__version__,
              llvmlite=llvmlite.__version__)
    try: import xlrd; pk['xlrd'] = xlrd.__version__
    except Exception: pk['xlrd'] = None
    return dict(data={p: _sha(p) for p in DATA_FILES}, code={p: _sha(p) for p in sorted(code)}, packages=pk, constants=_consts())


def _check_env():
    """Before anything is scored: the registered data files, code files, package versions and constants are the ones in
    use, and no project code file is loaded that the registry does not hold. In a test world a folder without a registry
    is not checked."""
    _guard()
    if WORLD is None and 't_world' in sys.modules: raise PermissionError('a test-world module is loaded in a real run')
    if not os.path.exists(OUT + 'HASHES.json'):
        if WORLD is None: raise PermissionError('the structure is not registered')
        return
    if WORLD is None and not _registered(): raise PermissionError('the registry does not match ledger line 0')
    reg = json.load(open(OUT + 'HASHES.json')); now = env_hashes()
    if any(now['data'].get(k) != v for k, v in reg['data'].items()): raise PermissionError('registered hashes changed: a data file')
    if any((not os.path.exists(k)) or _sha(k) != v for k, v in reg['code'].items()): raise PermissionError('registered hashes changed: a code file')
    new = [k for k in now['code'] if k not in reg['code']]
    if new: raise PermissionError('registered hashes changed: a project code file is loaded that is not registered (%s)' % os.path.basename(new[0]))
    if reg.get('packages') != now['packages']: raise PermissionError('registered hashes changed: package versions')
    if reg.get('constants') != now['constants']: raise PermissionError('registered hashes changed: constants')


def _env_tag():
    """short tag of the registry in force (kept with every partial batch result)"""
    return _sha(OUT + 'HASHES.json')[:16] if os.path.exists(OUT + 'HASHES.json') else ''


def checks_line(passed, detail=None):
    """ledger line of the data and parity checks (m_checks.py); scoring a batch requires a passed line under the registry in force"""
    ledger(dict(kind='checks', passed=bool(passed), env=_env_tag(), detail=detail or {}))


def _checks_passed():
    L = [e for e in read_ledger() if e.get('kind') == 'checks' and e.get('env') == _env_tag()]
    return bool(L) and bool(L[-1].get('passed'))
