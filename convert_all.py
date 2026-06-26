#!/usr/bin/env python3
"""
CSV to JSON Converter: Convert ALL product sections from Horizon trailer catalog
"""

import csv, json, re, os

CSV_PATH = '/tmp/TRAILERS/ok (1).csv'
OUTPUT_DIR = '/tmp/TRAILERS'

def parse_csv_line(line):
    try: return next(csv.reader([line]))
    except: return line.split(',')

def clean_val(val):
    if not val: return ""
    return val.strip().strip('"').strip('$').strip()

def get_csv_val(line, idx=1):
    parts = parse_csv_line(line)
    return clean_val(parts[idx]) if len(parts) > idx else ""

def detect_category_type(name):
    n = name.upper()
    if 'DUMP' in n and 'ROLL OFF' in n: return 'Roll Off Dump Trailer', 'Dump'
    if 'ROLL OFF' in n: return 'Roll Off Trailer', 'Roll Off'
    if 'DUMP' in n: return 'Dump Trailer', 'Bumper Pull'
    if 'CAR HAULER' in n or 'SINGLE CAR' in n:
        return ('Car Hauler', 'Gooseneck') if 'GN' in n else ('Car Hauler', 'Bumper Pull')
    if 'FLATDECK' in n or 'FLATBED' in n:
        if 'SUPER SINGLE' in n: return 'Flatbed Trailer', 'Super Single'
        if 'HEAVY DUTY' in n: return 'Flatbed Trailer', 'Heavy Duty'
        if 'HOT SHOT' in n: return 'Flatbed Trailer', 'Hot Shot'
        return 'Flatbed Trailer', 'Flatbed'
    if 'FULL TILT' in n or 'TILT' in n:
        if 'CONTAINER' in n: return 'Container Trailer', 'Full Tilt'
        if 'HOT SHOT' in n: return 'Tilt Trailer', 'Hot Shot'
        if 'SUPER SINGLE' in n: return 'Tilt Trailer', 'Super Single'
        return 'Tilt Trailer', 'Full Tilt'
    if 'PIPE HAULER' in n: return 'Pipe Hauler', 'Bumper Pull'
    if 'HYDRAULIC DOVETAIL' in n: return 'Hydraulic Dovetail Trailer', 'Hydraulic'
    if 'SPLIT TILT' in n or 'PARTIAL TILT' in n: return 'Split Tilt Trailer', 'Split Tilt'
    if 'CONTAINER' in n: return 'Container Trailer', 'Flatbed'
    if 'UTILITY' in n: return 'Utility Trailer', 'Bumper Pull'
    if 'ECONOMIC' in n: return 'Dump Trailer', 'Economy'
    if 'LIGHT WEIGHT' in n: return 'Dump Trailer', 'Light Weight'
    return 'Trailer', 'Trailer'

def is_real_product_header(name):
    """Filter out non-product lines (warnings, instructions, etc)"""
    n = name.upper()
    skip_words = ['PRIOR TO OPERATING', 'CONFIRM THE COMBINED', 'LOAD REDUCING', 
                  'NOTE:', 'IMAGE SHOWN', 'PAGE', 'OPTIONS', 'STANDARD FEATURES',
                  'MODELS & PRICES', 'ID,OPTIONS', 'JUN 1', 'JUN 2', 'JUN 3']
    for w in skip_words:
        if w in n: return False
    # Must be a recognizable trailer type
    trailer_keywords = ['TRAILER', 'DUMP', 'FLATDECK', 'FLATBED', 'CAR HAULER',
                        'TILT', 'PIPE', 'ROLL OFF', 'UTILITY', 'HYDRAULIC']
    for k in trailer_keywords:
        if k in n: return True
    return False

