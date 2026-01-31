#!/usr/bin/env python3
import json

data = json.load(open('/Users/donghun/Documents/git_repository/weather_lens/.omc/w4_jeolla.json'))

print(f'Worker: {data["worker"]}')
print(f'Regions: {data["regions"]}')
print(f'Total count: {data["total_count"]}')
print(f'Status: {data["status"]}')
print()

# Distribution by sido
by_sido = {}
for r in data['data']:
    by_sido[r['sido']] = by_sido.get(r['sido'], 0) + 1

print('Distribution by sido:')
for sido, count in sorted(by_sido.items()):
    print(f'  {sido}: {count}')
print()

# Sample data
print('First 5 samples:')
for i, r in enumerate(data['data'][:5]):
    print(f'{i+1}. {r["sido"]} > {r["sigungu"]} > {r["emd"]}')
    print(f'   lat={r["lat"]}, lon={r["lon"]}, elevation={r["elevation"]}')
    print(f'   source: {r["source"]}')
print()

# Source distribution
db_count = sum(1 for r in data['data'] if '_db' in r['source'])
sigungu_count = sum(1 for r in data['data'] if '_sigungu_avg' in r['source'])
print(f'Sources:')
print(f'  From DB: {db_count}')
print(f'  Sigungu avg: {sigungu_count}')
