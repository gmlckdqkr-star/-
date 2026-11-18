import sys, os, json, shutil, hashlib
sys.path.insert(0, '/tmp/df5d_merge')
import pandas as pd, numpy as np
from chk import check, load

BASE = '/mnt/project-files/research/df5/data'
C = BASE + '/clean'
proj = json.load(open(C + '/proj/MANIFEST_proj.json'))
pub = json.load(open(C + '/pub/_manifest_pub.json'))

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

# ---------------- decisions ----------------
# rule: 1) longer daily USD total-return coverage, 2) ACTUAL over PROXY, 3) tie -> project build (NYSE calendar)
SPEC = {
 'GOLD':  dict(origin='proj', etf='GLD', label='PROXY->ACTUAL',
   segs=[('1985-01-03','PROXY','spot XAU/USD daily close (Twelve Data; bullion, price = TR, no fee)'),
         ('2004-11-19','ACTUAL','GLD adjclose total return')],
   reason='proj covers 1985-01 vs pub 2000-08 (pub pre-GLD piece is COMEX front futures with roll jumps). Longer coverage wins.',
   ko_src='금 현물 XAU/USD (Twelve Data) → GLD'),
 'LTT':   dict(origin='proj', etf='TLT', label='PROXY->ACTUAL',
   segs=[('1977-02-16','PROXY','synthetic 25y constant-maturity par bond TR from daily ^TYX 30y yield'),
         ('2002-07-31','ACTUAL','TLT adjclose total return')],
   reason='proj covers 1977-02 vs pub 1986-05; proj proxy is vol-matched to TLT (pub VUSTX is an actual fund but shorter duration, vol 11.5% vs TLT 13.8%). Longer coverage wins; pub kept as alternative.',
   ko_src='^TYX 30년 금리로 만든 25년 만기 채권 TR → TLT'),
 'DEVX':  dict(origin='proj', etf='EFA', label='PROXY->ACTUAL',
   segs=[('1990-07-02','PROXY','Ken French Developed ex US market (Mkt-RF+RF) USD, local-close timing'),
         ('2001-08-28','ACTUAL','EFA adjclose total return')],
   reason='same construction and start in both; proj chosen because off-NYSE KF dates are compounded into the next NYSE day (pub keeps KF dates incl. some US holidays, 6267 vs 6175 rows).',
   ko_src='Ken French 선진국(미국 제외) 시장 USD → EFA'),
 'EM':    dict(origin='pub', etf='EEM', label='PROXY->ACTUAL',
   segs=[('1994-05-05','PROXY','VEIEX (Vanguard EM index fund) NAV total return; an actual fund, not the ETF'),
         ('2003-04-15','ACTUAL','EEM adjclose total return')],
   reason='pub covers 1994-05 vs proj 2003-04 (EEM only). Longer coverage wins. VEIEX NAV is less volatile than EEM (fair-value pricing, timing).',
   ko_src='VEIEX 인덱스펀드 NAV TR → EEM'),
 'CMDTY': dict(origin='proj', etf='DBC', label='ACTUAL',
   segs=[('2006-02-07','ACTUAL','DBC adjclose total return (futures + collateral yield)')],
   reason='pub is longer (1984) but its pre-2006-07 piece is the PRICE-ONLY S&P GSCI spot index (no roll, no collateral; runs about 7.6%/yr ahead of GSG), so it is not total return. Total-return coverage: proj DBC 2006-02-07 vs pub GSG 2006-07-24, and DBC is ACTUAL. pub spot splice kept as alternative.',
   ko_src='DBC 실제 TR'),
 'USD':   dict(origin='pub', etf='UUP', label='PROXY->ACTUAL',
   segs=[('1982-02-01','PROXY','synthetic fully collateralized USDX futures: DXY spot change + KF RF + DXY-weighted 3m rate differential'),
         ('2007-03-02','ACTUAL','UUP adjclose total return')],
   reason='pub covers 1982-02 vs proj 2007-03 (UUP only); the pub proxy includes carry and collateral, so it is a total-return proxy. Longer coverage wins.',
   ko_src='달러인덱스 현물+T-bill+금리차 캐리 합성 선물 → UUP'),
 'LOWVOL':dict(origin='pub', etf='SPLV', label='ACTUAL',
   segs=[('2011-05-06','ACTUAL','SPLV adjclose total return')],
   reason='both ACTUAL; pub SPLV starts 2011-05-06 vs proj USMV 2011-10-21. Longer coverage wins (ETF changes from USMV to SPLV; SPLV-USMV daily corr 0.905 per pub).',
   ko_src='SPLV 실제 TR (2011년부터만)'),
 'SMALL': dict(origin='proj', etf='IWM', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French size quintile 2 (Qnt 2) VW TR'),
         ('2000-05-30','ACTUAL','IWM adjclose total return')],
   reason='same construction, start and n in both; tie -> proj (project jp/md SMALL).',
   ko_src='Ken French 규모 2분위 VW → IWM'),
 'VALUE': dict(origin='proj', etf='IWD', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','0.5*KF BIG HiBM + 0.5*KF ME2 BM2 VW TR'),
         ('2000-05-30','ACTUAL','IWD adjclose total return')],
   reason='same construction, start and n in both; tie -> proj.',
   ko_src='Ken French 대형 가치/중립 혼합 → IWD'),
 'MOM':   dict(origin='proj', etf='MTUM', label='PROXY->ACTUAL',
   segs=[('1926-11-03','PROXY','Ken French BIG HiPRIOR (6 ME x Prior 12-2) VW TR'),
         ('2013-04-19','ACTUAL','MTUM adjclose total return')],
   reason='same construction, start and n in both; tie -> proj.',
   ko_src='Ken French 대형 고모멘텀 VW → MTUM'),
 'SOX':   dict(origin='proj', etf='SOXX', label='PROXY->PRICE-ONLY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 49-industry Chips VW TR (unscaled; broader than semis)'),
         ('1994-05-05','PRICE-ONLY','^SOX index close (no dividends)'),
         ('2001-07-16','ACTUAL','SOXX adjclose total return')],
   reason='proj covers 1926 vs pub 1985 (FSELX active fund). Longer coverage wins; the 1994-2014 pieces are the same (^SOX then SOXX). Chips is less volatile than ^SOX (37% vs 48% in 1994-2001); project x1.16 scaling NOT applied.',
   ko_src='KF 반도체(Chips) → ^SOX 지수(가격만) → SOXX'),
 'TECH':  dict(origin='proj', etf='XLK', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry BusEq VW TR'), ('1998-12-23','ACTUAL','XLK adjclose total return')],
   reason='same construction, start and n in both; tie -> proj.', ko_src='KF BusEq 산업 → XLK'),
 'ENER':  dict(origin='proj', etf='XLE', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Enrgy VW TR'), ('1998-12-23','ACTUAL','XLE adjclose total return')],
   reason='same construction, start and n in both; tie -> proj.', ko_src='KF Enrgy 산업 → XLE'),
 'HLTH':  dict(origin='proj', etf='XLV', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Hlth VW TR'), ('2002-01-02','ACTUAL','XLV adjclose total return')],
   reason='QUALITY OVERRIDE of the ACTUAL-over-PROXY tiebreak: same coverage (1926); pub splices XLV from 1998-12-23 but the 1998-12..2001 XLV prints are thinly traded (median 6-16k shares/day) and track the sector poorly (yearly corr 0.28-0.72), so the proj KF-through-2001 version is kept. pub version is the alternative.',
   ko_src='KF Hlth 산업 → XLV(2002~)'),
 'UTIL':  dict(origin='proj', etf='XLU', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Utils VW TR'), ('2002-01-02','ACTUAL','XLU adjclose total return')],
   reason='QUALITY OVERRIDE (as HLTH): early XLU prints 1998-12..2001 track poorly (yearly corr 0.57-0.72); proj keeps KF through 2001. pub (XLU from 1998-12-23) is the alternative.',
   ko_src='KF Utils 산업 → XLU(2002~)'),
 'STAP':  dict(origin='proj', etf='XLP', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry NoDur VW TR'), ('2002-01-02','ACTUAL','XLP adjclose total return')],
   reason='QUALITY OVERRIDE (as HLTH): early XLP prints 1998-12..2001 track poorly (yearly corr 0.57-0.73); proj keeps KF through 2001. pub (XLP from 1998-12-23) is the alternative.',
   ko_src='KF NoDur 산업 → XLP(2002~)'),
 'FIN':   dict(origin='proj', etf='XLF', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Money VW TR'), ('1998-12-23','ACTUAL','XLF adjclose total return')],
   reason='project only.', ko_src='KF Money 산업 → XLF'),
 'MANU':  dict(origin='proj', etf='XLI', label='PROXY->ACTUAL',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Manuf VW TR'), ('2002-01-02','ACTUAL','XLI adjclose total return')],
   reason='project only (early XLI thinly traded, so KF kept through 2001).', ko_src='KF Manuf 산업 → XLI(2002~)'),
 'SHOP':  dict(origin='proj', etf='XRT (not spliced)', label='PROXY',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Shops VW TR')],
   reason='project only. XRT is equal-weight (beta 1.30 to Shops), so not spliced.', ko_src='KF Shops 산업 (ETF 미연결)'),
 'TELE':  dict(origin='proj', etf='none (XLC 2018)', label='PROXY',
   segs=[('1926-07-01','PROXY','Ken French 12-industry Telcm VW TR')],
   reason='project only. No telecom ETF in the data before 2015.', ko_src='KF Telcm 산업 (ETF 없음)'),
 'DIV':   dict(origin='pub', etf='SCHD', label='PROXY->ACTUAL',
   segs=[('1988-03-22','PROXY','VEIPX (Vanguard Equity Income, active fund) close + distributions TR'),
         ('2011-10-21','ACTUAL','SCHD adjclose total return')],
   reason='public only (project has no dividend series).', ko_src='VEIPX 배당 액티브펀드 TR → SCHD'),
 'RF':    dict(origin='pub', etf='BIL (cash)', label='ACTUAL',
   segs=[('1926-07-01','ACTUAL','Ken French daily RF (1-month T-bill)')],
   reason='public only. Cash / financing rate for synthetic leverage.', ko_src='Ken French 일별 무위험수익률(T-bill)'),
}

