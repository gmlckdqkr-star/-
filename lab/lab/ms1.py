"""MS1 and G1 automatic report for lab specs (design side, every number <= 2014-12-31).

MS1 = the project's locked measurement standard (research/measure_std/MEASURE_STD_KO.md + std.py, sha ee4de887037c);
G1  = the information gate (research/breakthrough/INFO_GATE_KO.md + code/gate.py).

OUT OF PROCESS. std.py and the C3 chassis it imports need numba / scipy / xlrd, and their module names (engine,
lab, md, ...) collide with lab's on sys.path, so they are never imported in lab's core or bar processes. `lab run`
starts ONE worker per batch (`<py> -B -c "from lab import ms1; ms1.serve()"`, JSON lines on stdin / stdout);
<py> = env LAB_MS1_PY, else the lab-managed venv LAB_CACHE/ms1-venv (LAB_CACHE default ~/.cache/lab), made by
`python3 -B -m lab setup` (pip install numba scipy xlrd numpy pandas pyyaml from PyPI). NUMBA_CACHE_DIR =
LAB_CACHE/numba. This module imports no numba at import time: the client half runs in lab, serve() in the worker.

MS1 part ('MS1 경로 x% (하한 y%, s0.85 16.2·1x 11.6) dd80 z% s0.85대비 ±a%p 승 b% §5엔진'):
  ENGINE = 'MS1-조건 sleeve 엔진' (lab/ms1eng.py): std.measure's engine holds a level L as TQQQ L/3 + cash, which is
  wrong for QQQ / QLD sleeves (B = 1 gives 2.9%, not the 1x hold 11.6%). The sleeve engine trades the spec's own
  QQQ / QLD / TQQQ / cash weights with exactly beng's MS1 section-1 rules (see ms1eng.py) on the five section-2 bases
  of std.contexts() (dev250_path = headline with path-recomputed macro flags, dev250_glued, real_ndx_86_14,
  real_spx_55_85, real_spx_70_85). MEASURE_STD_KO.md section 5 allows a separate engine with the same section-1
  conditions and section-2 bases, hence the label '§5엔진'. The spec runs through the unchanged lab DSL on every
  path: '_NDX' = the path's NDX price level, each held sleeve's level = its MS1-cost return (level(x), brake),
  macro(k) = ctx.F[k] of that basis, month() / weekday() = the source date of each path row (real dates on the real
  bases). Spec `cost` / `delay` are not used (MS1: 0.3% per side, delay 2); `rebalance:` rows force a trade back to
  target as in lab's dev engine. Headline = dev250_path median after-tax CAGR, floor = std.measure FLOOR_MS1 =
  min(dev250_path, real_ndx_86_14); dd80 = share of dev250_path paths with MDD <= -80%; d / win = path-paired
  difference to s0.85 (std.s085 on the same paths), as std.measure reports them.
  Parity (tests/test_ms1.py): constant TQQQ = std 3x hold row exactly on all 5 bases; TQQQ + cash specs = std.measure
  exactly when every target is a 0.5-level multiple (else the gap is beng's order-step rounding); constant QQQ / QLD
  vs std.hold 1x / 2x rows: see README (std.hold is a separate formula without the yearly 2.5M deduction harvest).
G1 part: the spec compiled on the full real frames (NDX 1984-2014, SPX 1928-1985 with the SPX level in the _NDX
  slot and sleeves from SPX returns, historical macro flags); in market = total risky weight > 0 at close t; SPX
  signal before 1986-01-01 spliced with NDX after; gate.test(sig) raw hits per era, deflated here with the spec
  family's N (ledger): hit - 2 SE sqrt(1 + ln N), verdict on the lower era. In-market share 0 or 1 in an era ->
  'G1 해당 없음' and instead the classic after-cost pre-tax annual Sharpe (sleeve engine, tax 0, real NDX 86-14 and
  real SPX 55-85, lower era) against 1.1 (never mixed with the MS1-basis Sharpe of INFO_GATE_KO.md).
measure_series(dates, daily_ret_after_cost, label): any daily return stream on the MS1 bases by re-sampling it with
  the same path index matrices (the IS1 method, research/indiv_stock/code/bases.py + eng.py), paired with s0.85.
  basis_add (optional, the stock stream): each day's reinvested after-tax dividend / the previous day's level, added
  to the stream's cost basis (the dividend was taxed 15.4% when paid, inside the stream; MS1's 22% falls on the rest).
"""
import hashlib, json, math, os, select, shutil, subprocess, sys, time

from . import data, dsl

LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STD_DIR = '/mnt/project-files/research/measure_std/'
GATE_DIR = '/mnt/project-files/research/breakthrough/code/'
STD_FILE = os.path.join(STD_DIR, 'std.py')
GATE_FILE = os.path.join(GATE_DIR, 'gate.py')
STD_SHA = 'ee4de887037c'          # MEASURE_STD_KO.md: std.py sha256 prefix
GATE_SHA = '8bf8531428cb'         # gate.py sha256 prefix (checked 2026-11-03, the design study's gate.py)
MS1_VERSION = 1                   # bump when the sleeve engine / frames / G1 adapter change (ledger cache key)
SEAL = '2014-12-31'
CACHE = os.environ.get('LAB_CACHE') or os.path.join(os.path.expanduser('~'), '.cache', 'lab')
VENV = os.path.join(CACHE, 'ms1-venv')
FAILED_MARK = os.path.join(CACHE, 'ms1-setup.failed')
READY_MARK = os.path.join(VENV, '.lab_ready')          # written by a successful setup()
PKGS = ['numba', 'scipy', 'xlrd', 'numpy', 'pandas', 'pyyaml']
LEV = {'QQQ': 1, 'QLD': 2, 'TQQQ': 3}
SIG_OK = {'QQQ', 'QLD', 'TQQQ', '_NDX'}
BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85')
ERAS = ('ndx_86_14', 'spx_55_85')
LABEL = 'MS1-조건 sleeve 엔진 (MS1 §5 별도 엔진: §1 조건·§2 기준 그대로)'
SERIES_LABEL = 'MS1 (수익 흐름 재표본, 경로 재계산 없음)'
G1_WORDS = {'CLOSE': '닫음', 'HOLD': '보류', 'BUILD': '설계', '60%-CANDIDATE': '60%후보'}
SHARPE_BAR = 1.1
TIMEOUT = float(os.environ.get('LAB_MS1_TIMEOUT', '3600'))
WARM = 300
COST, TAX, D_UNITS = 0.003, 0.22, 2.5e6 / 10e6          # beng.F1: cost, tax, W0 = 10M -> D = 0.25
FEE1, ER3, CSPR, CTAX = 0.002, 0.0095 + 0.015, 0.02, 0.154


