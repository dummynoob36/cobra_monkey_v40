from v40.reports_v40 import build_daily_eprime_report, build_weekly_report
from v40.config_v40 import DATASET_V40_PATH
import pandas as pd
from datetime import date

df = pd.read_csv(DATASET_V40_PATH)
df["signal_date"] = pd.to_datetime(df["signal_date"])

today = date.today()

print("\n======= MENSAJE DIARIO =======")
d, msg = build_daily_eprime_report(df, today)
print(msg)

print("\n======= MENSAJE SEMANAL =======")
d2, msg2 = build_weekly_report(df, today)
print(msg2)

