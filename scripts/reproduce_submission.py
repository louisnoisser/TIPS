#!/usr/bin/env python3
"""Validate locked inputs and render manuscript assets without external services."""
from pathlib import Path
import argparse, hashlib, json, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from gba_ops_reanalysis.final_corrected import validate_expected_totals, scenario_metrics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = pd.read_csv(ROOT/'reproducibility/locked_outputs_sha256.csv')
    for row in manifest.itertuples(index=False):
        path = ROOT/row.path
        if not path.is_file() or sha(path) != row.sha256:
            raise ValueError(f'Locked input mismatch: {row.path}')
    sites = pd.read_csv(ROOT/'outputs/site_resolution_validation/resolved_site_level_data.csv')
    assert validate_expected_totals(sites).exact_match.all()
    y = sites[sites.reporting_year.eq(2024)]
    assert len(y) == 193 and (y.visible_activity > 0).sum() == 113
    assert y.visible_activity.sum() == 5247
    assert sites.loc[sites.reporting_year.eq(2012), 'visible_activity'].sum() == 2120
    return sites


def figure_s1(out):
    data = pd.read_csv(ROOT/'outputs/figure_s1_short_names_2026-10-19/FigureS1_data.csv', dtype={'site_id':str})
    assert len(data) == 113 and data.site_id.is_unique and data['rank'].tolist() == list(range(1,114))
    assert data.reported_tips_procedure_occurrences_2024.sum() == 5247
    assert data.figure_label.is_unique
    assert not data.duplicated(['table_name','city']).any()
    for col in ['figure_label','table_name']:
        assert data[col].str.strip().ne('').all() and not data[col].str.contains(r'[\r\n]').any()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','savefig.facecolor':'white','pdf.fonttype':42,'ps.fonttype':42})
    fig=plt.figure(figsize=(6.3,8.8),dpi=600);fig.canvas.draw();renderer=fig.canvas.get_renderer()
    labels=[f'{r}. {s}' for r,s in zip(data['rank'],data.figure_label)]
    fp=FontProperties(family='DejaVu Sans',size=6.6)
    width=max(renderer.get_text_width_height_descent(s,fp,False)[0] for s in labels)/600
    left=(width+3.5/72+.08)/6.3;plt.close(fig)
    with PdfPages(out/'FigureS1_site_level_activity_2024.pdf') as pdf:
        for tag,part in [('A',data.iloc[:29]),('B',data.iloc[29:57]),('C',data.iloc[57:85]),('D',data.iloc[85:])]:
            fig,ax=plt.subplots(figsize=(6.3,8.8),dpi=600);y=28-np.arange(len(part));v=part.reported_tips_procedure_occurrences_2024
            ax.barh(y,v,height=.62,color='#3182bd',edgecolor='none')
            for yi,vi in zip(y,v):ax.text(vi+3,yi,str(vi),va='center',ha='left',fontsize=6.6,color='#333333')
            ax.set_yticks(y,[f'{r}. {s}' for r,s in zip(part['rank'],part.figure_label)],fontsize=6.6)
            ax.set_ylim(-.7,28.7);ax.set_xlim(0,330);ax.set_xticks(np.arange(0,331,50));ax.set_axisbelow(True)
            ax.grid(axis='x',color='#d9d9d9',linewidth=.6);ax.tick_params(axis='y',length=0,pad=3.5);ax.tick_params(axis='x',length=3,color='#666666')
            ax.set_xlabel('Reported TIPS procedure occurrences, n (2024)',labelpad=6,fontsize=8)
            ax.set_title(f'{tag}  Ranks {int(part["rank"].iloc[0])}–{int(part["rank"].iloc[-1])} of 113',loc='left',fontsize=8,fontweight='bold',pad=8)
            fig.subplots_adjust(left=left,right=.97,top=.955,bottom=.065);fig.canvas.draw();renderer=fig.canvas.get_renderer()
            texts=ax.get_yticklabels()+list(ax.texts)+ax.get_xticklabels()+[ax.xaxis.label,ax._left_title]
            boxes=[t.get_window_extent(renderer) for t in texts if t.get_text()]
            for i,b in enumerate(boxes):
                assert b.x0>=0 and b.y0>=0 and b.x1<=fig.bbox.width and b.y1<=fig.bbox.height
                assert all(not b.overlaps(c) for c in boxes[i+1:])
            for ext in ['png','svg']:fig.savefig(out/f'FigureS1{tag}_site_level_activity_2024.{ext}',dpi=600)
            pdf.savefig(fig);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--verify-only',action='store_true');ap.add_argument('--output-dir',type=Path,default=ROOT/'results/submission');args=ap.parse_args()
    sites=verify()
    if args.verify_only:print('PASS: locked hashes, 2012=2120, 2024=5247 and 193/113 sites');return
    out=args.output_dir.resolve()
    if out.exists():raise SystemExit('Choose a new output directory; locked inputs are never overwritten')
    out.mkdir(parents=True);tables=out/'tables';tables.mkdir()
    from run_tips_final_corrected import export_figures_1_2
    metrics=scenario_metrics(sites,'physical_site')
    export_figures_1_2(metrics,out)
    from run_late_stage_geo_validation_2026_08_14 import build_figure3
    f3=ROOT/'outputs/tips_2012_filefix_2026-10-15/tables/Figure3_candidate_B_identifiable_network_data.csv'
    qa=out/'qa';qa.mkdir()
    build_figure3(data_path=f3,figure_dir=out,qa_dir=qa,expected_sha256=sha(f3))
    import run_late_stage_accessibility_193_113_2026_08_14 as maps
    import geopandas as gpd
    from shapely.geometry import shape
    master=pd.read_csv(maps.MASTER,dtype={'site_id':str,'ik':str})
    # Use the validated coordinates, as in the original geographic workflow.
    master['latitude']=pd.to_numeric(master.proposed_latitude,errors='raise')
    master['longitude']=pd.to_numeric(master.proposed_longitude,errors='raise')
    assert len(master)==master.site_id.nunique()==193 and master[['latitude','longitude']].notna().all().all()
    for col in ['suppressed_only','threshold_ge20','threshold_ge50','threshold_ge100']:
        master[col]=master[col].astype(str).str.lower().isin(['true','1'])
    locked_gdf=gpd.read_file(maps.LOCKED_UNIONS)
    locked={(int(r.threshold),int(r.time_minutes)):r.geometry for r in locked_gdf.itertuples()}
    unions={}
    for network in ['full_identifiable_reference','openly_numeric_reference']:
        unions[network]={}
        for minutes in [30,60]:
            p=ROOT/f'outputs/late_stage_accessibility_193_113_recovery_2026-08-15/isochrones/{network}_{minutes}min_union.geojson'
            j=json.loads(p.read_text());unions[network][minutes]=shape(j['features'][0]['geometry']) if j.get('type')=='FeatureCollection' else shape(j['geometry'])
    maps.OUT=out
    labels=pd.read_csv(maps.LABELS,dtype={'site_id':str})
    maps.build_figure('C193',master,unions,locked,labels)
    figure_s1(out)
    # Export all corrected manuscript table CSVs, preserving their relative paths.
    for p in (ROOT/'outputs/final_corrected_2026-07-24').rglob('*.csv'):
        dest=tables/'corrected_analysis'/p.relative_to(ROOT/'outputs/final_corrected_2026-07-24')
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    for folder in ['outputs/final_submission_assets_2026-07-24/tables',
                   'outputs/de_novo_accessibility_sensitivity_2026-08-16',
                   'outputs/late_stage_accessibility_193_113_recovery_2026-08-15/tables']:
        for p in (ROOT/folder).rglob('*.csv'):
            dest=tables/'additional_locked'/p.relative_to(ROOT/'outputs')
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    # Export exactly the locked correction tables; no rounding or data edits.
    for folder in ['tables','geography']:
        source=ROOT/'outputs/tips_2012_filefix_2026-10-15'/folder
        for p in source.glob('*.csv'):shutil.copy2(p,tables/p.name)
    source=ROOT/'outputs/de_novo_sensitivity_2013_2024'
    for p in source.glob('*.csv'):shutil.copy2(p,tables/p.name)
    for p in (ROOT/'outputs/tips_geographic_suppression_sensitivity_2026-09-23').glob('*.csv'):shutil.copy2(p,tables/p.name)
    (out/'reproduction_summary.json').write_text(json.dumps({'status':'passed','figures':['1','2','3B','4 C193','S1 A-D'],'figure4_selection':'C193','locked_csv_tables':[str(p.relative_to(tables)) for p in sorted(tables.rglob('*.csv'))]},indent=2)+'\n')
    print('PASS: manuscript figures and locked tables exported to',out)

if __name__=='__main__':main()