ALTS_PUB = {'GOLD':['GOLD_FFM'], 'CMDTY':['CMDTY_SPOT','CMDTY_WTI'], 'USD':['USD_SPOT'], 'STAP':['STAP_KF'], 'HLTH':['HLTH_KF'],
            'UTIL':['UTIL_KF'], 'ENER':['ENER_KF'], 'TECH':['TECH_KF'], 'DEVX':['DEVX_KF'], 'SMALL':['SMALL_KF'],
            'VALUE':['VALUE_KF'], 'MOM':['MOM_KF'], 'SOX':['SOX_KF']}
PUB_ONLY_VARIANTS = {k for v in ALTS_PUB.values() for k in v}

def brief(p):
    c = check(p)
    return {k: c[k] for k in ('start', 'end', 'n', 'ann_vol')}, c

manifest = {'_meta': {
    'built': '2026-11-18', 'builder': 'df5 merge step (/tmp/df5d_merge/merge.py); inputs clean/proj/MANIFEST_proj.json + clean/pub/_manifest_pub.json',
    'cut': '2014-12-31 (every series truncated on load; no 2015+ value read into the outputs)',
    'format': "clean/<ID>.csv: columns date,r; r = simple daily total return in decimal, USD; DatetimeIndex",
    'selection_rule': '1) longer daily USD total-return coverage (price-only pieces do not count), 2) ACTUAL over PROXY, 3) tie -> project build (NYSE calendar). Overrides are marked QUALITY OVERRIDE in choice_reason.',
    'calendar_note': 'KF-based series start 1926 and include NYSE Saturday sessions before 1952-05; the only gap > 5 weekdays is the 1933-03-03..1933-03-15 bank holiday (market closed, not missing data). research/data/INDEX.md restricts pre-1970 rows for some threads.',
    'origin_copies': 'clean/proj/<ID>.csv and clean/pub/<ID>.csv are the per-builder copies; clean/<ID>.csv is the chosen series (byte copy of its origin file).',
    'license': 'Ken French data: internal research use, no redistribution; Yahoo/Twelve Data/FRED/Bundesbank: internal use',
}, 'assets': {}}