def parse_product_section(lines, start, end, prefix="", name=""):
    cat, ptype = detect_category_type(name)
    
    result = {
        "id": "", "model_id": prefix, "category": cat, "type": ptype,
        "name": name,
        "models_and_prices": {},
        "options": {"deck":{},"tongue":{},"running_gear":{},"electrical_and_lighting":{},"finish":{},"lift_system":{}},
        "specifications": {
            "finish": {"paint": ""},
            "tongue": {"jack":"","safety_chains":"","winch_plate":"","storage":"","coupler":"","length":"","spare":"","type":""},
            "running_gear": {"suspension":"","rims":"","tires":"","axles":""},
            "electrical_and_lighting": {"lights":""},
            "weight_ratings": {"gvwr":""},
            "chassis": {"main_frame":""},
            "deck": {"ramps":"","crossmembers":"","deck_width":"","sides":"","flooring":"","width_between_fenders":"","fenders":"","type":""}
        }
    }
    specs = result["specifications"]
    
    # Find section boundaries
    models_start = None
    features_start = None
    options_start = None
    
    for i in range(start, min(start + 200, end)):
        line = lines[i].strip()
        ul = line.upper()
        if 'MODELS & PRICES' in ul: models_start = i + 1
        if 'STANDARD FEATURES' in ul: features_start = i
        if line.startswith('OPTIONS') and 'STANDARD' not in ul and i > start + 15: 
            options_start = i
            break
    
    if models_start is None: models_start = start + 15
    if features_start is None: features_start = start + 20
    
    # Parse models & prices
    for i in range(models_start, min(models_start + 80, options_start if options_start else end)):
        line = lines[i].strip()
        if not line: continue
        parts = parse_csv_line(line)
        
        if line.startswith('"') and 'TRAILER' in line.upper():
            model_name = parts[0].strip('"') if parts else ""
            if model_name and ('x' in model_name or "'" in model_name):
                p1 = clean_val(parts[1]) if len(parts) > 1 else ""
                p2 = clean_val(parts[2]) if len(parts) > 2 else ""
                result["models_and_prices"][model_name] = {"msrp": p2, "price": p1}
        
        # Two models per line
        if line.startswith('"') and len(parts) >= 4:
            second = parts[2].strip('"') if len(parts) > 2 else ""
            if second and 'TRAILER' in second.upper() and 'x' in second:
                result["models_and_prices"][second] = {"msrp": "", "price": ""}
            third = parts[4].strip('"') if len(parts) > 4 else ""
            if third and 'TRAILER' in third.upper() and 'x' in third:
                p1 = clean_val(parts[5]) if len(parts) > 5 else ""
                p2 = clean_val(parts[6]) if len(parts) > 6 else ""
                result["models_and_prices"][third] = {"msrp": p2, "price": p1}
        
        if 'STANDARD FEATURES' in line.upper(): break
    
    # More robust model detection for two-column format
    model_count = 0
    for i in range(models_start, min(models_start + 80, options_start if options_start else end)):
        line = lines[i].strip()
        if not line: continue
        parts = parse_csv_line(line)
        
        # The CSV often has: "MODEL1",price1,msrp1,"MODEL2",price2,msrp2
        if line.startswith('"') and len(parts) >= 3:
            # Check each field for model name
            for j in range(0, len(parts), 3):
                if j < len(parts) and parts[j].startswith('"'):
                    mn = parts[j].strip('"')
                    if 'TRAILER' in mn.upper() and ('x' in mn or "'" in mn):
                        p1 = clean_val(parts[j+1]) if j+1 < len(parts) else ""
                        p2 = clean_val(parts[j+2]) if j+2 < len(parts) else ""
                        if mn not in result["models_and_prices"]:
                            result["models_and_prices"][mn] = {"msrp": p2, "price": p1}
        
        if 'STANDARD FEATURES' in line.upper():
            break
    
    # Parse standard features
    if features_start:
        for i in range(features_start, min(features_start + 80, options_start if options_start else end)):
            line = lines[i].strip()
            if not line: continue
            if line.startswith('OPTIONS') and 'STANDARD' not in line.upper(): break
            
            m = {'GVWR:': ('weight_ratings','gvwr'), 'LENGTH:': ('tongue','length'),
                 'COUPLER:': ('tongue','coupler'), 'JACK:': ('tongue','jack'),
                 'SAFETY CHAINS:': ('tongue','safety_chains'), 'SPARE:': ('tongue','spare'),
                 'WINCH PLATE:': ('tongue','winch_plate'), 'STORAGE:': ('tongue','storage'),
                 'DECK WIDTH:': ('deck','deck_width'), 'BED WIDTH:': ('deck','deck_width'),
                 'WIDTH BETWEEN FENDERS:': ('deck','width_between_fenders'),
                 'FLOORING:': ('deck','flooring'), 'CROSSMEMBERS:': ('deck','crossmembers'),
                 'SIDES:': ('deck','sides'), 'RAMPS:': ('deck','ramps'),
                 'FENDERS:': ('deck','fenders'), 'TIRES:': ('running_gear','tires'),
                 'RIMS:': ('running_gear','rims'), 'AXLES:': ('running_gear','axles'),
                 'SUSPENSION:': ('running_gear','suspension'), 'LIGHTS:': ('electrical_and_lighting','lights'),
                 'PAINT:': ('finish','paint')}
            
            for key, (sec, fld) in m.items():
                if line.startswith(key):
                    v = get_csv_val(line)
                    if v: specs[sec][fld] = v; break
            
            if line.startswith('TONGUE:') and 'I-Beam' in line: specs['tongue']['type'] = get_csv_val(line)
            if line.startswith('MAIN FRAME:'):
                v = get_csv_val(line)
                if not v and i+1 < len(lines):
                    v = clean_val(lines[i+1].strip().strip('"'))
                if v: specs['chassis']['main_frame'] = v
            if line.startswith('DECK:') and 'Dovetail' in line: specs['deck']['type'] = get_csv_val(line)
    
    # Parse options
    cat_map = {'tongue':'tongue','deck':'deck','lift system':'lift_system',
               'running gear':'running_gear','electrical and lighting':'electrical_and_lighting',
               'finish':'finish','dump':'deck','chassis':'chassis'}
    current_cat = None
    
    if options_start:
        for i in range(options_start + 1, min(options_start + 120, end)):
            line = lines[i].strip()
            if not line: continue
            if line.startswith('PAGE') or line.startswith('"JUN'): continue
            if line.startswith('"') and 'TRAILER' in line.upper() and ('x' in line or "'" in line): break
            
            s = line.rstrip(',').strip()
            if s.endswith(':') and s.rstrip(':').strip().isupper():
                cat = s.rstrip(':').strip().lower()
                if cat in cat_map and cat_map[cat] in result['options']:
                    current_cat = cat_map[cat]
                    continue
            
            if line.startswith('ID,OPTIONS') or line.startswith('$') or line.startswith('PER') or line.startswith('EACH'): continue
            if not line.replace(',','').strip(): continue
            
            parts = parse_csv_line(line)
            opt_id = ""; opt_name_parts = []; opt_price = ""
            
            for p in parts:
                pc = p.strip().strip('"')
                if re.match(r'^[A-Z0-9]+-\d+$', pc) or re.match(r'^[A-Z0-9]+-[A-Z]\d+$', pc):
                    opt_id = pc
                elif pc.startswith('$'):
                    v = pc.replace('$','').replace(',','')
                    if v.replace('.','').isdigit(): opt_price = v
                else:
                    vc = pc.replace(',','')
                    if vc.replace('.','').isdigit() and len(pc) < 15 and len(pc) > 0:
                        if not opt_price: opt_price = pc
                    elif pc and not any(x in pc.upper() for x in ['PER LINEAR','EACH','PER FT']):
                        opt_name_parts.append(pc)
            
            if opt_id and current_cat and current_cat in result['options']:
                on = ' '.join(opt_name_parts).strip()
                result['options'][current_cat][opt_id] = {"option": on, "price": opt_price}
    
    return result

