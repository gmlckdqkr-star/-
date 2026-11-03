"""Out-of-process plugin runner.

A plugin never runs in the lab / judge process. Each worker process starts one helper interpreter (`zygote`, a fresh
`python3 -I` that imports only numpy, pandas and a few pure stdlib modules: no lab, no blackbox, no panel in memory).
For every plugin session the zygote forks a child. The child
  - reads its request from a pipe (the zygote itself never reads a request, so its memory holds no price data),
  - closes every fd but its two pipes and sets RLIMIT_NOFILE = 2 (no new file, socket or /proc handle can be opened),
  - drops to uid/gid nobody when started as root (cannot signal or ptrace lab), RLIMIT_NPROC = 0 (no fork), and
    RLIMIT_CPU as a backstop,
  - exec's the plugin source in a fresh namespace and answers frame by frame, then exits.
So a plugin sees only the frames it is sent, cannot read the panel or any file, cannot patch lab's checks, and keeps
no state between sessions (each session is a new fork of the pristine zygote).

A session can take several frames, but only frames that EXTEND the previous one (same rows plus later rows): state
the plugin keeps inside a session then only carries rows it has already been given. A frame that does not extend the
previous one closes the session and starts a new fork. The truncation tests use this: they send the cuts in
increasing order and the full frame last, so a plugin cannot replay a stored full-length answer on a shorter cut.

Wire format: length-prefixed JSON headers and raw little-endian float64 / int64 buffers (never pickle: the child's
answer is untrusted and is only parsed as JSON + numbers).
"""
import json, os, select, signal, socket, struct, subprocess, sys, time
import numpy as np, pandas as pd

TIMEOUT = float(os.environ.get('LAB_PLUGIN_TIMEOUT', '120'))     # seconds per frame (wall)
CPU_LIMIT = int(os.environ.get('LAB_PLUGIN_CPU', '1800'))        # seconds of CPU per session (backstop)


class PluginError(ValueError):
    pass


ZYGOTE = r'''
import os, sys, json, struct, resource, signal
os.environ.clear()
import math, itertools, functools, collections, statistics, bisect, heapq, operator, re
import numpy as np, pandas as pd
import numpy.lib.stride_tricks
try:
    pd.set_option('compute.use_numexpr', False)
    pd.set_option('compute.use_bottleneck', False)
except Exception:
    pass
pd.DataFrame({'a': [1.0, 2.0]}, index=pd.bdate_range('2000-01-03', periods=2)).rolling(2).mean().ewm(span=2).mean()
_ = repr(pd.DataFrame({'a': [1.0]}))
CTL = int(sys.argv[1]); CPU = int(sys.argv[2])


def rd(fd, n):
    b = bytearray()
    while len(b) < n:
        x = os.read(fd, n - len(b))
        if not x:
            raise EOFError
        b += x
    return bytes(b)


def wr(fd, b):
    v = memoryview(b)
    while len(v):
        v = v[os.write(fd, v):]


def msg_in():
    n, = struct.unpack('<Q', rd(0, 8))
    h = json.loads(rd(0, n).decode())
    bufs = [rd(0, k) for k in h.pop('_bufs', [])]
    return h, bufs


def msg_out(h, bufs=()):
    h = dict(h, _bufs=[len(b) for b in bufs])
    j = json.dumps(h).encode()
    wr(1, struct.pack('<Q', len(j)) + j + b''.join(bufs))


def child():
    os.close(CTL)
    for fd in os.listdir('/proc/self/fd'):
        if int(fd) > 1:
            try:
                os.close(int(fd))
            except OSError:
                pass
    resource.setrlimit(resource.RLIMIT_NOFILE, (2, 2))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU, CPU))
    if os.getuid() == 0:
        try:
            os.setgroups([])
            os.setgid(65534)
            os.setuid(65534)
        except Exception:
            pass
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    except Exception:
        pass
    h, _ = msg_in()
    try:
        ns = {'__name__': 'lab_plugin', '__builtins__': __builtins__}
        exec(compile(h['src'], h['file'], 'exec'), ns)
        fn = ns.get(h['func'])
        if not callable(fn):
            raise ValueError(f"plugin has no function {h['func']}")
        msg_out({'ok': True})
    except BaseException as e:
        msg_out({'ok': False, 'err': f'{type(e).__name__}: {e}'[:400]})
        os._exit(0)
    sleeves, params, allowed = h['sleeves'], h['params'], set(h['allowed'])
    while True:
        f, bufs = msg_in()
        if f.get('end'):
            os._exit(0)
        try:
            idx = pd.DatetimeIndex(np.frombuffer(bufs[0], '<i8').astype('datetime64[ns]'))
            X = np.frombuffer(bufs[1], '<f8').reshape(len(idx), len(f['cols'])).copy()
            F = pd.DataFrame(X, index=idx, columns=f['cols'])
            out = fn(F, list(sleeves), json.loads(json.dumps(params)))
            if not isinstance(out, pd.DataFrame):
                raise TypeError('plugin must return a pandas DataFrame of weights')
            if len(out) != len(idx) or not out.index.equals(idx):
                raise ValueError('plugin weights must have exactly the index of F')
            cols = [str(c) for c in out.columns]
            bad = sorted(set(cols) - allowed)
            if bad or len(set(cols)) != len(cols):
                raise ValueError(f'plugin returned columns {bad or cols} outside sleeves + CASH {sorted(allowed)}')
            V = np.ascontiguousarray(out.values.astype('<f8'))
            msg_out({'ok': True, 'cols': cols}, [V.tobytes()])
        except BaseException as e:
            msg_out({'ok': False, 'err': f'{type(e).__name__}: {e}'[:400]})
            os._exit(0)


while True:
    b = os.read(CTL, 1)
    if not b:
        os._exit(0)
    pid = os.fork()
    if pid == 0:
        try:
            child()
        finally:
            os._exit(0)
    os.write(CTL, b'P' + struct.pack('<q', pid))
    _, st = os.waitpid(pid, 0)
    os.write(CTL, b'X' + struct.pack('<q', st))
'''