rows = []
for aid, s in SPEC.items():
    origin = s['origin']
    ofile = f"{C}/{origin}/{aid}.csv"
    top = f"{C}/{aid}.csv"
    oc = check(ofile)
    assert oc['n_post2014_in_file'] == 0 and oc['max_nan_run'] == 0, (aid, oc)
    # place chosen series at clean/<ID>.csv (byte copy). proj files at top level are already identical to clean/proj.
    if origin == 'pub' or not os.path.exists(top):
        shutil.copyfile(ofile, top)
    assert sha(top) == sha(ofile), aid
    ser, _ = load(top)
    idx = ser.index
    segs = []
    for j, (frm, typ, lab) in enumerate(s['segs']):
        f = pd.Timestamp(frm)
        assert f in idx, (aid, frm)
        if j + 1 < len(s['segs']):
            nxt = pd.Timestamp(s['segs'][j + 1][0]); to = idx[idx < nxt][-1]
        else:
            to = idx[-1]
        segs.append({'from': frm, 'to': str(to.date()), 'type': typ, 'source': lab, 'n': int(((idx >= f) & (idx <= to)).sum())})
    assert segs[0]['from'] == str(idx[0].date()), aid
    act = [g['from'] for g in segs if g['type'] == 'ACTUAL']
    tr_from = next((g['from'] for g in segs if g['type'] != 'PRICE-ONLY'), None)
    if origin == 'proj':
        e = proj[aid]; src = e['source']; okind = e['kind']; onotes = e.get('notes', '')
    else:
        e = pub[aid]; src = [g['source'] for g in e['segments']]; okind = e['kind']; onotes = e.get('notes', '')
    alts = []
    other = 'pub' if origin == 'proj' else 'proj'
    of = f"{C}/{other}/{aid}.csv"
    if os.path.exists(of):
        b, c = brief(of); assert c['n_post2014_in_file'] == 0
        oe = (pub if other == 'pub' else proj)[aid]
        alts.append({'role': 'other builder, same ID (not chosen)', 'origin': other, 'file': of, 'kind': oe['kind'], **b})
    if aid in proj and origin != 'proj':
        pass
    for nm, a in (proj.get(aid, {}).get('alt_files') or {}).items():
        b, c = brief(a['file']); assert c['n_post2014_in_file'] == 0
        alts.append({'role': f'proj unspliced variant: {nm}', 'origin': 'proj', 'file': a['file'], **b})
    for v in ALTS_PUB.get(aid, []):
        pf = f"{C}/pub/{v}.csv"; b, c = brief(pf); assert c['n_post2014_in_file'] == 0
        alts.append({'role': f'pub variant {v}', 'origin': 'pub', 'file': pf, 'kind': pub[v]['kind'], 'notes': pub[v].get('notes', ''), **b})
    if aid == 'USD':
        alts.append({'role': 'pub auxiliary (daily carry used in the USD proxy)', 'origin': 'pub', 'file': f"{C}/pub/_aux_USD_carry.csv"})
    manifest['assets'][aid] = {
        'id': aid, 'etf': s['etf'], 'file': top, 'origin': origin, 'origin_file': ofile,
        'label': s['label'], 'kind': okind, 'source': src, 'segments': segs,
        'total_return_from': tr_from, 'actual_etf_from': act[-1] if act else None,
        'start': oc['start'], 'end': oc['end'], 'n': oc['n'], 'ann_vol': oc['ann_vol'],
        'daily': True, 'usd': True, 'sha256': sha(top),
        'choice_reason': s['reason'], 'notes': onotes, 'alternatives': alts,
        'ko_src': s['ko_src'],
    }

