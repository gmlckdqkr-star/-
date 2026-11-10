# data_cut : 2014-12-31 까지의 자료 (설계용)

`holdout/code/cut_data.py` 가 전체 자료(`holdout/data/us.csv`, `kr.csv`)에서 2014-12-31 뒤의 행과 `*_adj` 열을 지워 만듭니다.
`*_adj`(배당 소급 조정 가격)는 값의 수준에 이후 배당이 섞여 있어 뺐습니다. 수익률 열(`r_cc`, `r_on`, `r_id`, `f_on`, `f_id`)은 하루 단위 비율이라 이후 정보가 들어가지 않습니다.
읽기: `pd.read_csv(path, index_col=0, parse_dates=True)`

## us_le2014.csv (미국 거래일 1985-10-01~2014-12-31, QQQ 열은 1999-03-10 부터)
- `ndx`, `ndx_open`, `ndx_high`, `ndx_low`: 나스닥100 지수. 지수 시가는 체결 가격이 아니므로 밤 수익 계산에 쓰지 않습니다.
- `rf`: 13주 국채 금리(연, 소수). `y10`, `y3m`: 10년·3개월 금리(%).
- `qqq_open`, `qqq_close`, `qqq_high`, `qqq_low`: 분할만 조정한 가격. `spy_open`, `spy_close`: SPY(1993-01-29 부터).
- `r_cc`: 종가→종가 총수익, `r_id`: 시가→종가, `r_on`: 전일 종가→시가(배당은 밤에 귀속), `ndx_cc`: 지수 종가→종가.
- `caldays`: 직전 거래일 이후 달력 일수, `dt_on`, `dt_id`: 밤·낮 구간의 연 환산 길이.
- `f_on = r_on − rf×dt_on`, `f_id = r_id − rf×dt_id`: 선물 방식 초과 수익.

## kr_le2014.csv (한국 거래일 2007-01-29~2014-12-30)
- `k_*`: KODEX 200, `lev_*`: KODEX 레버리지(2010-02-22 부터), `inv_*`: KODEX 인버스. `*_n` = 전일 종가→시가, `*_d` = 시가→종가.
- `kr_n = (lev_n − inv_n)/3`: 코스피200 선물 야간 수익 대용치, `kr_d` 같은 방식의 낮, `kr_spot_n`, `usdkrw`.
- 실제 코스피200 선물 가격은 없습니다. 이 자료로는 한국 구간을 v1 기준(MS1)으로 잴 수 없습니다.
