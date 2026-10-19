#!/usr/bin/env python3
"""Reproduce the legacy code-level audit, then apply case-insensitive selection.

No imputation or record deduplication is performed at the procedure level.
Descriptions are frozen display annotations from the documented legacy audit;
all frequencies, flags, identities and names are independently read from XML.
"""
from pathlib import Path
import argparse,csv,json,hashlib,collections,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gba_ops_reanalysis.gba_xml import (report_files,discover_year_dirs,REPORT_RE,PROCEDURE_PATTERNS,PROCEDURE_CODE_NAMES,COUNT_NAMES,find_first_text,extract_contact_info,parse_file_identity)
DESCRIPTIONS={
 '8-839.8':'Portosystemischer Shunt (TIPS) [non-terminal parent]',
 '8-839.80':'Perkutanes Anlegen [historical de novo TIPS creation]',
 '8-839.81':'Perkutane (Ballon-)Angioplastie', '8-839.82':'Perkutane Thrombolyse',
 '8-839.83':'Perkutane Thrombektomie',
 '8-839.84':'Perkutane Verkleinerung eines bestehenden portosystemischen Shunts',
 '8-839.85':'Perkutaner Verschluss','8-839.86':'Revision mit Stenteinlage',
 '8-839.87':'Perkutanes Anlegen eines ungecoverten Stents',
 '8-839.88':'Perkutanes Anlegen eines gecoverten Stents',
 '8-839.89':'Perkutanes Anlegen von 2 oder mehr ungecoverten Stents',
 '8-839.8a':'Perkutanes Anlegen von 2 oder mehr gecoverten Stents',
 '8-839.8x':'Sonstige',
 '8-839.8A':'Perkutanes Anlegen von 2 oder mehr gecoverten Stents [upper-case source variant]',
 '8-839.8X':'Sonstige [upper-case source variant]'}
COLUMNS=['reporting_year','site_identifier','ik','OPS_code','hospital_name','numeric_count','current_parser_numeric_count','suppressed_flag','source_file','inpatient_or_ambulatory','code_description','raw_record_count','visible_record_count','suppressed_record_count','aggregate_report_count_wrapper_flag','n_suppressed_component_reports','site_report_type']
def sha(payload):return hashlib.sha256(payload).hexdigest()
def number(text):
 try:return int(text.strip())
 except (ValueError,AttributeError):return None

def parse_report(path,payload,year):
 tree=ET.fromstring(payload);groups=collections.defaultdict(list)
 for pattern in PROCEDURE_PATTERNS:
  for proc in tree.findall(pattern):
   code=find_first_text(proc,PROCEDURE_CODE_NAMES)
   if code.lower().startswith('8-839.8'):groups[code].append(proc)
 if not groups:return []
 ik,site,parsed_year=parse_file_identity(path,year);contact=extract_contact_info(tree)
 rows=[]
 for code,procs in sorted(groups.items()):
  direct=[];nums=[];supp=[];wrappers=[];ncomp=0
  for proc in procs:
   direct_val=next((number(proc.findtext(name)) for name in COUNT_NAMES if number(proc.findtext(name)) is not None),None)
   nested=[e for e in proc.iter() if 'gesamtbericht' in e.tag.lower()]
   count=direct_val
   if count is None:
    values=[number(e.text) for wrapper in nested for e in wrapper if e.tag in COUNT_NAMES and number(e.text) is not None]
    if values:count=sum(values)
   if count is not None:nums.append(count)
   if direct_val is not None:direct.append(direct_val)
   supp.append(any('datenschutz' in e.tag.lower() for e in proc.iter() if e is not proc))
   wrappers.append(bool(nested))
   ncomp+=sum(number(e.text) or 0 for e in proc.iter() if e.tag in ('Anzahl_FA_Datenschutz','Fallzahl_FA_Datenschutz'))
  rows.append(dict(zip(COLUMNS,[str(parsed_year),f'{ik}-{site}',ik,code,contact['hospital_name'],str(sum(nums)) if nums else '',str(sum(direct)) if direct else '',str(any(supp)),f'data/xml/{path.parent.name}/{path.name}','inpatient_department_procedure (B-X.7)',DESCRIPTIONS.get(code,''),str(len(procs)),str(len(nums)),str(sum(supp)),str(any(wrappers)),str(ncomp),'aggregate_99' if site=='99' else 'component_or_single_site'])))
 return rows