class NotMS1(ValueError):
    pass


# =====================================================================================================================
# client half (lab process: no numba, no std)
# =====================================================================================================================
def _sha12(path):
    try:
        with open(path, 'rb') as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:12]
    except OSError:
        return None


def guard(expect_std=None, expect_gate=None):
    """None if std.py / gate.py are the locked versions, else the refusal text 'MS1 기준 변경됨 (...)'."""
    es, eg = expect_std or STD_SHA, expect_gate or GATE_SHA
    s, g = _sha12(STD_FILE), _sha12(GATE_FILE)
    bad = ([f'std {s or "없음"}≠{es}'] if s != es else []) + ([f'gate {g or "없음"}≠{eg}'] if g != eg else [])
    return f"MS1 기준 변경됨 ({', '.join(bad)})" if bad else None


def cache_key():
    return f'ms1v{MS1_VERSION}@{STD_SHA}:{GATE_SHA}'


def _few(xs, n=3):
    xs = sorted(xs)
    return ','.join(xs[:n]) + ('…' if len(xs) > n else '')


def eligibility(spec):
    """-> (True, dict(held, macro, calendar)) or (False, short Korean reason). MS1 has the NDX price index and the 8
    macro flags on its paths and trades QQQ / QLD / TQQQ / cash in the US 22% account, nothing else."""
    a = spec.get('account', 'us')
    if a != 'us':
        return False, f'계좌 {a}: MS1은 미국 상장 22% 계좌만'
    held = dsl.held_sleeves(spec)
    bad = [s for s in held if s not in LEV]
    if bad:
        return False, f'보유 {_few(bad)}: QQQ·QLD·TQQQ·CASH만'
    names = dsl.spec_names(spec)
    bad = [n for n in names if n not in SIG_OK and not n.startswith('macro:')]
    if bad:
        return False, f'읽는 계열 {_few(bad)}: 나스닥100·macro()만'
    return True, dict(held=held, macro=sorted(dsl.macro_keys(spec)), calendar=uses_calendar(spec))


def uses_calendar(spec):
    import ast
    for e in dsl.spec_exprs(spec):
        if isinstance(e, (int, float)) or not dsl._parses(e):
            continue
        for n in ast.walk(ast.parse(str(e), mode='eval')):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ('month', 'weekday'):
                return True
    return False


def _py_ok(py):
    try:
        r = subprocess.run([py, '-c', 'import numba, scipy, xlrd, numpy, pandas, yaml'], capture_output=True,
                           timeout=180)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def interpreter():
    """The MS1 interpreter path, or None: env LAB_MS1_PY, else LAB_CACHE/ms1-venv/bin/python once setup() finished
    there (a half-built venv does not count)."""
    p = os.environ.get('LAB_MS1_PY')
    if p:
        return shutil.which(p) or (p if os.path.exists(p) else None)
    v = os.path.join(VENV, 'bin', 'python')
    return v if (os.path.exists(v) and os.path.exists(READY_MARK)) else None


