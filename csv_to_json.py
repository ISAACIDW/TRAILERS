#!/usr/bin/env python3
"""
CSV to JSON Converter for Horizon Trailer Catalog
Converts the CSV catalog into structured JSON format matching the sample schema.
Usage: python3 csv_to_json.py [--all]
"""

import csv
import json
import re
import os
import sys

CSV_PATH = '/tmp/TRAILERS/ok (1).csv'
OUTPUT_DIR = '/tmp/TRAILERS'

def parse_csv_line(line):
    try:
        return next(csv.reader([line]))
    except:
        return line.split(',')

def clean_val(val):
    if not val:
        return ""
    return val.strip().strip('"').strip('$').strip()

def get_csv_val(line, idx=1):
    parts = parse_csv_line(line)
    if len(parts) > idx:
        return clean_val(parts[idx])
    return ""

def parse_product(lines, start_line, end_line, model_prefix="", category="", ptype=""):
    """Parse a product section from CSV lines"""
    result = {
        "id": "",
        "models_and_prices": {},
        "options": {
            "deck": {}, "tongue": {}, "running_gear": {},
            "electrical_and_lighting": {}, "finish": {}, "lift_system": {}
        },
        "model_id": model_prefix,
        "category": category,
        "type": ptype,
        "name": lines[start_line].strip().strip('"').rstrip(','),
        "specifications": {
            "finish": {"paint": ""},
            "tongue": {"jack": "", "safety_chains": "", "winch_plate": "",
                       "storage": "", "coupler": "", "length": "",
                       "spare": "", "type": ""},
            "running_gear": {"suspension": "", "rims": "", "tires": "", "axles": ""},
            "electrical_and_lighting": {"lights": ""},
            "weight_ratings": {"gvwr": ""},
            "chassis": {"main_frame": ""},
            "deck": {"ramps": "", "crossmembers": "", "deck_width": "",
                     "sides": "", "flooring": "", "width_between_fenders": "",
                     "fenders": "", "type": ""}
        }
    }
    
    specs = result["specifications"]
    
    # Parse Models & Prices
    for i in range(start_line, min(start_line + 100, end_line)):
        line = lines[i].strip()
        if not line:
            continue
        parts = parse_csv_line(line)
        
        if line.startswith('"') and model_prefix in line and 'TRAILER' in line.upper():
            model_name = parts[0].strip('"') if parts else ""
            if model_name:
                price = clean_val(parts[1]) if len(parts) > 1 else ""
                msrp = clean_val(parts[2]) if len(parts) > 2 else ""
                result["models_and_prices"][model_name] = {"msrp": msrp, "price": price}
        elif '....' in line and result["models_and_prices"]:
            p_vals = []
            for p in parts:
                p = clean_val(p)
                if p and p.replace(',', '').replace('.', '').isdigit():
                    p_vals.append(p)
            keys = list(result["models_and_prices"].keys())
            if keys and len(p_vals) >= 2:
                result["models_and_prices"][keys[0]]["price"] = p_vals[0]
                result["models_and_prices"][keys[0]]["msrp"] = p_vals[1]
    
    # Parse Standard Features
    in_features = False
    for i in range(start_line, end_line):
        line = lines[i].strip()
        if not line:
            continue
        if 'STANDARD FEATURES' in line.upper():
            in_features = True
            continue
        if line.startswith('OPTIONS') and 'STANDARD' not in line.upper():
            break
        if not in_features:
            continue
        
        # Weight
        if line.startswith('GVWR:'):
            specs["weight_ratings"]["gvwr"] = get_csv_val(line)
        # Tongue
        if line.startswith('TONGUE:') and 'I-Beam' in line:
            specs["tongue"]["type"] = get_csv_val(line)
        if line.startswith('LENGTH:'):
            specs["tongue"]["length"] = get_csv_val(line)
        if line.startswith('COUPLER:'):
            specs["tongue"]["coupler"] = get_csv_val(line)
        if line.startswith('JACK:'):
            specs["tongue"]["jack"] = get_csv_val(line)
        if line.startswith('SAFETY CHAINS:'):
            specs["tongue"]["safety_chains"] = get_csv_val(line)
        if line.startswith('SPARE:'):
            specs["tongue"]["spare"] = get_csv_val(line)
        if line.startswith('WINCH PLATE:'):
            specs["tongue"]["winch_plate"] = get_csv_val(line)
        if line.startswith('STORAGE:'):
            specs["tongue"]["storage"] = get_csv_val(line)
        # Chassis
        if line.startswith('MAIN FRAME:'):
            val = get_csv_val(line)
            if not val and i + 1 < len(lines):
                val = clean_val(lines[i+1].strip().strip('"'))
            specs["chassis"]["main_frame"] = val
        # Deck
        if line.startswith('DECK WIDTH:'):
            specs["deck"]["deck_width"] = get_csv_val(line)
        if line.startswith('WIDTH BETWEEN FENDERS:'):
            specs["deck"]["width_between_fenders"] = get_csv_val(line)
        if line.startswith('FLOORING:'):
            specs["deck"]["flooring"] = get_csv_val(line)
        if line.startswith('CROSSMEMBERS:'):
            specs["deck"]["crossmembers"] = get_csv_val(line)
        if line.startswith('SIDES:'):
            specs["deck"]["sides"] = get_csv_val(line)
        if line.startswith('RAMPS:'):
            specs["deck"]["ramps"] = get_csv_val(line)
        if line.startswith('FENDERS:'):
            specs["deck"]["fenders"] = get_csv_val(line)
        if line.startswith('DECK:') and 'Dovetail' in line:
            specs["deck"]["type"] = get_csv_val(line)
        # Running Gear
        if line.startswith('TIRES:'):
            specs["running_gear"]["tires"] = get_csv_val(line)
        if line.startswith('RIMS:'):
            specs["running_gear"]["rims"] = get_csv_val(line)
        if line.startswith('AXLES:'):
            specs["running_gear"]["axles"] = get_csv_val(line)
        if line.startswith('SUSPENSION:'):
            specs["running_gear"]["suspension"] = get_csv_val(line)
        # Electrical
        if line.startswith('LIGHTS:'):
            specs["electrical_and_lighting"]["lights"] = get_csv_val(line)
        # Finish
        if line.startswith('PAINT:'):
            specs["finish"]["paint"] = get_csv_val(line)
    
    # Parse Options
    cat_map = {
        'tongue': 'tongue', 'deck': 'deck', 'lift system': 'lift_system',
        'running gear': 'running_gear', 'electrical and lighting': 'electrical_and_lighting',
        'finish': 'finish'
    }
    current_cat = None
    
    for i in range(start_line, end_line):
        line = lines[i].strip()
        if not line:
            continue
        
        s = line.rstrip(',').strip()
        if s.endswith(':') and s.rstrip(':').strip().isupper():
            cat = s.rstrip(':').strip().lower()
            if cat in cat_map:
                current_cat = cat_map[cat]
                continue
        
        if line.startswith('ID,OPTIONS') or line.startswith('PAGE') or line.startswith('$') or line.startswith('PER') or line.startswith('EACH'):
            continue
        
        parts = parse_csv_line(line)
        opt_id = ""
        opt_name_parts = []
        opt_price = ""
        
        for p in parts:
            p_clean = p.strip().strip('"')
            if re.match(r'^[A-Z0-9]+-\d+$', p_clean) or re.match(r'^[A-Z0-9]+-[A-Z]\d+$', p_clean):
                opt_id = p_clean
            elif p_clean.startswith('$'):
                val = p_clean.replace('$', '').replace(',', '')
                if val.replace('.', '').isdigit():
                    opt_price = val
            else:
                val_clean = p_clean.replace(',', '')
                if val_clean.replace('.', '').isdigit() and len(p_clean) < 15:
                    if not opt_price:
                        opt_price = p_clean
                elif p_clean and 'PER LINEAR' not in p_clean.upper() and 'EACH' not in p_clean.upper():
                    opt_name_parts.append(p_clean)
        
        if opt_id and current_cat:
            result["options"][current_cat][opt_id] = {
                "option": ' '.join(opt_name_parts).strip(),
                "price": opt_price
            }
    
    return result


def main():
    with open(CSV_PATH, 'r') as f:
        raw = f.read()
    lines = raw.split('\n')
    
    # Parse CEZ Car Hauler (lines 3935-4056)
    cez = parse_product(lines, 3935, 4056, "CEZ", "Car Hauler", "Bumper Pull")
    output_path = os.path.join(OUTPUT_DIR, 'cez_car_hauler.json')
    with open(output_path, 'w') as f:
        json.dump(cez, f, indent=2)
    print(f"✓ Written: {output_path}")
    
    if '--all' in sys.argv:
        # CHZ Car Hauler (lines 4057-~)
        chz = parse_product(lines, 4057, 4200, "CHZ", "Car Hauler", "Bumper Pull")
        out = os.path.join(OUTPUT_DIR, 'chz_car_hauler.json')
        with open(out, 'w') as f:
            json.dump(chz, f, indent=2)
        print(f"✓ Written: {out}")
    
    print("\nDone! Use --all to convert all product sections.")

if __name__ == '__main__':
    main()