def bag(rows):return collections.Counter(tuple(r[c] for c in COLUMNS) for r in rows)
def write_csv(path,rows):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args();out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
 old=[];new=[];hashes=[];additions=[];selection=[]
 for folder in discover_year_dirs(ROOT/'data/xml'):
  historical=sorted(x for x in folder.glob('*-xml.xml') if x.is_file() and REPORT_RE.search(x.name))
  corrected=report_files(folder)
  oldset=set(historical);newset=set(corrected)
  paths=sorted(oldset|newset)
  for path in paths:
   payload=path.read_bytes()
   hashes.append({'path':str(path.relative_to(ROOT)),'bytes':len(payload),'sha256':sha(payload),'legacy_selected':path in oldset,'corrected_selected':path in newset})
   if b'8-839.8' not in payload.lower():continue
   rows=parse_report(path,payload,int(folder.name[-4:]))
   if path in oldset:old.extend(rows)
   if path in newset:new.extend(rows)
   if path in newset-oldset:additions.append({'path':str(path.relative_to(ROOT)),'matched_code_rows':len(rows),'records':rows})
  selection.append({'year':int(folder.name[-4:]),'legacy_files':len(oldset),'corrected_files':len(newset),'additional':[x.name for x in sorted(newset-oldset)],'removed':[x.name for x in sorted(oldset-newset)]})
  print(folder.name,'files',len(paths),'cumulative rows',len(old),len(new),flush=True)
 legacy=list(csv.DictReader((ROOT/'outputs/audit/tips_code_level_audit.csv').open()))
 assert list(legacy[0])==COLUMNS
 target=bag(legacy);observed=bag(old)
 proof={'legacy_existing_rows':len(legacy),'legacy_rebuilt_rows':len(old),'exact_all_columns_multiset_match':target==observed,'normalizations':['CSV parsing removes only record order/line-ending/quoting differences; all field strings, empty fields and duplicate multiplicities compared exactly.'],'missing':[dict(zip(COLUMNS,r))|{'multiplicity':n} for r,n in (target-observed).items()],'unexpected':[dict(zip(COLUMNS,r))|{'multiplicity':n} for r,n in (observed-target).items()]}
 (out/'legacy_reproduction.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
 (out/'file_selection.json').write_text(json.dumps(selection,indent=2))
 (out/'additional_reports.json').write_text(json.dumps(additions,ensure_ascii=False,indent=2))
 with (out/'xml_input_sha256_manifest.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(hashes[0]));w.writeheader();w.writerows(hashes)
 write_csv(out/'tips_code_level_audit_legacy_reproduced.csv',old)
 if not proof['exact_all_columns_multiset_match']:
  print('REPRODUCTION FAILED',len(proof['missing']),len(proof['unexpected']));return 2
 delta=bag(new)-observed;removed=observed-bag(new)
 assert not removed and all(r[0]=='2012' and r[1]=='261200220-00' for r in delta), 'Unexpected correction beyond Potsdam 2012'
 write_csv(out/'tips_code_level_audit_corrected.csv',new)
 # Compatible input name for the existing validation CLI, only in the new destination.
 write_csv(out/'tips_code_level_audit.csv',new)
 print('REPRODUCTION PASS; corrected rows',len(new),'additional',sum(delta.values()),flush=True)
 return 0
if __name__=='__main__':raise SystemExit(main())