manifest['missing'] = [
 'GOLD before 1985-01-03: not in the chosen series. pub GOLD_FFM (Frankfurt fixing in USD, price-only, German business days) covers 1968-06-19..1998-12-30 as an unspliced alternative.',
 'LTT before 1977-02-16: none (^TYX starts 1977).',
 'DEVX before 1990-07: no daily USD series; would need the project PX1/AT2/GX1 local indices plus FX (raw/pub has FRED DEX* and Bundesbank DEM).',
 'EM before 1994-05: Ken French Emerging is monthly only (from 1989-07).',
 'CMDTY total return before 2006-02-07: only price-only S&P GSCI spot (1984) and WTI spot (1986) exist, as alternatives; no free GSCI ER/TR index found.',
 'USD before 1982-02: only DXY spot price (USD_SPOT, from 1971) without carry.',
 'LOWVOL before 2011-05: Ken French variance portfolios are monthly only.',
 'DIV before 1988-03: Ken French D/P portfolios are monthly only.',
 'Short actual-ETF history: MTUM (2013-04), SPLV (2011-05), SCHD (2011-10).',
 'TELE has no telecom ETF before 2015 and SHOP is not spliced to XRT: both are KF proxy only.',
]

with open(BASE + '/MANIFEST.json', 'w') as f:
    json.dump(manifest, f, indent=1, ensure_ascii=False)