def _pack(h, bufs=()):
    h = dict(h, _bufs=[len(b) for b in bufs])
    j = json.dumps(h).encode()
    return struct.pack('<Q', len(j)) + j + b''.join(bufs)


class _Zygote:
    def __init__(self):
        a, b = socket.socketpair()
        env = {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
               'NUMEXPR_MAX_THREADS': '1', 'PATH': '/usr/bin:/bin'}
        self.p = subprocess.Popen([sys.executable, '-I', '-B', '-c', ZYGOTE, str(b.fileno()), str(CPU_LIMIT)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  pass_fds=(b.fileno(),), env=env, cwd='/', close_fds=True)
        b.close()
        self.ctl = a
        self.pid = os.getpid()
        self.out = self.p.stdout.fileno()
        os.set_blocking(self.out, False)
        self.buf = bytearray()
        self.child = None
        self.pending = False

    def alive(self):
        return self.p.poll() is None

    # --- session control
    def start(self):
        if self.pending:                         # exit report of the previous child (its teardown overlapped our work)
            self.pending = False
            self.child = -1
            self._finish()
            if not self.alive():
                raise PluginError('plugin runner died')
        self.buf.clear()
        self.ctl.sendall(b'G')
        b = self._ctl_read(9)
        if b[:1] != b'P':
            raise PluginError('plugin runner: bad control message')
        self.child = struct.unpack('<q', b[1:])[0]

    def _ctl_read(self, n, timeout=None):
        self.ctl.settimeout(TIMEOUT if timeout is None else timeout)
        b = b''
        while len(b) < n:
            x = self.ctl.recv(n - len(b))
            if not x:
                raise PluginError('plugin runner died')
            b += x
        return b

    def send(self, data):
        w = self.p.stdin
        w.write(data); w.flush()

    def recv(self, timeout=None):
        """One message from the child; raises PluginError if the child exits or times out first."""
        timeout = TIMEOUT if timeout is None else timeout
        t_end = time.time() + timeout
        while True:
            m = self._try_parse()
            if m is not None:
                return m
            left = t_end - time.time()
            if left <= 0:
                self.kill()
                raise PluginError(f'plugin timed out ({timeout:.0f}s per frame)')
            r, _, _ = select.select([self.out, self.ctl], [], [], left)
            if self.out in r:
                try:
                    x = os.read(self.out, 1 << 20)
                except BlockingIOError:
                    x = b''
                if x:
                    self.buf += x
                    continue
            if self.ctl in r:                     # child exited before a full answer
                self._drain()
                m = self._try_parse()
                self._finish()
                if m is not None:
                    return m
                raise PluginError('plugin process ended without an answer (crashed, killed or exited)')

    def _drain(self):
        while True:
            try:
                x = os.read(self.out, 1 << 20)
            except BlockingIOError:
                return
            if not x:
                return
            self.buf += x

    def _try_parse(self):
        b = self.buf
        if len(b) < 8:
            return None
        n, = struct.unpack('<Q', b[:8])
        if n > 1 << 24:
            raise PluginError('plugin runner: bad answer header')
        if len(b) < 8 + n:
            return None
        h = json.loads(bytes(b[8:8 + n]).decode())
        sizes = h.pop('_bufs', [])
        if not isinstance(sizes, list) or not all(isinstance(s, int) and 0 <= s < 1 << 31 for s in sizes):
            raise PluginError('plugin runner: bad answer header')
        end = 8 + n + sum(sizes)
        if len(b) < end:
            return None
        bufs, o = [], 8 + n
        for s in sizes:
            bufs.append(bytes(b[o:o + s])); o += s
        del b[:end]
        return h, bufs

    def _finish(self):
        """Wait for the zygote's exit report of the current child."""
        if self.child is None:
            return
        try:
            b = self._ctl_read(9, timeout=30)
        except Exception:
            b = b''
        self.child = None
        self._drain(); self.buf.clear()
        if b[:1] != b'X':
            self.close()

    def end(self):
        if self.child is None:
            return
        try:
            self.send(_pack({'end': True}))
        except Exception:
            self._finish()
            return
        self.child = None; self.pending = True   # read its exit report at the next start()

    def kill(self):
        if self.child is not None:
            try:
                os.kill(self.child, signal.SIGKILL)
            except Exception:
                pass
            self._finish()

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass
        self.child = None


_Z = {}


def _zygote():
    z = _Z.get('z')
    if z is None or z.pid != os.getpid() or not z.alive():
        if z is not None and z.pid == os.getpid():
            z.close()
        z = _Z['z'] = _Zygote()
    return z


class Session:
    """Plugin calls on one plugin (src, func, sleeves, params). Frames must extend each other; otherwise a fresh child
    is forked. Use as a context manager (or call close())."""

    def __init__(self, src, func, file, sleeves, params, allowed):
        self.h = dict(src=src, func=func, file=file, sleeves=list(sleeves), params=params, allowed=sorted(allowed))
        self.z = None
        self.last = None          # (index int64, values) of the previous frame in the open child

    def _open(self):
        self.close()
        z = self.z = _zygote()
        z.start()
        z.send(_pack(self.h))
        h, _ = z.recv()
        if not h.get('ok'):
            z.end(); self.z = None
            raise PluginError(f"plugin: {h.get('err', 'load failed')}")
        self.last = None

    def _extends(self, ix, X, cols):
        if self.z is None or self.last is None or self.z.child is None:
            return False
        pix, pX, pcols = self.last
        n = len(pix)
        return (cols == pcols and len(ix) >= n and np.array_equal(ix[:n], pix)
                and np.array_equal(X[:n], pX, equal_nan=True))

    def call(self, F):
        ix = np.ascontiguousarray(F.index.values.astype('datetime64[ns]').astype('<i8'))
        X = np.ascontiguousarray(F.values.astype('<f8'))
        cols = [str(c) for c in F.columns]
        if not self._extends(ix, X, cols):
            self._open()
        z = self.z
        try:
            z.send(_pack({'cols': cols}, [ix.tobytes(), X.tobytes()]))
            h, bufs = z.recv()
        except PluginError:
            self.z = None; self.last = None
            raise
        except (BrokenPipeError, OSError) as e:
            self.z = None; self.last = None
            raise PluginError(f'plugin process ended: {e}')
        if not h.get('ok'):
            z._finish(); self.z = None; self.last = None
            raise PluginError(f"plugin: {h.get('err', 'failed')}")
        out_cols = h.get('cols')
        if not isinstance(out_cols, list) or not all(isinstance(c, str) for c in out_cols) \
                or set(out_cols) - set(self.h['allowed']) or len(bufs) != 1 \
                or len(bufs[0]) != 8 * len(ix) * len(out_cols):
            self.close()
            raise PluginError('plugin answer has a bad shape')
        self.last = (ix, X, cols)
        return out_cols, np.frombuffer(bufs[0], '<f8').reshape(len(ix), len(out_cols))

    def close(self):
        if self.z is not None:
            try:
                self.z.end()
            except Exception:
                pass
        self.z = None; self.last = None

    def __enter__(self):
        return self

    def __exit__(self, *e):
        self.close()
