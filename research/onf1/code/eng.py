"""Independent event-ordered engine for the overnight-futures strategy family (v9..v13 / PRESET_A).
Written from the rule text in the uploaded reports (not from the original research engine, which was not uploaded).

Timeline per calendar date D (UTC order):  KR open -> KR close -> US open -> US close
  KR open  D : close the KR night position entered at the previous KR close (E1)
  KR close D : enter KR night position  N = Lk[D] * bm * E               (E2)
  US open  D : book overnight P&L, cut to the day target stored at the previous US close (reduce only)   (E4)
  US close D : book intraday P&L, snapshot (cooldown, peak), set night target N = Ln[D] * bm * E, store Ld[D] * bm   (E3)
Leverage = futures notional / equity. P&L of a held segment = notional at entry * futures excess return of the segment.
Tax: 11% of positive calendar-year derivatives P&L (after costs), no carry-forward; paid on the first row of the next year.
Cash interest: equity * max(rf - cash_spread, 0) per calendar day, taxed 15.4% (cash_spread=None -> no interest).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
import math
import numpy as np, pandas as pd
from numba import njit

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA
# audit switches (all True = patched behaviour; set False to reproduce the audited snapshot)
FIX = dict(kr_sig_dropna=True, gran_open_unit=True, bond_gap_us=True, bond_at_close=True, sharpe_rows=True)
OPT = dict(bond_brake=True)   # True = bond notional scaled by brake/cooldown b (snapshot behaviour); False = 'always bond_lev x equity' as the v11 report words it


@dataclass
class Cfg:
    us_day_c: float = 0.36; us_day_max: float = 4.0
    us_night_c: float = 0.50; us_night_max: float = 5.0
    kr_c: float = 0.225; kr_max: float = 3.0
    step: float = 0.5
    vol_win: int = 20; kr_vol_win: int = 20
    use_shock_cap: bool = True; shock_cap: float = 1.0
    use_crisis: bool = True; kr_crisis: bool = True
    shock_win: int = 126; shock_pp: float = 1.0; inv_win: int = 378; ma_win: int = 200; band: float = 0.02
    brake_k: float = 2.0; brake_floor: float = 0.2; brake_min: float = 0.2
    cool_loss: float = 0.05; cool_mult: float = 0.3; cool_days: int = 5
    bond_lev: float = 0.0; bond_off_on_shock: bool = False
    # frictions
    c_us: float = 0.000083; c_kr: float = 0.00006
    tax: float = 0.11; cash_spread: float | None = 0.02; int_tax: float = 0.154
    fin_spread: float = 0.0   # futures implied financing above the T-bill rate (project standard MF1: 0.004)
    delay: int = 0            # extra US/KR trading days of signal delay
    use_kr: bool = True
    # contract granularity (None = ideal fractional). unit = notional of 1 contract / starting equity
    unit_us: float | None = None; unit_kr: float | None = None
    night_scale: float = 1.0; day_scale: float = 1.0; kr_scale: float = 1.0   # scenario haircuts on mean (applied by caller)


PRESET_A = Cfg()
V10 = Cfg(us_day_c=0.18, us_day_max=3.0, us_night_c=0.40, us_night_max=4.0, kr_c=0.10, kr_max=2.0,
          cool_loss=0.07, cool_mult=0.5, cool_days=5)
V9 = replace(V10, us_day_c=0.09, us_day_max=1.5)
V11D_NOBOND = Cfg(us_day_c=0.18, us_day_max=3.0, us_night_c=0.30, us_night_max=4.0, kr_c=0.15, kr_max=2.0, vol_win=60,
                  use_shock_cap=False, brake_k=3.0, cool_loss=0.05, cool_mult=0.3, cool_days=3)


def load(ext=False):
    """ext=True: US rows extended to 2026-11-09 (data/us_ext.csv, proxy NDX level; information only)."""
    us = pd.read_csv(DATA + ('us_ext.csv' if ext else 'us.csv'), index_col=0, parse_dates=True)
    kr = pd.read_csv(DATA + 'kr.csv', index_col=0, parse_dates=True)
    return us, kr


def floor_step(x, step):
    x = np.where(np.isfinite(x) & (x > 0), x, 0.0)
    return np.floor(x / step + 1e-9) * step


def us_state(us: pd.DataFrame, cfg: Cfg) -> pd.DataFrame:
    """Signals at each US close (uses data up to and including that close)."""
    d = pd.DataFrame(index=us.index)
    lr = np.log(us.ndx).diff()
    d['sig'] = lr.rolling(cfg.vol_win).std() * math.sqrt(252)
    d['ma'] = us.ndx.rolling(cfg.ma_win).mean()
    inv = ((us.y10 - us.y3m) < 0).astype(float).rolling(cfg.inv_win, min_periods=1).max() > 0
    shock = (us.y10 - us.y10.shift(cfg.shock_win)) > cfg.shock_pp
    alarm = (inv | shock).values
    st = np.zeros(len(us), bool); s = False
    px = us.ndx.values; ma = d.ma.values
    for i in range(len(us)):
        if np.isnan(ma[i]): s = False
        elif px[i] < ma[i] * (1 - cfg.band) and alarm[i]: s = True
        elif px[i] > ma[i] * (1 + cfg.band) or not alarm[i]: s = False
        st[i] = s
    d['inv'] = inv; d['shock'] = shock; d['crisis'] = st
    sig = d.sig.values
    Ld = floor_step(np.minimum(cfg.us_day_max, cfg.us_day_c / sig ** 2), cfg.step)
    Ln = floor_step(np.minimum(cfg.us_night_max, cfg.us_night_c / sig ** 2), cfg.step)
    if cfg.use_shock_cap:
        Ld = np.where(shock.values, np.minimum(Ld, cfg.shock_cap), Ld); Ln = np.where(shock.values, np.minimum(Ln, cfg.shock_cap), Ln)
    if cfg.use_crisis:
        Ld = np.where(st, 0.0, Ld); Ln = np.where(st, 0.0, Ln)
    d['Ld'] = Ld; d['Ln'] = Ln
    return d


def kr_state(kr: pd.DataFrame, usst: pd.DataFrame, cfg: Cfg) -> pd.DataFrame:
    d = pd.DataFrame(index=kr.index)
    if FIX['kr_sig_dropna']:
        px = kr.k_close.dropna()            # sigma from the last n valid closes (same as live realized_vol)
        d['sig'] = (np.log(px).diff().rolling(cfg.kr_vol_win, min_periods=cfg.kr_vol_win).std() * math.sqrt(252)).reindex(kr.index)
    else:
        px = kr.k_close.where(kr.k_close.notna())
        lr = np.log(px).diff()
        d['sig'] = lr.rolling(cfg.kr_vol_win, min_periods=cfg.kr_vol_win).std() * math.sqrt(252)
    # latest US close strictly before the KR date (US close D-1 is 05:00/06:00 KST of D)
    cr = usst.crisis.astype(float).reindex(kr.index - pd.Timedelta(days=1), method='ffill').fillna(0).values > 0.5
    L = floor_step(np.minimum(cfg.kr_max, cfg.kr_c / d.sig.values ** 2), cfg.step)
    if cfg.kr_crisis and cfg.use_crisis: L = np.where(cr, 0.0, L)
    d['Lk'] = L; d['us_crisis'] = cr
    return d


@njit(cache=True)
def _sim(is_us, is_kr, f_on, f_id, kr_n, kr_ok, Ln, Ld, Lk, cash_d, newyear, uus, ukr, gran, bond_r, Lb,
         c_us, c_kr, tax, k, fl, bmin, closs, cmult, cdays, e0, kr_sync, crisis_us, uuo, bond_at_close, bond_brake):
    # kr_sync=True is a DIAGNOSTIC mode (not tradable): the KR night ending at D is sized with the brake/cooldown/crisis
    # state known only after the US close of D-1, i.e. after the KR position should already have been entered.
    T = len(is_us)
    E = e0; peak = e0; snap = e0; cd = 0
    Nus = 0.0; Nkr = 0.0; Nb = 0.0; Ld_store = 0.0; bm_store = 1.0; Lk_store = 0.0
    pnl_y = 0.0
    out = np.empty(T); tov_us = 0.0; tov_kr = 0.0
    leg = np.zeros(6)   # sum of pnl/E fractions: us night, us day, kr, costs, tax, interest
    ncool = 0
    for t in range(T):
        if newyear[t]:
            tx = tax * max(pnl_y, 0.0)
            E -= tx; snap -= tx; peak -= tx; pnl_y = 0.0
            leg[4] -= tx / max(E, 1e-12)
        if cash_d[t] != 0.0:
            x = E * cash_d[t]; E += x; leg[5] += x / max(E, 1e-12)
        if is_kr[t] and kr_sync:
            if Lk_store > 0.0 and not crisis_us[t]:
                b = k * (E / peak - fl) / (1.0 - fl)
                if b > 1.0: b = 1.0
                if b < bmin: b = bmin
                if cd > 0: b *= cmult
                N = Lk_store * b * E
                p = N * kr_n[t]; c = N * (2.0 + kr_n[t]) * c_kr
                leg[2] += p / E; leg[3] -= c / E
                E += p - c; pnl_y += p - c; tov_kr += 2 * N / E
            Lk_store = Lk[t] if kr_ok[t] else 0.0
        elif is_kr[t]:
            if Nkr > 0.0:
                p = Nkr * kr_n[t]; c = Nkr * (1.0 + kr_n[t]) * c_kr
                leg[2] += p / E; leg[3] -= c / E
                E += p - c; pnl_y += p - c; tov_kr += Nkr * (1.0 + kr_n[t]) / E
                Nkr = 0.0
            if kr_ok[t] and Lk[t] > 0.0 and E > 0.0:
                b = k * (E / peak - fl) / (1.0 - fl)
                if b > 1.0: b = 1.0
                if b < bmin: b = bmin
                if cd > 0: b *= cmult
                tgt = Lk[t] * b * E
                if gran: tgt = math.floor(tgt / ukr[t] + 1e-9) * ukr[t]
                c = tgt * c_kr
                leg[3] -= c / E
                E -= c; pnl_y -= c; tov_kr += tgt / E
                Nkr = tgt
        if is_us[t]:
            # ---- US open: overnight P&L, then cut to the stored day target (reduce only)
            p = Nus * f_on[t]
            leg[0] += p / E
            E += p; pnl_y += p
            if Nb != 0.0 and not bond_at_close:
                pb = Nb * bond_r[t]; E += pb; pnl_y += pb
            cur = Nus * (1.0 + f_on[t])
            tgt = Ld_store * bm_store * E
            if gran: tgt = math.floor(tgt / uuo[t] + 1e-9) * uuo[t]      # contract value AT THE OPEN (not the day's close)
            if tgt > cur: tgt = cur
            if tgt < 0.0: tgt = 0.0
            c = abs(cur - tgt) * c_us
            leg[3] -= c / max(E, 1e-12)
            E -= c; pnl_y -= c; tov_us += abs(cur - tgt) / max(E, 1e-12)
            Nday = tgt
            # ---- US close: intraday P&L, snapshot, night target
            p = Nday * f_id[t]
            leg[1] += p / max(E, 1e-12)
            E += p; pnl_y += p
            if Nb != 0.0 and bond_at_close:      # close-to-close bond P&L is only known at the close
                pb = Nb * bond_r[t]; E += pb; pnl_y += pb
            if E < 1e-9: E = 1e-9
            if cd > 0: cd -= 1
            if E / snap - 1.0 < -closs:
                cd = cdays; ncool += 1
            if E > peak: peak = E
            snap = E
            b = k * (E / peak - fl) / (1.0 - fl)
            if b > 1.0: b = 1.0
            if b < bmin: b = bmin
            if cd > 0: b *= cmult
            cur = Nday * (1.0 + f_id[t])
            tgt = Ln[t] * b * E
            if gran: tgt = math.floor(tgt / uus[t] + 1e-9) * uus[t]
            c = abs(cur - tgt) * c_us
            leg[3] -= c / E
            E -= c; pnl_y -= c; tov_us += abs(cur - tgt) / E
            Nus = tgt; Ld_store = Ld[t]; bm_store = b
            Nb = Lb[t] * (b if bond_brake else 1.0) * E
        out[t] = E
    # final liquidation: tax on the open year's P&L
    fin = E - tax * max(pnl_y, 0.0)
    return out, fin, tov_us, tov_kr, leg, ncool


def prepare(us, kr, cfg: Cfg, start='1999-03-10', end=None, scen=None):
    """Build aligned arrays on the union calendar. scen: dict(night=, day=, kr=) multiplicative haircut on the MEAN of each leg."""
    usst = us_state(us, cfg)
    krst = kr_state(kr, usst, cfg)
    if cfg.delay:
        usst[['Ld', 'Ln']] = usst[['Ld', 'Ln']].shift(cfg.delay).fillna(0.0); krst['Lk'] = krst['Lk'].shift(cfg.delay).fillna(0.0)
    u = us.loc[start:end]; kk = kr.loc[start:end]
    idx = u.index.union(kk.index) if cfg.use_kr else u.index
    is_us = np.asarray(idx.isin(u.index), bool); is_kr = np.asarray(idx.isin(kk.index), bool) & bool(cfg.use_kr)
    f_on = (u.f_on - cfg.fin_spread * u.dt_on).reindex(idx).fillna(0.0).values.copy()
    f_id = (u.f_id - cfg.fin_spread * u.dt_id).reindex(idx).fillna(0.0).values.copy()
    krn = kk.kr_n.reindex(idx)
    # entry at KR close D allowed only if the next KR row has a valid night return (missing-data handling)
    kv = kk.kr_n.notna()
    ok_next = kv.shift(-1, fill_value=False).reindex(idx).fillna(False).values.astype(bool) & is_kr
    kr_n = krn.fillna(0.0).values.copy()
    if scen:
        m = is_us & (f_on != 0); f_on[m] -= (1 - scen.get('night', 1.0)) * f_on[m].mean()
        m = is_us & (f_id != 0); f_id[m] -= (1 - scen.get('day', 1.0)) * f_id[m].mean()
        m = is_kr & (kr_n != 0)
        if m.any(): kr_n[m] -= (1 - scen.get('kr', 1.0)) * kr_n[m].mean()
        if 'shift' in scen:   # move a share of the night mean into the day
            m = is_us & (f_on != 0); mu = f_on[m].mean() * scen['shift']; f_on[m] -= mu; f_id[m] += mu
    Ln = usst.Ln.reindex(idx).fillna(0.0).values; Ld = usst.Ld.reindex(idx).fillna(0.0).values
    Lk = krst.Lk.reindex(idx).fillna(0.0).values if cfg.use_kr else np.zeros(len(idx))
    rf = us.rf.reindex(idx, method='ffill').values
    gap = np.r_[1.0, np.diff(idx.values).astype('timedelta64[D]').astype(float)]
    cash_d = np.zeros(len(idx)) if cfg.cash_spread is None else np.maximum(rf - cfg.cash_spread, 0) * gap / 365 * (1 - cfg.int_tax)
    newyear = np.r_[False, np.asarray(idx.year[1:] != idx.year[:-1], bool)]
    lvl = us.ndx.reindex(idx, method='ffill').values; lvl = lvl / lvl[0]
    kl = kr.k_close.reindex(idx, method='ffill').bfill().values; kl = kl / kl[0]
    gran = cfg.unit_us is not None
    uus = (cfg.unit_us or 1.0) * lvl; ukr = (cfg.unit_kr or 1.0) * kl
    # contract unit at the US open = previous close level * (1 + overnight price move); the snapshot used the SAME day's close
    lvl_prev = np.r_[lvl[0], lvl[:-1]]
    r_on_px = us.r_on.reindex(idx).fillna(0.0).values
    uuo = (cfg.unit_us or 1.0) * (lvl_prev * (1.0 + r_on_px) if FIX['gran_open_unit'] else lvl)
    # bond overlay (10y future proxy): -8*dy + (y10-rf)*dt, target set at previous US close
    y = us.y10.reindex(idx).values / 100; yprev = pd.Series(np.where(is_us, y, np.nan)).ffill().shift(1).bfill().values
    gap_b = np.nan_to_num(us.caldays.reindex(idx).values) if FIX['bond_gap_us'] else gap   # carry days since previous US close
    bond_r = np.where(is_us, -8.0 * (y - yprev) + (y - rf) * gap_b / 365, 0.0); bond_r = np.nan_to_num(bond_r)
    sh = usst.shock.reindex(idx).fillna(False).values.astype(bool)
    Lb = np.where(cfg.bond_off_on_shock & sh, 0.0, cfg.bond_lev) * np.ones(len(idx))
    # crisis state at the latest US close strictly before each row's date (for the diagnostic kr_sync mode)
    cu = usst.crisis.astype(float).reindex(idx, method='ffill').shift(1).fillna(0).values > 0.5
    if not (cfg.use_crisis and cfg.kr_crisis): cu = np.zeros(len(idx), bool)
    return dict(crisis_us=cu, idx=idx, is_us=is_us, is_kr=is_kr, f_on=f_on, f_id=f_id, kr_n=kr_n, kr_ok=ok_next, Ln=Ln, Ld=Ld, Lk=Lk,
                cash_d=cash_d, newyear=newyear, uus=uus, ukr=ukr, gran=gran, bond_r=bond_r, Lb=Lb, usst=usst, krst=krst, uuo=uuo)


def run(A, cfg: Cfg, e0=1.0, kr_sync=False):
    out, fin, tu, tk, leg, ncool = _sim(A['is_us'], A['is_kr'], A['f_on'], A['f_id'], A['kr_n'], A['kr_ok'], A['Ln'], A['Ld'], A['Lk'],
                                        A['cash_d'], A['newyear'], A['uus'], A['ukr'], A['gran'], A['bond_r'], A['Lb'],
                                        cfg.c_us, cfg.c_kr, cfg.tax, cfg.brake_k, cfg.brake_floor, cfg.brake_min,
                                        cfg.cool_loss, cfg.cool_mult, cfg.cool_days, e0, kr_sync, A['crisis_us'],
                                        A['uuo'], FIX['bond_at_close'], OPT['bond_brake'])
    eq = pd.Series(out, index=A['idx'])
    return eq, dict(fin=fin, tov_us=tu, tov_kr=tk, leg=leg, ncool=ncool)


def stats(eq: pd.Series, fin=None, e0=1.0):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    end = fin if fin is not None else eq.iloc[-1]
    cagr = (end / e0) ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    r = eq.pct_change().dropna()
    ann = (len(r) / yrs) if FIX['sharpe_rows'] else 252.0
    sh = r.mean() / r.std() * math.sqrt(ann) if r.std() > 0 else float('nan')
    return dict(cagr=cagr, mdd=dd, sharpe=sh, worst_day=r.min(), yrs=yrs, final=end)


def yearly(eq: pd.Series):
    y = eq.groupby(eq.index.year).last(); y0 = pd.concat([pd.Series([1.0]), y]).values
    return pd.Series(y.values / y0[:-1] - 1, index=y.index)


if __name__ == '__main__':
    if os.environ.get('ONF1_ALLOW_HOLDOUT') != '1':
        sys.exit('eng.py self-test prints 1999-2026 performance (post-2014 numbers). Run with ONF1_ALLOW_HOLDOUT=1 from a non-design thread.')
    us, kr = load()
    for nm, cfg in (('PRESET_A', PRESET_A), ('v10', V10), ('v9', V9), ('v11D-nobond', V11D_NOBOND)):
        for lab, c2, st in ((' US+KR(2010-03~) ', cfg, '1999-03-10'), (' US only         ', replace(cfg, use_kr=False), '1999-03-10'), (' US+KR from 2010-03', cfg, '2010-03-02')):
            A = prepare(us, kr, c2, start=st); eq, info = run(A, c2); s = stats(eq, info['fin'])
            print('%-12s %s CAGR %.1f%% MDD %.1f%% Sharpe %.2f worst day %.1f%% tovUS/yr %.0f tovKR/yr %.0f cooldowns %d' % (
                nm, lab, s['cagr'] * 100, s['mdd'] * 100, s['sharpe'], s['worst_day'] * 100, info['tov_us'] / s['yrs'], info['tov_kr'] / s['yrs'], info['ncool']))
