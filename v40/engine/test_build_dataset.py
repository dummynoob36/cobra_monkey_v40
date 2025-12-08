from v40.engine.build_dataset_v40 import build_dataset_v40

df, start_date = build_dataset_v40()

print(df.head())
print(f"\nFilas totales: {len(df)}")
print(f"Start date: {start_date}")