def setup(verbose=True):
    """Create LAB_CACHE/ms1-venv and pip install the MS1 packages from PyPI. True on success."""
    os.makedirs(CACHE, exist_ok=True)
    log = os.path.join(CACHE, 'ms1-setup.log')
    py = os.path.join(VENV, 'bin', 'python')
    try:
        with open(log, 'w') as lf:
            if not os.path.exists(py):
                subprocess.run([sys.executable, '-m', 'venv', VENV], stdout=lf, stderr=lf, check=True, timeout=600)
            subprocess.run([py, '-m', 'pip', 'install', '-q', '--disable-pip-version-check'] + PKGS, stdout=lf,
                           stderr=lf, check=True, timeout=1800)
        ok = _py_ok(py)
    except (OSError, subprocess.SubprocessError):
        ok = False
    if ok:
        if os.path.exists(FAILED_MARK):
            os.remove(FAILED_MARK)
        with open(READY_MARK, 'w') as fh:
            fh.write(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + ' ' + ' '.join(PKGS) + '\n')
    else:
        with open(FAILED_MARK, 'w') as fh:
            fh.write(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    if verbose:
        print(f'MS1 환경 {"준비됨" if ok else "설치 실패"}: {VENV} (기록 {log})', flush=True)
    return ok


def ensure_interpreter(auto=True):
    """-> (python path or None, message or None). Missing venv: run setup once (a failed attempt leaves a mark that
    stops further automatic attempts until `python3 -m lab setup` succeeds)."""
    py = interpreter()
    if py:
        return py, None
    if os.environ.get('LAB_MS1_PY'):
        return None, f"MS1: 인터프리터 없음 (LAB_MS1_PY={os.environ['LAB_MS1_PY']})"
    if not auto or os.path.exists(FAILED_MARK):
        return None, 'MS1: 설치 실패 (python3 -m lab setup)'
    print('MS1 계산 환경 설치 중 (numba·scipy, 1~2분, 한 번만)', flush=True)
    if setup(verbose=False):
        return interpreter(), None
    return None, 'MS1: 설치 실패 (python3 -m lab setup)'


class WorkerError(RuntimeError):
    pass


class Worker:
    """One MS1 worker process (cold start ~10-40 s: std contexts, s0.85 reference, numba). Started without waiting;
    the first call waits for its ready line."""

    def __init__(self, py):
        os.makedirs(CACHE, exist_ok=True)
        env = dict(os.environ, NUMBA_CACHE_DIR=os.environ.get('LAB_NUMBA_CACHE', os.path.join(CACHE, 'numba')),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        lf = os.path.join(CACHE, 'ms1-worker.log')
        self.log = open(lf, 'a' if (not os.path.exists(lf) or os.path.getsize(lf) < 5e6) else 'w')
        boot = f'import sys; sys.path.insert(0, {LAB_ROOT!r}); from lab import ms1; ms1.serve()'
        self.p = subprocess.Popen([py, '-B', '-c', boot], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=self.log, env=env, cwd=LAB_ROOT)
        self.ready = None
        self.t0 = time.time()
        self.seq = 0
        self.pending = None

    def _read(self, timeout):
        end = time.time() + timeout
        while True:
            left = end - time.time()
            if left <= 0:
                raise WorkerError('시간 초과')
            r, _, _ = select.select([self.p.stdout], [], [], min(left, 5.0))
            if r:
                line = self.p.stdout.readline()
                if not line:
                    raise WorkerError(f'작업자 종료 (코드 {self.p.poll()}, 기록 {_home(self.log.name)})')
                return json.loads(line.decode('utf-8'))
            if self.p.poll() is not None:
                raise WorkerError(f'작업자 종료 (코드 {self.p.returncode}, 기록 {_home(self.log.name)})')

    def wait_ready(self, timeout=TIMEOUT):
        if self.ready is None:
            self.ready = self._read(timeout)
        if not self.ready.get('ok'):
            raise WorkerError(self.ready.get('error', 'init failed'))
        return self.ready

    def send(self, req, timeout=TIMEOUT):
        """One request at a time: an unanswered request is a protocol error (the caller kills the worker)."""
        self.wait_ready(timeout)
        if self.pending is not None:
            raise WorkerError('이전 요청의 답을 안 읽음')
        self.seq += 1
        try:
            self.p.stdin.write((json.dumps(dict(req, id=self.seq), default=_jdefault) + '\n').encode('utf-8'))
            self.p.stdin.flush()
        except OSError as e:
            raise WorkerError(f'작업자 연결 끊김 ({e})')
        self.pending = self.seq

    def recv(self, timeout=TIMEOUT):
        res = self._read(timeout)
        want, self.pending = self.pending, None
        if res.get('id') != want:
            raise WorkerError(f"답 번호 {res.get('id')} ≠ 요청 {want}")
        if not res.get('ok'):
            raise WorkerError(res.get('error', 'error'))
        return res

    def call(self, req, timeout=TIMEOUT):
        self.send(req, timeout)
        return self.recv(timeout)

    def close(self):
        try:
            if self.p.poll() is None:
                self.p.stdin.close()
                self.p.wait(timeout=10)
        except Exception:
            self.p.kill()
        finally:
            self.log.close()


def _home(p):
    h = os.path.expanduser('~')
    return '~' + p[len(h):] if p.startswith(h + os.sep) else p


def _jdefault(x):
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            return float(x)
        if isinstance(x, (np.bool_,)):
            return bool(x)
    except ImportError:
        pass
    if hasattr(x, 'isoformat'):
        return x.isoformat()
    return str(x)


class Session:
    """What `lab run` holds for a batch: the parts asked for, one lazily started worker, the setup message."""

    def __init__(self, parts=('ms1', 'g1'), auto=True):
        self.parts = tuple(parts)
        self.auto = auto
        self.w = None
        self.msg = None
        self.tried = False

    def worker(self):
        if self.w is None and not self.tried:
            self.tried = True
            py, self.msg = ensure_interpreter(self.auto)
            if py:
                self.w = Worker(py)
        return self.w

    def close(self):
        if self.w is not None:
            self.w.close()
            self.w = None


def needs_compute(spec, h, parts):
    from . import ledger
    if dsl.is_universe(spec):                 # stock spec: the MS1 stream always needs the worker, G1 only with a gate
        if guard():
            return False
        hit = ledger.get_std(h, stock_key()) or {}
        return ('ms1' in parts and 'ms1' not in hit) or ('g1' in parts and 'g1' not in hit and _stock_gate(spec)[0])
    ok, _ = eligibility(spec)
    if not ok or guard():
        return False
    hit = ledger.get_std(h, cache_key()) or {}
    return any(p not in hit for p in parts)


def _final(text):
    return dict(text=text, ms1=None, g1=None, detail=None, cached=False)


def begin(spec, h, family, ses):
    """First half of report(): eligibility, version guard, ledger cache; a missing part is SENT to the worker (the
    caller can run the bar meanwhile) and collected by finish()."""
    from . import ledger
    ok, info = eligibility(spec)
    if not ok:
        return dict(final=_final(f'MS1: 해당 없음 ({info})'))
    g = guard()
    if g:
        return dict(final=_final(g))
    key = cache_key()
    hit = ledger.get_std(h, key) or {}
    todo = [p for p in ses.parts if p not in hit]
    st = dict(h=h, key=key, hit=hit, todo=todo, family=family, ses=ses, w=None)
    if todo:
        w = ses.worker()
        if w is None:
            return dict(final=_final(ses.msg or 'MS1: 설치 실패 (python3 -m lab setup)'))
        try:
            w.send(dict(op='spec', spec=spec, parts=todo))
        except WorkerError as e:
            ses.close(); ses.tried = False
            return dict(final=_final(f'MS1: 오류 ({e})'[:160]))
        st['w'] = w
    return st


def finish(st):
    """-> dict(text, ms1 (headline or None), g1 (verdict word or None), detail, cached). Cached in the ledger by
    (spec hash, std / gate sha, MS1_VERSION); the G1 deflation uses the family N at report time."""
    from . import ledger
    if 'final' in st:
        return st['final']
    if st.get('kind') == 'stock':
        return _finish_stock(st)
    ses, hit, todo = st['ses'], st['hit'], st['todo']
    cached = not todo
    if todo:
        try:
            res = st['w'].recv()
        except WorkerError as e:
            ses.close(); ses.tried = False                  # a dead worker is restarted for the next spec
            return _final(f'MS1: 오류 ({e})'[:160])
        hit.update({p: res[p] for p in todo})
        ledger.put_std(st['h'], st['key'], hit)
    N = ledger.family_n(st['family'])
    parts, out = [], dict(ms1=None, g1=None)
    if 'ms1' in ses.parts:
        parts.append(fmt_ms1(hit['ms1']))
        out['ms1'] = hit['ms1']['HEADLINE_MS1']
    if 'g1' in ses.parts:
        ev = g1_eval(hit['g1'], N)
        parts.append(fmt_g1(hit['g1'], ev, N))
        out['g1'] = ev.get('verdict') if hit['g1'].get('binary') else g1_word(hit['g1'])
    return dict(out, text=' | '.join(parts), detail=hit, cached=cached, short=_short_text(hit, ses.parts, N),
                key=st['key'], label=LABEL)


def report(spec, h, family, ses):
    return finish(begin(spec, h, family, ses))


# ---------------- single-stock specs (universe: sp500, lab/stocks.py) ----------------
STOCK_MS1_VERSION = 2             # bump when the stock stream / gate adapter changes (ledger cache key)
                                  # 2: the stream is after the dividend tax, its dividends are cost basis (basis_add)


def stock_key():
    """Ledger key of a stock spec's MS1 / G1 report: engine + std / gate sha, the stock summary version (the stream
    is that summary's conservative book) and this adapter's version."""
    from . import stocks
    return f'{cache_key()}:stk{stocks.STOCK_VERSION}.{STOCK_MS1_VERSION}'


def _stock_gate(spec):
    """-> (True, gate spec) when the stock spec's exposure gate can go on the G1 frames, (False, None) without a gate,
    (False, reason) when the gate reads series the G1 frames do not have."""
    from . import stocks
    gs = stocks.gate_spec(spec)
    if gs is None:
        return False, None
    ok, info = eligibility(dsl.check_spec(gs))
    return (True, gs) if ok else (False, info)


def begin_stock(spec, h, family, ses, stream_fn):
    """begin() for a stock spec. MS1 = measure_series on the strategy's own daily return stream (stream_fn():
    stocks.ms1_stream, the CONSERVATIVE book after trading cost and the dividend tax, before the 22% tax, real dates,
    with its reinvested dividends as basis_add; the IS1 method: re-sampled
    with std.contexts()' path index matrices, no path recomputation). G1 = the Sharpe branch of the dev summary
    (after-cost pre-tax Sharpe 1986-2014 vs 1.1, in stocks.evaluate) and, when the spec has an exposure gate,
    gate.test on that gate (stocks.gate_spec: the gate as a QQQ / cash spec, compiled on the G1 real frames exactly
    like an ETF spec's signal). Same worker and ledger table as the ETF specs, own key (stock_key)."""
    from . import ledger
    g = guard()
    if g:
        return dict(final=_final(g))
    key = stock_key()
    hit = ledger.get_std(h, key) or {}
    todo = [p for p in ses.parts if p not in hit]
    st = dict(h=h, key=key, hit=hit, todo=todo, family=family, ses=ses, w=None, kind='stock', sent=[])
    req = dict(op='stock', parts=[])
    if 'g1' in todo:
        ok, gs = _stock_gate(spec)
        if ok:
            req['gate'] = gs; req['parts'].append('g1')
        else:
            hit['g1'] = dict(gate=gs is not None, na=gs)
    if 'ms1' in todo:
        try:
            req.update(stream_fn())
        except Exception as e:                       # a stream that cannot be built: say so, keep the dev line
            return dict(final=_final(f'MS1: 오류 ({type(e).__name__}: {e})'[:160]))
        req['parts'].append('ms1')
    if req['parts']:
        w = ses.worker()
        if w is None:
            return dict(final=_final(ses.msg or 'MS1: 설치 실패 (python3 -m lab setup)'))
        try:
            w.send(req)
        except WorkerError as e:
            ses.close(); ses.tried = False
            return dict(final=_final(f'MS1: 오류 ({e})'[:160]))
        st['w'] = w; st['sent'] = list(req['parts'])
    return st


def _finish_stock(st):
    from . import ledger
    ses, hit, todo = st['ses'], st['hit'], st['todo']
    if st['sent']:
        try:
            res = st['w'].recv()
        except WorkerError as e:
            ses.close(); ses.tried = False
            return _final(f'MS1: 오류 ({e})'[:160])
        hit.update({p: res[p] for p in st['sent']})
    if todo:
        ledger.put_std(st['h'], st['key'], hit)
    N = ledger.family_n(st['family'])
    full, short, least, out = [], [], [], dict(ms1=None, g1=None)
    if 'ms1' in ses.parts:
        a, b, c = fmt_stream(hit['ms1'])
        full.append(a); short.append(b); least.append(c)
        out['ms1'] = hit['ms1'].get('HEADLINE_MS1')
    if 'g1' in ses.parts:
        g = hit['g1']
        a, b, c = fmt_gate(g, N)
        if a:
            full.append(a); short.append(b); least.append(c)
        if g.get('binary'):
            out['g1'] = g1_eval(g, N)['verdict']
        elif g.get('gate'):
            out['g1'] = '게이트 해당없음'
    return dict(out, text=' | '.join(full), short=' | '.join(short), shortest=' | '.join(least), detail=hit,
                cached=not todo, key=st['key'], label=SERIES_LABEL)


def fmt_stream(m):
    """(full, short, shortest) MS1 text of a return stream (measure_series result), same numbers."""
    p = m.get('dev250_path')
    if not p:
        cv = (m.get('cover') or {}).get('dev250_path', 0.0)
        t = f"MS1(수익 흐름 재표본) 경로 없음 (흐름 {str(m.get('start', '?'))[:4]}~, 덮음 {cv:.0%}<95%)"
        return t, t, f"MS1흐름 경로 없음 (덮음 {cv:.0%})"
    ref = f"(s0.85 {100 * p['ref_s085']:.1f}·1x {100 * p['hold1x']:.1f})"
    lo = m.get('FLOOR_MS1')
    full = (f"MS1(수익 흐름 재표본) 경로 {p['cagr']:.1%} "
            + (f"(하한 {lo:.1%}, " + ref[1:] if lo is not None else ref)
            + f" dd80 {p['dd80']:.0%} s0.85대비 {100 * p['d_vs_s085']:+.1f}%p")
    return full, f"MS1(수익 흐름 재표본) 경로 {p['cagr']:.1%} {ref}", f"MS1흐름 경로 {p['cagr']:.1%}{ref}"


def fmt_gate(g, N):
    """(full, short, shortest) G1 text of a stock spec's exposure gate ('' when the spec has no gate: the Sharpe
    branch of the dev part is the G1 answer)."""
    if not g.get('gate'):
        return '', '', ''
    if g.get('na'):
        t = f"G1 게이트 해당 없음 ({g['na']})"
        return t, t, 'G1게이트 해당 없음'
    if not g.get('binary'):
        t = f"G1 게이트 해당 없음 ({'상시 현금' if g.get('all_out') else '상시 보유'})"
        return t, t, t.replace('G1 게이트 ', 'G1게이트 ')
    ev = g1_eval(g, N)
    a, b = g['ndx_86_14'], g['spx_55_85']
    v = ev['verdict']
    return (f"G1 게이트 NDX {100 * a['hit']:.1f}(상시{100 * a['always_up']:.1f}) SPX {100 * b['hit']:.1f}"
            f"({100 * b['always_up']:.1f}) 보정 {100 * ev['low']:.1f} N={N} {G1_WORDS[v]} {v}",
            f"G1게이트 {100 * a['hit']:.1f}/{100 * a['always_up']:.1f}·{100 * b['hit']:.1f}/{100 * b['always_up']:.1f}"
            f" 보정{100 * ev['low']:.1f} N{N} {v}",
            f"G1게이트 {100 * a['hit']:.1f}·{100 * b['hit']:.1f} 보정{100 * ev['low']:.1f} N{N} {v}")


def abandon(st):
    """The caller failed between begin() and finish(): a request still in flight would answer the NEXT spec's read,
    so the worker is stopped (the next spec starts a fresh one)."""
    if st is not None and st.get('w') is not None:
        ses = st['ses']
        ses.close(); ses.tried = False


def _short_text(hit, parts, N):
    """Compact form for a crowded line (same numbers, fewer words)."""
    out = []
    if 'ms1' in parts:
        out.append(fmt_ms1(hit['ms1']).replace(' §5엔진', ' §5'))
    if 'g1' in parts:
        g = hit['g1']
        if g.get('binary'):
            ev = g1_eval(g, N)
            a, b = g['ndx_86_14'], g['spx_55_85']
            out.append(f"G1 {100 * a['hit']:.1f}/{100 * a['always_up']:.1f}·{100 * b['hit']:.1f}/"
                       f"{100 * b['always_up']:.1f} 보정{100 * ev['low']:.1f} N{N} {ev['verdict']}")
        else:
            out.append(fmt_g1(g, g1_eval(g, N), N).replace('샤프(비용후·세전)', '샤프'))
    return ' | '.join(out)


def fmt_ms1(m):
    p = m['dev250_path']
    return (f"MS1 경로 {p['cagr']:.1%} (하한 {m['FLOOR_MS1']:.1%}, s0.85 {100 * p['ref_s085']:.1f}·1x "
            f"{100 * p['hold1x']:.1f}) dd80 {p['dd80']:.0%} s0.85대비 {100 * p['d_vs_s085']:+.1f}%p "
            f"승 {p['pw_vs_s085']:.0%} §5엔진")


def g1_eval(g, N):
    """gate.test's deflation and verdict, with trials = N (the spec family's count in the ledger)."""
    out = {}
    k = 2.0 * math.sqrt(1.0 + math.log(max(int(N or 1), 1)))
    for era in ERAS:
        e = g.get(era)
        if e:
            out[era] = e['hit'] - k * e['se']
    low = min(out.values()) if out else 0.0
    v = '60%-CANDIDATE' if low >= .77 else 'BUILD' if low >= .70 else 'HOLD' if low >= .65 else 'CLOSE'
    return dict(deflated=out, low=low, verdict=v)


def g1_word(g):
    """Summary-table word of a G1 with no timing answer (always in / always out): the Sharpe branch vs 1.1."""
    what = '상시현금' if g.get('all_out') else '상시'
    sh = g.get('sharpe') or {}
    if not sh:
        return what
    return f"{what}·샤프{'통과' if min(sh.values()) >= SHARPE_BAR else '닫음'}"


def fmt_g1(g, ev, N):
    if not g.get('binary'):
        what = '상시 현금' if g.get('all_out') else '상시 보유'
        sh = g.get('sharpe') or {}
        if not sh:
            return f'G1 해당 없음 ({what})'
        era = min(sh, key=sh.get)
        x = sh[era]
        return (f"G1 해당 없음 ({what}) 샤프(비용후·세전) {x:.2f} {'≥' if x >= SHARPE_BAR else '<'}1.1 "
                f"{'통과' if x >= SHARPE_BAR else '닫음'} ({'NDX' if 'ndx' in era else 'SPX'})")
    a, b = g['ndx_86_14'], g['spx_55_85']
    v = ev['verdict']
    return (f"G1 NDX {100 * a['hit']:.1f}(상시{100 * a['always_up']:.1f}) SPX {100 * b['hit']:.1f}"
            f"({100 * b['always_up']:.1f}) 보정 {100 * ev['low']:.1f} N={N} {G1_WORDS[v]} {v}")


_SES = None


def measure_series(dates, daily_ret_after_cost, label, turnover=1.0, min_cover=0.95, basis_add=None):
    """Measure an arbitrary daily return stream (after trading cost) on the MS1 bases, re-sampled with the same path
    index matrices as std.contexts() (paired with s0.85 path by path). Tax: IS1 rules (research/indiv_stock/code/
    eng.py): every 252 days 22% of max(min(1, turnover) x unrealized gain - 2.5M/10M, 0), no carry-forward, entry and
    exit cost 0.3%, liquidation tax. turnover = one-way yearly turnover of the strategy behind the stream (0 =
    buy and hold, only the liquidation is taxed; default 1 = every year's gain realized, the conservative side).
    basis_add (optional, same length as the stream): the part of each day's return that is reinvested cash already
    taxed (a dividend after its 15.4% tax), as a share of the previous day's level: it is added to the cost basis of
    the re-sampled path (moved with its day), so the 22% tax never falls on it (no double tax). None = 0 (an ETF or
    price stream: every gain is a capital gain). IS1's flat div_tax drag is NOT applied (the stock stream already pays
    the dividend tax day by day).
    A basis whose used source days the stream covers less than min_cover -> None. Rows after 2014-12-31 are dropped
    (seal). -> dict(basis -> row or None, HEADLINE_MS1, FLOOR_MS1, label, cover). No path recomputation: the stream
    is what it is; the label says so."""
    global _SES
    import numpy as np, pandas as pd
    d = pd.DatetimeIndex(pd.to_datetime(dates))
    x = np.asarray(daily_ret_after_cost, float)
    req = dict(op='series', dates=[t.strftime('%Y-%m-%d') for t in d], ret=x.tolist(), label=str(label),
               turnover=float(turnover), min_cover=float(min_cover))
    if basis_add is not None:
        q = np.asarray(basis_add, float)
        if q.shape != x.shape:
            raise ValueError(f'basis_add: {q.shape} values for a stream of {x.shape}')
        req['basis_add'] = q.tolist()
    if _SRV is not None:                                   # already inside the worker
        return _SRV.series(req)
    g = guard()
    if g:
        raise WorkerError(g)
    if _SES is None:
        _SES = Session(('series',))
    w = _SES.worker()
    if w is None:
        raise WorkerError(_SES.msg or 'MS1: 설치 실패 (python3 -m lab setup)')
    res = w.call(req)
    return res['series']


# =====================================================================================================================
# worker half (runs only inside serve(): imports std / numba)
# =====================================================================================================================
_SRV = None


def serve():
    """Worker main loop: one JSON request per stdin line, one JSON answer per stdout line. Everything the MS1 code
    prints goes to stderr (the log)."""
    global _SRV
    out = os.fdopen(os.dup(1), 'w', buffering=1, encoding='utf-8')
    os.dup2(2, 1)
    sys.stdout = sys.stderr

    def send(d):
        out.write(json.dumps(d, default=_jdefault) + '\n'); out.flush()
    t0 = time.time()
    try:
        _SRV = _Server()
        send(dict(ok=True, ready=True, secs=round(time.time() - t0, 1), std=STD_SHA, gate=GATE_SHA))
    except Exception as e:
        import traceback; traceback.print_exc()
        send(dict(ok=False, error=f'{type(e).__name__}: {e}'[:300]))
        return
    while True:
        line = sys.stdin.readline()
        if not line:
            return
        rid = None
        try:
            req = json.loads(line)
            rid = req.get('id')
            res = _SRV.handle(req)
            send(dict(res, ok=True, id=rid))
        except Exception as e:
            import traceback; traceback.print_exc()
            send(dict(ok=False, id=rid, error=f'{type(e).__name__}: {e}'[:300]))


def _no_series(*a, **k):
    raise NotMS1('the spec reads a panel series that is not on an MS1 path')


class _Server:
    def __init__(self):
        g = guard()
        if g:
            raise NotMS1(g)
        sys.dont_write_bytecode = True
        for p in (GATE_DIR, STD_DIR):
            if p not in sys.path:
                sys.path.insert(0, p)
        import numpy as np, pandas as pd
        import std, ov, jp, gate        # noqa: F401  (std puts the C3 chassis folders on sys.path)
        from . import ms1eng
        self.np, self.pd, self.std, self.ov, self.jp, self.gate, self.eng = np, pd, std, ov, jp, gate, ms1eng
        assert ov.WARM == WARM == ms1eng.WARM
        self.seal = pd.Timestamp(SEAL)
        self.C = std.contexts()
        # source calendars (the ones std.contexts() samples from) and the DSL frame dates per basis
        R, M = jp.calendar('1984-01-03', SEAL); Xn = jp.mkX(R, M, 'NDX')
        R, M = jp.calendar('1928-01-03', '1985-12-31'); Xs = jp.mkX(R, M, 'SPX')
        a, b = std.iv.POOLS['dev250'][:2]
        R, M = jp.calendar(a, b); Xd = jp.mkX(R, M, 'NDX')
        self.X = dict(ndx=Xn, spx=Xs, dev=Xd)
        self.src = {'dev250_path': 'dev', 'dev250_glued': 'dev', 'real_ndx_86_14': 'ndx', 'real_spx_55_85': 'spx',
                    'real_spx_70_85': 'spx'}
        self.dates, self.srcdates = {}, {}
        for bn in BASES:
            c = self.C[bn]; X = self.X[self.src[bn]]
            sd = X.index.values[c.ii]                                  # (P, T) source dates of every path row
            if sd.max() > self.seal.to_datetime64():
                raise RuntimeError(f'{bn}: source dates after {SEAL}')
            self.srcdates[bn] = sd
            self.dates[bn] = (pd.DatetimeIndex(sd[0]) if c.P == 1 else pd.bdate_range(end=SEAL, periods=c.T))
        self._ref = {}
        self._g1f = None
        for bn in BASES:                                   # s0.85 / hold references (disk cache after the first run)
            self.ref(bn)
        x = np.zeros((1, WARM + 2, 1))                     # load the sleeve kernel (numba cache) before the first spec
        ms1eng.runP(x, np.zeros((1, WARM + 2)), x, np.zeros((1, WARM + 2), np.bool_), 2, COST, TAX, D_UNITS, 3, 1.0)

    # ---------------- MS1 references (s0.85 per path, hold rows: exactly std.measure's) ----------------
    def _ref_file(self):
        """Disk cache of the reference rows (std.engine re-JITs its brake-function signature in every process,
        ~20 s): keyed by the sha of std.py AND of every chassis module it imports. <= 2014 numbers only."""
        h = hashlib.sha256()
        for m in ('std', 'jp', 'ov', 'bk', 'ce', 'beng', 'brakes', 'rx', 'iv', 'md', 'mkt'):
            f = getattr(sys.modules.get(m), '__file__', None)
            h.update((m + ':' + (_sha12(f) or '-') + ';').encode())
        return os.path.join(CACHE, f'ms1_ref_{STD_SHA}_{h.hexdigest()[:12]}.json')

    def ref(self, bn):
        np = self.np
        if not self._ref:
            try:
                with open(self._ref_file()) as fh:
                    d = json.load(fh)
                self._ref = {k: dict(v, fin=np.asarray(v['fin'], float)) for k, v in d.items()}
            except (OSError, ValueError, KeyError):
                self._ref = {}
        if bn not in self._ref:
            std, c = self.std, self.C[bn]
            rB, rbf, rbp, rfs = std.s085(c)
            ref, fr = std.row(*std.engine(c, rB, rbf, rbp, rfs))
            q, _ = std.row(*std.hold(c, 1)); l, _ = std.row(*std.hold(c, 2))
            t, _ = std.row(*std.engine(c, np.full(c.r.shape, 3.0), std.ident, np.zeros(1), 0.5))
            self._ref[bn] = dict(fin=fr, s085=ref['cagr'], hold1x=q['cagr'], hold2x=l['cagr'], hold3x=t['cagr'])
            if all(b in self._ref for b in BASES):
                try:
                    os.makedirs(CACHE, exist_ok=True)
                    tmp = self._ref_file() + '.tmp'
                    with open(tmp, 'w') as fh:
                        json.dump({k: dict(v, fin=v['fin'].tolist()) for k, v in self._ref.items()}, fh)
                    os.replace(tmp, self._ref_file())
                except OSError:
                    pass
        return self._ref[bn]

    def handle(self, req):
        op = req.get('op')
        if op == 'spec':
            return self.spec(req['spec'], req.get('parts') or ['ms1', 'g1'])
        if op == 'series':
            return dict(series=self.series(req))
        if op == 'stock':                         # a stock spec: its return stream + (optional) exposure gate
            out = {}
            if 'ms1' in req['parts']:
                out['ms1'] = dict(self.series(req), start=req.get('start'), stream_label=req.get('label'))
            if 'g1' in req['parts']:
                gs = dsl.check_spec(req['gate'])
                ok, el = eligibility(gs)
                if not ok:
                    raise NotMS1(el)
                out['g1'] = dict(self.g1(gs, el, None, sharpe=False), gate=True)
            return out
        if op == 'ping':
            return dict(pong=True)
        if op == 'hold_stream':                   # tests: the NDX 1x hold stream of a basis' source calendar
            X = self.X[req.get('cal', 'ndx')]
            r = X['r'].values - FEE1 / 252
            return dict(dates=[t.strftime('%Y-%m-%d') for t in X.index], ret=r.tolist())
        if op == 'std_measure_tqqq':              # tests: std.measure on a TQQQ + cash spec (level = 3 x weight)
            return dict(T=self.std_measure_tqqq(req['spec'], float(req.get('fstep', 0.1))))
        if op == 'sleeve_parity':                 # tests: pre-tax sleeve curves vs std.hold's formula curves
            return dict(dev=self.sleeve_parity())
        if op == 'flags_hist':                    # tests: ov.flags_hist on the two MS1 source calendars
            out = {}
            for cal in ('ndx', 'spx'):
                Fh = self.ov.flags_hist(self.X[cal])
                out[cal] = dict(dates=[t.strftime('%Y-%m-%d') for t in Fh.index],
                                flags={k: Fh[k].astype(int).tolist() for k in data.MACRO_KEYS})
            return out
        if op == 'gate_selfcheck':                # tests: gate.py's own self-check (always in, look-ahead oracle)
            L = self.gate.labels()
            both = self.pd.concat([L['spx_55_85'], L['ndx_86_14']])
            both = both[~both.index.duplicated(keep='last')].sort_index()
            a = self.gate.test(self.pd.Series(True, index=both.index), verbose=False)
            o = self.gate.test(L['ndx_86_14'].astype(bool), verbose=False)
            return dict(always={e: a[e]['hit'] for e in ERAS}, always_verdict=a['verdict'],
                        oracle_ndx=o['ndx_86_14']['hit'], oracle_verdict=o['verdict'])
        if op == 'seal':                          # tests: last source date of every basis and G1 frame
            g = self.g1_frames()
            return dict(bases={bn: str(self.pd.Timestamp(self.srcdates[bn].max()).date()) for bn in BASES},
                        g1={e: str(g[e]['X'].index.max().date()) for e in ERAS},
                        labels={e: str(v.index.max().date()) for e, v in self.gate.labels().items()})
        raise ValueError(f'unknown op {op!r}')

    def sleeve_parity(self):
        """Pre-tax, no-trade check of the sleeve return formulas: the engine's equity for a constant weight 1 in
        QQQ / QLD / TQQQ must be proportional to std.hold's cumulative curve of the same leverage (std.hold applies
        the first day's return and no entry cost, the engine buys at close k = 0: a constant ratio)."""
        np, std = self.np, self.std
        out = {}
        for bn in BASES:
            c = self.C[bn]
            for s, L in LEV.items():
                W = np.ones((c.P, c.T, 1)); force = np.zeros((c.P, c.T), np.bool_)
                _, E, _ = self.run(bn, [s], W, force, tax=0.0)
                _, Eh = std.hold(c, L, tax=0.0)
                q = E / Eh
                out[f'{bn}:{s}'] = float(np.abs(q / q[:, :1] - 1).max())
        return out

    # ---------------- frames and weights ----------------
    def sleeve_returns(self, r, rf, L):
        if L == 1:
            return r - FEE1 / 252
        return L * r - (L - 1) * rf - ER3 / 252

    def _frame(self, i, bn, c, held, mac, cal, dates, lv):
        pd = self.pd
        F = {'_NDX': c.lvl[i]}
        for s in held:
            F[s] = lv[s][i]
        for k in mac:
            F['macro:' + k] = c.F[k][i]
        if cal:
            sd = pd.DatetimeIndex(self.srcdates[bn][i])
            F['cal:month'] = sd.month.values; F['cal:weekday'] = sd.weekday.values
        return pd.DataFrame(F, index=dates)

    def weights(self, spec, bn, el):
        """(P, T, S) decided weights of the spec's held sleeves on every path of basis bn, + (P, T) forced rows."""
        np, pd, c = self.np, self.pd, self.C[bn]
        held, mac, cal = el['held'], el['macro'], el['calendar']
        dates = self.dates[bn]
        lv = {}
        for s in held:
            x = self.sleeve_returns(c.r, c.rf, LEV[s]).copy(); x[:, 0] = 0.0
            lv[s] = np.cumprod(1.0 + x, axis=1)
        W = np.zeros((c.P, c.T, max(len(held), 1)))
        orig = (data.series, data.macro_flags)
        data.series = data.macro_flags = _no_series        # nothing but the path's own columns on an MS1 path
        try:
            for i in range(c.P):
                Wi = dsl.compile_weights(spec, self._frame(i, bn, c, held, mac, cal, dates, lv), held)
                for j, s in enumerate(held):
                    if s in Wi.columns:
                        W[i, :, j] = Wi[s].values
        finally:
            data.series, data.macro_flags = orig
        reb = spec.get('rebalance', 'daily')
        force = np.zeros((c.P, c.T), np.bool_)
        if reb != 'daily':
            force[:] = dsl.reb_rows(dates, reb)[None, :]
        return np.nan_to_num(np.clip(W, 0.0, 1.0)), force

    def run(self, bn, held, W, force, tax=TAX):
        np, c = self.np, self.C[bn]
        S = max(len(held), 1)
        R = np.zeros((c.P, c.T, S))
        for j, s in enumerate(held):
            R[:, :, j] = self.sleeve_returns(c.r, c.rf, LEV[s])
        CR = np.ascontiguousarray(np.maximum(c.rf - CSPR / 252, 0.0) * (1 - CTAX))
        fin, EE, ntr = self.eng.runP(R, CR, np.ascontiguousarray(W), np.ascontiguousarray(force), 2, COST, tax,
                                     D_UNITS if tax > 0 else 0.0, 3, 1.0)
        yrs = EE.shape[1] / 252
        return np.maximum(fin, 1e-9) ** (1 / yrs) - 1, EE, ntr / yrs

    # ---------------- MS1 ----------------
    def spec(self, spec, parts):
        spec = dsl.check_spec(spec)
        ok, el = eligibility(spec)
        if not ok:
            raise NotMS1(el)
        out, Wc = {}, {}
        t0 = time.time()

        def w_of(bn):          # dev250_path / _glued share r, ii and dates: same weights unless macro flags differ
            key = bn if (el['macro'] or not bn.startswith('dev250')) else 'dev250'
            if key not in Wc:
                Wc[key] = self.weights(spec, bn, el)
            return Wc[key]
        if 'ms1' in parts:
            out['ms1'] = self.ms1(el, w_of)
        if 'g1' in parts:
            out['g1'] = self.g1(spec, el, w_of)
        out['secs'] = round(time.time() - t0, 1)
        return out

    def ms1(self, el, w_of):
        np, std = self.np, self.std
        res = {}
        for bn in BASES:
            W, force = w_of(bn)
            fin, E, tr = self.run(bn, el['held'], W, force)
            row, fc = std.row(fin, E)
            rf = self.ref(bn)
            d = fc - rf['fin']
            row.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=rf['s085'],
                       hold1x=rf['hold1x'], hold2x=rf['hold2x'], hold3x=rf['hold3x'],
                       trades_yr=float(np.median(tr)), risk_w=float(W[:, WARM:].sum(2).mean()))
            res[bn] = row
        res['HEADLINE_MS1'] = res['dev250_path']['cagr']
        res['FLOOR_MS1'] = min(res['dev250_path']['cagr'], res['real_ndx_86_14']['cagr'])
        res['label'] = LABEL
        return res

    # ---------------- G1 ----------------
    def g1_frames(self):
        if self._g1f is None:
            np, ov = self.np, self.ov
            self._g1f = {}
            for era, cal in (('ndx_86_14', 'ndx'), ('spx_55_85', 'spx')):
                X = self.X[cal]
                r = X['r'].values.copy(); r[0] = 0.0
                Fh = ov.flags_hist(X)
                self._g1f[era] = dict(X=X, r=r, rf=X['rf'].values, lvl=np.cumprod(1 + r),
                                      F={k: Fh[k].values.astype(bool) for k in Fh.columns})
        return self._g1f

    def g1(self, spec, el, w_of, sharpe=True):
        np, pd, gate = self.np, self.pd, self.gate
        held, mac = el['held'], el['macro']
        sigs = {}
        orig = (data.series, data.macro_flags)
        data.series = data.macro_flags = _no_series
        try:
            for era, d in self.g1_frames().items():
                F = {'_NDX': d['lvl']}
                for s in held:
                    x = self.sleeve_returns(d['r'], d['rf'], LEV[s]).copy(); x[0] = 0.0
                    F[s] = np.cumprod(1 + x)
                for k in mac:
                    F['macro:' + k] = d['F'][k]
                W = dsl.compile_weights(spec, pd.DataFrame(F, index=d['X'].index), held)
                risk = W[[s for s in held if s in W.columns]].sum(1).values if held else np.zeros(len(W))
                sigs[era] = pd.Series(np.nan_to_num(risk) > 1e-12, index=d['X'].index)
        finally:
            data.series, data.macro_flags = orig
        L = gate.labels()
        frac = {era: float(sigs[era].reindex(L[era].index, method='ffill').fillna(False).mean()) for era in ERAS}
        cut = pd.Timestamp('1986-01-01')
        s = pd.concat([sigs['spx_55_85'][sigs['spx_55_85'].index < cut], sigs['ndx_86_14'][sigs['ndx_86_14'].index >= cut]])
        assert s.index.max() <= self.seal
        t = gate.test(s, trials=1, name=str(spec.get('name', 'spec')), verbose=False)
        out = dict(binary=all(0.0 < f < 1.0 for f in frac.values()), all_out=all(f == 0.0 for f in frac.values()),
                   gate_raw_verdict=t['verdict'])
        for era in ERAS:
            e = t.get(era)
            out[era] = None if e is None else dict(hit=e['hit'], n=e['n'], se=e['se'], always_up=e['always_up'],
                                                   frac=frac[era])
        if not out['binary'] and sharpe:
            out['sharpe'] = {}
            for bn in ('real_ndx_86_14', 'real_spx_55_85'):
                W, force = w_of(bn)
                _, E, _ = self.run(bn, held, W, force, tax=0.0)
                rf = self.C[bn].rf[0, WARM + 1:]
                x = np.diff(E[0]) / E[0][:-1] - rf
                out['sharpe'][bn] = float(x.mean() / x.std() * 252 ** .5) if x.std() > 0 else 0.0
        return out

    # ---------------- parity helper: std.measure on a TQQQ + cash spec ----------------
    def std_measure_tqqq(self, spec, fstep):
        ok, el = eligibility(dsl.check_spec(spec))
        if not ok or el['held'] != ['TQQQ']:
            raise NotMS1('std.measure parity needs a TQQQ + CASH spec')
        cache = {}

        def make(c):
            bn = next(k for k, v in self.C.items() if v is c)
            key = bn if (el['macro'] or not bn.startswith('dev250')) else 'dev250'
            if key not in cache:
                cache[key] = 3.0 * self.weights(spec, bn, el)[0][:, :, 0]
            return cache[key], self.std.ident, self.np.zeros(1), fstep
        return self.std.measure(str(spec.get('name', 'spec')), make, verbose=False)

    # ---------------- arbitrary return stream (IS1 method) ----------------
    def series(self, req):
        np, pd, std = self.np, self.pd, self.std
        x = np.asarray(req['ret'], float)
        qa = req.get('basis_add')
        qa = np.zeros(len(x)) if qa is None else np.asarray(qa, float)
        if qa.shape != x.shape:
            raise ValueError(f'basis_add: {qa.shape} values for a stream of {x.shape}')
        S = pd.DataFrame(dict(r=x, q=qa), index=pd.DatetimeIndex(pd.to_datetime(req['dates'])))
        S = S[~S.index.duplicated(keep='last')].sort_index()
        n_cut = int((S.index > self.seal).sum())
        S = S[(S.index <= self.seal) & S['r'].notna()]
        s = S['r']
        share = min(1.0, max(0.0, float(req.get('turnover', 1.0))))
        out = dict(label=SERIES_LABEL + f' [{req.get("label", "")}]', cut_after_seal=n_cut, turnover=share, cover={},
                   basis_add=bool(np.any(qa != 0)))
        lvl = (1.0 + s).cumprod()
        # reinvested taxed cash (basis_add) in level units, cumulated: moved onto the source calendar like the level
        cc = (S['q'].fillna(0.0) * lvl.shift(1).fillna(1.0)).cumsum()
        for bn in BASES:
            c = self.C[bn]; X = self.X[self.src[bn]]
            if len(s):
                # stream level on the source calendar = level at the latest stream date on or before each source
                # date (1.0 before the stream's first return); source-day return = ratio of consecutive levels
                L = lvl.reindex(X.index, method='ffill')
                v = np.array(L / L.shift(1).fillna(1.0) - 1.0, dtype=float)
                v[0] = 0.0
                have = np.asarray((X.index >= s.index[0]) & (X.index <= s.index[-1]))
                v = np.where(have, np.nan_to_num(v), 0.0)
                C = cc.reindex(X.index, method='ffill').fillna(0.0)
                qv = np.array((C - C.shift(1).fillna(0.0)) / L.shift(1).fillna(1.0), dtype=float)
                qv[0] = 0.0
                qv = np.where(have, np.nan_to_num(qv), 0.0)
            else:
                v, have = np.zeros(len(X)), np.zeros(len(X), bool)
                qv = np.zeros(len(X))
            used = c.ii[:, WARM:]
            cover = float(have[used].mean())
            out['cover'][bn] = cover
            if cover < float(req.get('min_cover', 0.95)):
                out[bn] = None
                continue
            Mx = v[c.ii]; Mx[:, 0] = 0.0; Mx = np.ascontiguousarray(Mx[:, WARM:])
            Qx = qv[c.ii]; Qx[:, 0] = 0.0; Qx = np.ascontiguousarray(Qx[:, WARM:])
            fin, E = self.eng.series_run(Mx, Qx, share, COST, TAX, D_UNITS)
            yrs = E.shape[1] / 252
            fc = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
            row, _ = std.row(fc, E)
            rf = self.ref(bn)
            d = fc - rf['fin']
            row.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=rf['s085'],
                       hold1x=rf['hold1x'], hold2x=rf['hold2x'], hold3x=rf['hold3x'], cover=cover)
            out[bn] = row
        p, r = out.get('dev250_path'), out.get('real_ndx_86_14')
        out['HEADLINE_MS1'] = p['cagr'] if p else None
        out['FLOOR_MS1'] = min(p['cagr'], r['cagr']) if (p and r) else None
        return out