# ------------- verification of the chosen clean csvs (print start, end, n, ann vol only + pass flags) -------------
BAND = {'RF': (0.0, 0.01), 'USD': (0.04, 0.15), 'LTT': (0.06, 0.25), 'GOLD': (0.08, 0.35), 'LOWVOL': (0.05, 0.20),
        'SOX': (0.20, 0.70), 'EM': (0.12, 0.45), 'CMDTY': (0.10, 0.45), 'DIV': (0.08, 0.30)}
print(f"{'ID':7}{'origin':7}{'start':11} {'end':11} {'n':>6} {'ann_vol':>8}  checks")
allok = True
for aid in SPEC:
    p = manifest['assets'][aid]['file']
    c = check(p)
    lo, hi = BAND.get(aid, (0.08, 0.45))
    ok = dict(loads=c['cols'] == ['r'] and c['index_is_datetime'], no_post2014=c['n_post2014_in_file'] == 0 and c['end'] <= '2014-12-31',
              nan_run_le5=c['max_nan_run'] <= 5, vol_plausible=lo <= c['ann_vol'] <= hi, no_dups=c['dup_dates'] == 0 and c['monotonic'],
              r_gt_minus1=c['n_le_minus1'] == 0)
    allok &= all(ok.values())
    manifest['assets'][aid]['checks'] = {**ok, 'max_nan_run': c['max_nan_run'], 'vol_band': [lo, hi], 'gaps_gt5_weekdays': c.get('gaps_gt5_weekdays', [])}
    print(f"{aid:7}{manifest['assets'][aid]['origin']:7}{c['start']:11} {c['end']:11} {c['n']:6d} {c['ann_vol']:8.4f}  {'PASS' if all(ok.values()) else 'FAIL '+str(ok)}")
print('ALL PASS' if allok else 'SOME FAIL')
with open(BASE + '/MANIFEST.json', 'w') as f:
    json.dump(manifest, f, indent=1, ensure_ascii=False)