def main():
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    lines = raw.split('\n')
    print(f"Total lines: {len(lines)}")
    
    # Find product sections
    candidates = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s: continue
        
        # Quoted product headers
        m = re.match(r'^"([A-Z][A-Z\s,]+)"', s)
        if m and not re.search(r"\d['\"]\s*x\s*\d", m.group(1)):
            name = m.group(1)
            if is_real_product_header(name):
                candidates.append((i, name))
        
        # Unquoted ALL-CAPS product headers
        if s.isupper() and len(s) > 15 and 'TRAILER' in s:
            skip = ['HZ5','HZ6','CEZ','CHZ','FHZ','HHZ','FFT','FFH','CFT','FTS','FHS','PHZ']
            if not any(s.startswith(p) for p in skip):
                if is_real_product_header(s.rstrip(',')):
                    if not any(abs(ex[0]-i) < 15 for ex in candidates):
                        candidates.append((i, s.rstrip(',')))
    
    candidates.sort(key=lambda x: x[0])
    
    # Deduplicate
    sections = []
    prev = -100
    for idx, name in candidates:
        if idx - prev > 20:
            sections.append((idx, name))
            prev = idx
    
    print(f"\nFound {len(sections)} product sections:\n")
    
    all_products = []
    for si, (start, name) in enumerate(sections):
        end = sections[si+1][0] if si+1 < len(sections) else len(lines)
        
        # Get prefix
        prefix = ""
        for i in range(start, min(start+15, end)):
            l = lines[i].strip()
            if l.startswith('"') and 'x' in l:
                m2 = re.match(r'"([A-Z]+)', l)
                if m2: prefix = m2.group(1); break
        
        print(f"  [{si+1}/{len(sections)}] L{start}-{end}: {name[:60]}")
        
        try:
            prod = parse_product_section(lines, start, end, prefix, name)
            all_products.append(prod)
        except Exception as e:
            print(f"      ERROR: {e}")
    
    # Write individual files
    outfiles = []
    for i, prod in enumerate(all_products):
        sf = re.sub(r'[^a-zA-Z0-9]+', '_', prod['name'].lower()).strip('_')[:50]
        path = os.path.join(OUTPUT_DIR, f'{i+1:02d}_{sf}.json')
        with open(path, 'w') as f: json.dump(prod, f, indent=2)
        outfiles.append(os.path.basename(path))
    
    # Combined file
    with open(os.path.join(OUTPUT_DIR, 'all_products.json'), 'w') as f:
        json.dump(all_products, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ {len(all_products)} products converted")
    for f in outfiles: print(f"   {f}")
    print(f"✓ Combined: all_products.json")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()