#!/usr/bin/env python3
# MemeCoin Smart Profit Tool
# Accepts natural inputs like '22.3k', '1.3 million', '70b', '$1.3m', '1,300,000'
# Keeps presets and allows custom entries. Outputs human-readable results and saves CSV.
import re, sys, csv
from math import isfinite

MULTS = {
    'k': 1_000,
    'thousand': 1_000,
    'm': 1_000_000,
    'million': 1_000_000,
    'b': 1_000_000_000,
    'bn': 1_000_000_000,
    'billion': 1_000_000_000,
    't': 1_000_000_000_000,
    'trillion': 1_000_000_000_000
}

def parse_money(s):
    if s is None:
        raise ValueError('Empty input')
    s = str(s).strip().lower()
    s = s.replace('$','').replace(',','').strip()
    s = re.sub(r'(\d)\s+([a-z]+)', r'\1\2', s)
    # direct number?
    try:
        return float(s)
    except:
        pass
    m = re.match(r'^([0-9]*\.?[0-9]+)\s*([a-z]+)$', s)
    if m:
        num = float(m.group(1))
        suf = m.group(2)
        if suf in MULTS:
            return num * MULTS[suf]
    words = s.split()
    if len(words) == 2:
        try:
            num = float(words[0])
        except:
            num = None
        suf = words[1]
        if num is not None and suf in MULTS:
            return num * MULTS[suf]
    raise ValueError("Could not parse money/supply value: '%s'" % s)

def human_format(n):
    if n is None or (isinstance(n, float) and (not isfinite(n))):
        return 'N/A'
    n = float(n)
    absn = abs(n)
    if absn >= 1_000_000_000_000:
        return f"${n/1_000_000_000_000:.3f}T"
    if absn >= 1_000_000_000:
        return f"${n/1_000_000_000:.3f}B"
    if absn >= 1_000_000:
        return f"${n/1_000_000:.3f}M"
    if absn >= 1_000:
        return f"${n/1_000:.3f}K"
    return f"${n:.2f}"

def ask(prompt, default=None):
    s = input(prompt + (f" [{default}]" if default is not None else "") + ": ").strip()
    if s == "" and default is not None:
        return default
    return s

def choose_preset(prompt, presets):
    print(prompt)
    for i,(k,v) in enumerate(presets.items(), start=1):
        print(f"  {i}. {k} -> {human_format(v)}")
    choice = input("Choose number or type a custom value (like 22.3k, 1.3million, 70b): ").strip()
    if choice.isdigit():
        idx = int(choice)-1
        if 0 <= idx < len(presets):
            key = list(presets.keys())[idx]
            return presets[key]
    try:
        return parse_money(choice)
    except Exception as e:
        print(f"Could not parse custom value: {e}") 
        return choose_preset(prompt, presets)

def calc(invest, buy_mc, sell_mc, supply):
    if supply <= 0:
        raise ValueError('Supply must be > 0')
    buy_price = buy_mc / supply
    sell_price = sell_mc / supply
    tokens = invest / buy_price if buy_price > 0 else 0.0
    final_value = tokens * sell_price
    profit = final_value - invest
    roi = (profit / invest) * 100 if invest > 0 else float('nan')
    mult = final_value / invest if invest > 0 else float('nan')
    return {
        'buy_price': buy_price,
        'sell_price': sell_price,
        'tokens': tokens,
        'final_value': final_value,
        'profit': profit,
        'roi': roi,
        'mult': mult
    }

def main():
    print('\n=== MemeCoin Smart Profit Tool By Fazal-e-Azeem ===\n')
    try:
        invest_s = ask('Investment amount (e.g. 50, 100, 22.3k)', '100')
        invest = parse_money(invest_s)
    except Exception as e:
        print('Investment parse error:', e); sys.exit(1)

    presets = {
        '1 million': 1_000_000,
        '10 million': 10_000_000,
        '100 million': 100_000_000,
        '1 billion': 1_000_000_000,
        '10 billion': 10_000_000_000,
        '70 billion': 70_000_000_000
    }

    buy_mc = choose_preset('Select market cap WHEN YOU BUY (preset/custom):', presets)
    print('Buy market cap set to:', human_format(buy_mc))

    print('\nEnter target market cap(s). You can enter multiple values separated by commas (e.g. 100m,1b,70b)')
    target_raw = input('Targets: ').strip()
    if not target_raw:
        print('No targets given. Exiting.'); sys.exit(0)
    target_parts = [p.strip() for p in target_raw.split(',') if p.strip()]
    targets = []
    for p in target_parts:
        try:
            if p.isdigit():
                idx = int(p)-1
                if 0 <= idx < len(presets):
                    targets.append(list(presets.values())[idx])
                    continue
            matched = False
            for k,v in presets.items():
                if p.lower() in k:
                    targets.append(v); matched=True; break
            if matched: continue
            targets.append(parse_money(p))
        except Exception as e:
            print(f"Skipping target '{p}': {e}")

    total_supply_s = ask('Total token supply (e.g. 1000000000 or 1b)', '1000000000')
    try:
        total_supply = parse_money(total_supply_s)
    except Exception as e:
        print('Supply parse error:', e); sys.exit(1)

    circ_choice = input('Do you want to specify circulating supply? (y/n) [n]: ').strip().lower()
    if circ_choice == 'y':
        circ_s = input('Enter circulating supply (number or percent like 20%): ').strip()
        if circ_s.endswith('%'):
            pct = float(circ_s[:-1])
            circ_supply = total_supply * pct/100.0
        else:
            circ_supply = parse_money(circ_s)
    else:
        pct = input('Enter circulating supply percent of total (e.g. 20 for 20%) [100]: ').strip()
        pct = float(pct) if pct else 100.0
        circ_supply = total_supply * pct/100.0

    basis_choice = input('Basis? 1) circulating 2) fdv 3) both [3]: ').strip()
    if basis_choice == '1':
        basis = 'circulating'
    elif basis_choice == '2':
        basis = 'fdv'
    else:
        basis = 'both'

    results = []
    for t in targets:
        if basis in ('circulating','both'):
            r = calc(invest, buy_mc, t, circ_supply)
            r['scenario'] = 'Circulating'
            r['buy_mc'] = buy_mc; r['sell_mc'] = t; r['supply_used'] = circ_supply
            results.append(r)
        if basis in ('fdv','both'):
            r = calc(invest, buy_mc, t, total_supply)
            r['scenario'] = 'FDV'
            r['buy_mc'] = buy_mc; r['sell_mc'] = t; r['supply_used'] = total_supply
            results.append(r)

    print('\n--- Results ---\n')
    for r in results:
        print(f"Scenario: {r['scenario']}")
        print(f"Buy MC: {human_format(r['buy_mc'])}   Sell MC: {human_format(r['sell_mc'])}")
        print(f"Supply used: {int(r['supply_used']):,}")
        print(f"Buy price: {human_format(r['buy_price'])}   Sell price: {human_format(r['sell_price'])}")
        print(f"Tokens acquired: {r['tokens']:,.4f}")
        print(f"Final value: {human_format(r['final_value'])}   Profit: {human_format(r['profit'])}")
        print(f"ROI: {r['roi']:.2f}%   Multiplier: {r['mult']:.2f}x\n")

    csvfile = 'memecoin_smart_results.csv'
    keys = ['scenario','buy_mc','sell_mc','supply_used','buy_price','sell_price','tokens','final_value','profit','roi','mult']
    with open(csvfile, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k) for k in keys}
            writer.writerow(row)
    print(f"Results saved to {csvfile}")


if __name__ == '__main__':
    main()