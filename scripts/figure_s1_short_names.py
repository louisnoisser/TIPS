#!/usr/bin/env python3
"""Rebuild Figure S1 using checked single-line names; no pipeline changes.

Run: python figure_s1_short_names.py --repo REPO --desktop '.../TIPS OPS' --out NEW_FOLDER
Requires pandas, numpy and matplotlib. Websites were manually verified on 2026-10-19;
the evidence below is a dated assessment, not a live network lookup on reruns.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties

ACCESS_DATE = '2026-10-19'
# Expected XML identity/address and manually verified carrier-website evidence.
EVIDENCE = {
42: ('260590139-773659000', 'Beurhausstraße', '40', '44137', 'Dortmund',
     'https://www.klinikumdo.de/patienten-besucher/anfahrt',
     'Klinikzentrum Mitte am angegebenen Standort bestätigt. XML nennt Klinikum Dortmund Mitte; figure_label und table_name auf Nutzerwunsch exakt auf diesen Standortnamen gesetzt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
52: ('260571421-773289000', 'Kiskerstr.', '26', '33615', 'Bielefeld',
     'https://www.franziskus.de/fr/kontakt/anfahrt.php',
     'Franziskus Hospital Bielefeld am angegebenen Standort bestätigt; Website schreibt Kiskerstraße. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
53: ('260550701-772358000', 'Mühlenstraße', '27', '45659', 'Recklinghausen',
     'https://www.proselis.de/prosper-hospital-recklinghausen/aufenthalt-und-besuch',
     'Prosper-Hospital, Standort Recklinghausen, bestätigt; nicht mit dem zweiten PROSELIS-Standort St. Elisabeth-Hospital Herten gleichgesetzt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
54: ('260510939-771562000', 'Carnaper Straße', '48', '42283', 'Wuppertal',
     'https://www.petrus-krankenhaus-wuppertal.de/ihr-aufenthalt/anfahrt-parken',
     'Petrus-Krankenhaus als weiterhin verwendeter Kurzname bestätigt. XML 2024 und Website führen Cellitinnen-Krankenhaus St. Petrus. Laut Trägerhistorie Umbenennung bereits 2023, nicht nach 2024: https://www.petrus-krankenhaus-wuppertal.de/ueber-uns/unsere-historie/ . Auf Nutzerwunsch figure_label auf Cellitinnen-Krankenhaus St. Petrus, Wuppertal und table_name auf Cellitinnen-Krankenhaus St. Petrus gesetzt: XML-Standortname 2024, einheitlich mit den Cellitinnen-Häusern in Köln.'),
69: ('260930129-771930000', 'Söllnerstraße', '16', '92637', 'Weiden i. d. OPf.',
     'https://www.kliniken-nordoberpfalz.ag/ueber-uns/unsere-standorte/klinikum-weiden',
     'Klinikum Weiden am angegebenen Standort bestätigt; Website kürzt den Ortsnamen zu Weiden. Standortnummer ist im Krankenhauskontaktdaten-Block vorhanden. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
71: ('261101878-773179000', 'Landsberger Allee', '49', '10249', 'Berlin',
     'https://www.vivantes.de/gesundheitsnetzwerk/krankenhaeuser/klinikum-im-friedrichshain/',
     'Vivantes Klinikum im Friedrichshain am Standort Landsberger Allee bestätigt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
72: ('261101878-773183000', 'Rudower Straße', '48', '12351', 'Berlin',
     'https://www.vivantes.de/gesundheitsnetzwerk/krankenhaeuser/klinikum-neukoelln/',
     'Vivantes Klinikum Neukölln am angegebenen Standort bestätigt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
89: ('261101878-773184000', 'Rubensstraße', '125', '12157', 'Berlin',
     'https://www.vivantes.de/gesundheitsnetzwerk/krankenhaeuser/auguste-viktoria-klinikum/',
     'Vivantes Auguste-Viktoria-Klinikum am angegebenen Standort bestätigt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
95: ('261101878-773186000', 'Am Nordgraben', '2', '13509', 'Berlin',
     'https://www.vivantes.de/gesundheitsnetzwerk/krankenhaeuser/humboldt-klinikum/',
     'Vivantes Humboldt-Klinikum am Standort Am Nordgraben bestätigt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
105: ('261101878-773181000', 'Dieffenbachstraße', '1', '10967', 'Berlin',
      'https://www.vivantes.de/gesundheitsnetzwerk/krankenhaeuser/klinikum-am-urban/',
      'Vivantes Klinikum Am Urban am angegebenen Standort bestätigt. Keine spätere Namensänderung in der geprüften Quelle festgestellt.'),
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def accepted_s9(path):
    w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    for parent in root.iter():
        for child in list(parent):
            if child.tag in (w + 'del', w + 'moveFrom'):
                parent.remove(child)
    tables = []
    for table in root.iter(w + 'tbl'):
        rows = [[' '.join(''.join(t.text or '' for t in cell.iter(w + 't')).split())
                 for cell in row.findall(w + 'tc')] for row in table.findall(w + 'tr')]
        if len(rows) == 21 and rows[0][:3] == ['Rank', 'Hospital', 'City']:
            tables.append(rows)
    assert len(tables) == 1, 'Table S9 must be unambiguously identified'
    return tables[0][1:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--desktop', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    repo, desktop, out = args.repo.resolve(), args.desktop.resolve(), args.out.resolve()
    assert not out.exists(), 'Use a new output directory; existing outputs are never overwritten'
    master = repo / 'outputs/late_stage_geo_corrective_qa_2026-08-14/proposed_full_identifiable_network_review_master_corrective_qa.csv'
    resolved = repo / 'outputs/site_resolution_validation/resolved_site_level_data.csv'
    names = repo / 'outputs/figure_s1_inputs_2026-10-19/FigureS1_short_names.csv'
    template = repo / 'outputs/figure_s1_inputs_2026-10-19/figure_s1.py'
    old = desktop / 'Figure S1/FigureS1_data.csv'
    supplement = desktop / 'OPS_TIPS_Supplement_v5.1.docx'
    protected = [master, resolved, names, template, supplement]
    protected += sorted(f for f in (desktop / 'Figure S1').rglob('*') if f.is_file())
    hashes_before = {str(f): sha(f) for f in protected}

    # Original template validation and sorting, retained verbatim.
    m = pd.read_csv(master, dtype=str)
    m["vis"] = m.visible_activity.astype(float).astype(int)
    r = pd.read_csv(resolved, dtype={"ik": str}); r = r[r.reporting_year == 2024]
    chk = m.merge(r[["site_identifier", "visible_activity", "hospital_name"]].rename(columns={"visible_activity": "r_vis"}), left_on="site_id", right_on="site_identifier")
    assert len(chk) == 193 and (chk.vis == chk.r_vis).all() and (chk.provider_name == chk.hospital_name).all()
    d = m[m.vis > 0].copy()
    assert len(d) == 113 and d.vis.sum() == 5247 and (m.vis == 0).sum() == 80
    d = d.sort_values(["vis", "site_id"], ascending=[False, True]).reset_index(drop=True)
    d["rank"] = np.arange(1, len(d) + 1)
    assert len(m) == 193 and m.site_id.is_unique and len(r) == 193 and r.site_identifier.is_unique
    d['official_name_gba'] = d.provider_name
    n = pd.read_csv(names, dtype={'site_id': str}, keep_default_na=False)
    assert len(n) == 113 and n.site_id.is_unique
    assert sorted(n['rank']) == list(range(1, 114))
    assert set(n.site_id) == set(d.site_id)
    n = n.sort_values('rank').reset_index(drop=True)
    original_names = n.copy(deep=True)
    # User-approved revision on 2026-10-19: use the XML 2024 location names.
    overrides = {
        42: ('260590139-773659000', 'Klinikum Dortmund Mitte', 'Klinikum Dortmund Mitte'),
        54: ('260510939-771562000', 'Cellitinnen-Krankenhaus St. Petrus, Wuppertal', 'Cellitinnen-Krankenhaus St. Petrus'),
    }
    for rank, (sid, figure_label, table_name) in overrides.items():
        idx = n.index[n['rank'] == rank][0]
        assert n.loc[idx, 'site_id'] == sid
        n.loc[idx, ['figure_label', 'table_name']] = [figure_label, table_name]
    assert n.loc[~n['rank'].isin(overrides)].equals(original_names.loc[~original_names['rank'].isin(overrides)])
    assert n.drop(columns=['figure_label', 'table_name']).equals(original_names.drop(columns=['figure_label', 'table_name']))
    assert n.site_id.tolist() == d.site_id.tolist()
    assert n.official_name_gba.str.split().str.join(' ').tolist() == d.provider_name.str.split().str.join(' ').tolist()
    assert n.city.tolist() == d.city.tolist()
    for column in ('figure_label', 'table_name'):
        assert n[column].str.strip().ne('').all()
        assert not n[column].str.contains(r'[\r\n]').any()
    assert not n.figure_label.str.match(r'^\s*\d+\.').any()
    assert n.figure_label.is_unique and not n.duplicated(['table_name', 'city']).any()
    assert not n.figure_label.str.contains(r'(?i)(?:straße|strasse|\bstr\.)').any(), 'Street additions are prohibited'
    for column in ('figure_label', 'table_name'):
        d[column] = n[column]
    baseline = pd.read_csv(old, dtype={'site_id': str})
    columns = ['rank', 'site_id', 'reported_tips_procedure_occurrences_2024']
    new_data = d[['rank', 'site_id', 'ik', 'official_name_gba', 'city', 'figure_label', 'table_name', 'vis']].rename(columns={'vis': columns[-1]})
    assert baseline[columns].equals(new_data[columns]), 'Old/new rowwise data comparison failed'

    # Table S9: accepted-all-changes view; the sole authorized exception is exact.
    s9_rows = []
    for row in accepted_s9(supplement):
        rank = int(row[0]); x = d.iloc[rank - 1]
        assert rank == len(s9_rows) + 1
        assert row[2] == x.city and int(row[3]) == x.vis
        full_name = ' '.join(x.official_name_gba.split())
        status = 'identisch'
        if row[1] != full_name:
            assert rank == 15
            assert row[1] == 'Universitätsklinikum Carl Gustav Carus Dresden an der Technischen Universität Dresden'
            assert full_name == row[1] + ', Anstalt des öffentlichen Rechts des Freistaates Sachsen'
            status = 'freigegebene Ausnahme: Rechtsformzusatz fehlt in S9'
        s9_rows.append([rank, x.site_id, row[1], row[2], int(row[3]), status])
    assert len(s9_rows) == 20

    # Dated website assessment is linked to the exact local XML identity/address.
    assert set(n.loc[n.check_note.ne(''), 'rank']) == set(EVIDENCE)
    checked = n.copy()
    for col in ['check_status', 'xml_file', 'xml_sha256', 'xml_location_name', 'xml_location_address', 'website_url', 'access_date', 'check_result']:
        checked[col] = ''
    checked['check_status'] = 'nicht markiert; unverändert'
    for rank, evidence in EVIDENCE.items():
        sid, street, number, postcode, city, url, result = evidence
        idx = checked.index[checked['rank'] == rank][0]
        assert checked.loc[idx, 'site_id'] == sid
        f = repo / f'data/xml/xml_2024/{sid}-2024-xml.xml'
        root = ET.parse(f).getroot()
        elem = root.find('.//Standortkontaktdaten')
        if elem is None:
            elem = root.find('.//Krankenhauskontaktdaten')
        assert elem is not None
        ik, site = sid.split('-')
        assert elem.findtext('IK') == ik and elem.findtext('Standortnummer') == site
        address = elem.find('Kontakt_Zugang')
        assert address is not None
        assert [(address.findtext(t) or '').strip() for t in ['Strasse', 'Hausnummer', 'Postleitzahl', 'Ort']] == [street, number, postcode, city]
        checked.loc[idx, ['check_status', 'xml_file', 'xml_sha256', 'xml_location_name', 'xml_location_address', 'website_url', 'access_date', 'check_result']] = [
            ('bestätigt; auf Nutzerwunsch an XML-Standortnamen angepasst' if rank in overrides else 'bestätigt; unverändert'), str(f.relative_to(repo)), sha(f), elem.findtext('Name'),
            f'{street} {number}, {postcode} {city}', url, ACCESS_DATE, result]
        protected.append(f); hashes_before[str(f)] = sha(f)
    assert checked[n.columns].equals(n), 'Checked mapping must match the approved names'

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'pdf.fonttype': 42, 'ps.fonttype': 42})
    COL = '#3182bd'; XMAX = 330
    labels = [f'{rank}. {label}' for rank, label in zip(d['rank'], d.figure_label)]
    # Measure every label using the actual Agg renderer at the PNG export DPI.
    probe = plt.figure(figsize=(6.3, 8.8), dpi=600)
    probe.canvas.draw(); renderer = probe.canvas.get_renderer()
    font = FontProperties(family='DejaVu Sans', size=6.6)
    widths = [renderer.get_text_width_height_descent(label, font, ismath=False)[0] for label in labels]
    widest = int(np.argmax(widths))
    label_width_in = max(widths) / 600
    tick_pad_pt = 3.5
    # Add tick padding plus 0.08 inch of physical paper margin.
    common_left = (label_width_in + tick_pad_pt / 72 + 0.08) / 6.3
    plt.close(probe)
    assert 0 < common_left < .97
    parts = [('A', d.iloc[:29]), ('B', d.iloc[29:57]), ('C', d.iloc[57:85]), ('D', d.iloc[85:])]
    figures = []; layout = []
    for tag, part in parts:
        fig, ax = plt.subplots(figsize=(6.3, 8.8), dpi=600)
        y = 28 - np.arange(len(part))
        ax.barh(y, part.vis, height=0.62, color=COL, edgecolor='none')
        values = [ax.text(v + 3, yi, f'{v}', va='center', ha='left', fontsize=6.6, color='#333333') for yi, v in zip(y, part.vis)]
        ax.set_yticks(y, [f'{rk}. {lab}' for rk, lab in zip(part['rank'], part.figure_label)], fontsize=6.6)
        ax.set_ylim(-0.7, 28.7)
        ax.set_xlim(0, XMAX); ax.set_xticks(np.arange(0, XMAX + 1, 50))
        ax.set_axisbelow(True); ax.grid(axis='x', color='#d9d9d9', linewidth=.6)
        ax.tick_params(axis='y', length=0, pad=tick_pad_pt); ax.tick_params(axis='x', length=3, color='#666666')
        ax.set_xlabel('Reported TIPS procedure occurrences, n (2024)', labelpad=6, fontsize=8)
        first, last = int(part['rank'].iloc[0]), int(part['rank'].iloc[-1])
        ax.set_title(f'{tag}  Ranks {first}–{last} of 113', loc='left', fontsize=8, fontweight='bold', pad=8)
        fig.subplots_adjust(left=common_left, right=.97, top=.955, bottom=.065)
        fig.canvas.draw(); renderer = fig.canvas.get_renderer()
        texts = ax.get_yticklabels() + values + ax.get_xticklabels() + [ax.xaxis.label, ax._left_title]
        boxes = [t.get_window_extent(renderer).frozen() for t in texts if t.get_visible() and t.get_text()]
        for box in boxes:
            assert box.x0 >= 0 and box.y0 >= 0 and box.x1 <= fig.bbox.width and box.y1 <= fig.bbox.height, f'Panel {tag}: text outside paper'
        for i, box in enumerate(boxes):
            for other in boxes[i+1:]:
                assert not box.overlaps(other), f'Panel {tag}: overlapping text'
        yboxes = [t.get_window_extent(renderer) for t in ax.get_yticklabels()]
        vboxes = [t.get_window_extent(renderer) for t in values]
        layout.append({'panel': tag, 'first_rank': first, 'last_rank': last, 'common_left_fraction': common_left,
                       'axes_bounds_fraction': list(ax.get_position().bounds), 'label_min_left_in': min(b.x0 for b in yboxes) / 600,
                       'text_count_checked': len(boxes), 'overlap_count': 0, 'outside_count': 0,
                       'label_value_min_gap_in': min(v.x0 - b.x1 for b,v in zip(yboxes,vboxes)) / 600})
        figures.append((tag, fig))
    assert len({tuple(x['axes_bounds_fraction']) for x in layout}) == 1

    # No exports until all data/name/layout gates pass.
    out.mkdir(parents=True)
    new_data.to_csv(out / 'FigureS1_data.csv', index=False)
    checked.to_csv(out / 'FigureS1_short_names_checked.csv', index=False)
    shutil.copy2(Path(__file__), out / 'figure_s1_short_names.py')
    with PdfPages(out / 'FigureS1_site_level_activity_2024.pdf') as pdf:
        for tag, fig in figures:
            fig.savefig(out / f'FigureS1{tag}_site_level_activity_2024.png', dpi=600)
            fig.savefig(out / f'FigureS1{tag}_site_level_activity_2024.svg')
            pdf.savefig(fig)
            plt.close(fig)
    assert pd.read_csv(out / 'FigureS1_data.csv', dtype={'site_id':str})[columns].equals(baseline[columns])
    assert all(sha(f) == hashes_before[str(f)] for f in protected), 'A protected input changed'
    audit = {'date': ACCESS_DATE, 'counts': {'sites':193,'numeric_sites':113,'visible_occurrences':5247,'suppressed_only':80},
             'widest_label': labels[widest], 'widest_label_width_in':label_width_in, 'common_left_fraction':common_left,
             'layout':layout, 'inputs_sha256':hashes_before, 'rowwise_old_new_equal':True,
             's9':s9_rows, 'website_verification':'manually verified 2026-10-19; evidence embedded in script and checked CSV',
             'pdf_visual_review':'pending independent rendering and review'}
    (out / 'validation_results.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    lines = ['# Figure S1: einzeilige Kliniknamen', '', 'Erstellt am 2026-10-19. Daten, Sortierung, Panelaufteilung und Diagrammparameter bleiben unverändert. Ausschließlich Klinikbeschriftungen und der gemeinsame linke Rand wurden angepasst.', '',
             '## Daten- und Namensprüfung', '',
             '- Alle ursprünglichen Assertions aus figure_s1.py unverändert übernommen und bestanden: 193 Standorte; 113 numerische Standorte; Summe 5.247; 80 suppressed-only; vollständiger Abgleich von Aktivität und provider_name mit resolved_site_level_data für 2024.',
             '- Namenszuordnung: genau 113 eindeutige site_id; Ränge 1–113 vollständig und eindeutig; ID-Menge und Rangzuordnung entsprechen exakt den numerischen Standorten.',
             '- figure_label und table_name vollständig, einzeilig; figure_label ohne Rang eindeutig; Kombination table_name und city eindeutig. Keine Straßenzusätze; keine anderen Namen als Rang 42 und 54 geändert.',
             '- Alle zehn markierten Vorschläge anhand der Standort-ID/Adresse im XML 2024 und der Träger-Website bestätigt. Zunächst waren alle Vorschläge bestätigt. Auf Nutzerwunsch wurden anschließend ausschließlich Rang 42 und Rang 54 an die XML-Standortnamen angepasst; figure_label und table_name konsistent geändert. Beim Adressvergleich wurden ausschließlich äußere Leerzeichen entfernt (XML-Straßenfelder bei Rang 95 und 105). Original-Namensdatei unverändert; checked-Datei enthält alle 113 Namen und zusätzliche Prüffelder.', '',
             '## Freigegebene Namensrevision am 2026-10-19', '', '- Rang 42, 260590139-773659000: figure_label und table_name Klinikum Dortmund Mitte. Begründung: Standortname laut XML 2024.', '- Rang 54, 260510939-771562000: figure_label Cellitinnen-Krankenhaus St. Petrus, Wuppertal; table_name Cellitinnen-Krankenhaus St. Petrus. Begründung: Standortname laut XML 2024, einheitlich mit den Cellitinnen-Häusern in Köln.', '- Alle übrigen Daten, Namen und Diagrammparameter unverändert; linke Ränder erneut gemeinsam aus dem breitesten Label berechnet.', '', '## Zeilenweiser Datenabgleich', '',
             'Alle 113 Zeilen wurden in gleicher Reihenfolge nach rank, site_id und reported_tips_procedure_occurrences_2024 exakt mit der bisherigen FigureS1_data.csv verglichen; auch die erneut eingelesene neue CSV stimmt überein.', '',
             '| Rang | site_id | Vorher n | Neu n | Ergebnis |','|---:|---|---:|---:|---|']
    for i,x in new_data.iterrows():
        lines.append(f'| {x["rank"]} | {x.site_id} | {baseline.iloc[i][columns[-1]]} | {x[columns[-1]]} | identisch |')
    lines += ['', '## Table S9: Ränge 1–20', '',
              'Die DOCX wurde ausschließlich gelesen. Für die Ansicht nach Annahme aller Änderungen wurden gelöschte/wegbewegte XML-Inhalte entfernt und eingefügte/hinbewegte Inhalte beibehalten; das Supplement selbst bleibt unverändert.', '',
              '**Freigegebene Ausnahme bei Rang 15:** Table S9 enthält die frühere gekürzte Fassung „Universitätsklinikum Carl Gustav Carus Dresden an der Technischen Universität Dresden“ ohne „, Anstalt des öffentlichen Rechts des Freistaates Sachsen“. Der Nutzer hat diese Ausnahme am 2026-10-19 ausdrücklich akzeptiert: Zuordnung eindeutig über Rang 15, Dresden, Aktivität 113 und übereinstimmenden Namensanfang. Der vollständige G-BA-Name bleibt in official_name_gba erhalten. Table S9 wird später separat auf Kurznamen umgestellt.', '',
              '| Rang | site_id (aus Master, nicht S9) | Name in S9 | Stadt | Visible n | Ergebnis |', '|---:|---|---|---|---:|---|']
    for row in s9_rows: lines.append('| '+' | '.join(map(str,row))+' |')
    lines += ['', '## Standortprüfung der zehn markierten Namen', '', 'Abrufdatum aller unten genannten Websites: 2026-10-19. Aussagen zu Namensänderungen beziehen sich auf die tatsächlich geprüften Quellen; keine Behauptung einer vollständigen historischen Recherche.', '']
    for _,x in checked[checked.check_note.ne('')].iterrows():
        lines += [f'### Rang {x["rank"]}: {x.figure_label}', '', f'- site_id: `{x.site_id}`', f'- XML: `{x.xml_file}`', f'- Standortname im XML: {x.xml_location_name}', f'- Standortadresse im XML: {x.xml_location_address}', f'- Träger-Website: {x.website_url}', f'- Abrufdatum: {x.access_date}', f'- Ergebnis: {x.check_result}', '']
    lines += ['## Layout und Exportprüfung', '',
              '- 6,3 × 8,8 Zoll; DejaVu Sans; Klinik- und Wertlabels 6,6 pt; Balkenfarbe #3182bd; x-Achse 0–330. Achsentitel, Paneltitel, Balkenhöhe, vertikale Positionen sowie oberer, unterer und rechter Rand wie in der Vorlage.',
              '- A: Ränge 1–29; B: 30–57; C: 58–85; D: 86–113. Keine Umbrüche, kein textwrap, kein automatisches Verkleinern.',
              f'- Breitestes Label: „{labels[widest]}“, gemessene Breite {label_width_in:.6f} Zoll bei 600 dpi. Gemeinsamer linker Rand: {common_left:.9f} der Abbildungsbreite (= {common_left*6.3:.6f} Zoll). Berechnung: maximale Labelbreite + 3,5 pt Tickabstand + 0,08 Zoll Papierrand.',
              '- Alle Text-Bounding-Boxes bei 600 dpi geprüft: Kliniklabels, Wertangaben, Achsenticks, Achsentitel und Paneltitel vollständig innerhalb der Seite; keine paarweisen Textüberschneidungen. Alle Panels haben identische Achsenkoordinaten.',
              '- PNG: 3780 × 5280 Pixel bei 600 dpi; SVG/PDF: voller gemeinsamer Seitenrahmen, kein tight/crop-Export.',
              '- Visuelle Prüfung der vier PDF-Seiten: noch ausstehend; wird nach unabhängigem Rendern ergänzt.', '',
              '## Quellen und Unverändertheit', '', 'SHA-256 aller Eingaben, der zehn XML-Berichte und aller Dateien im bisherigen Ordner Figure S1 wurden vor/nach der Erstellung verglichen: unverändert. Hashes und Layoutmesswerte stehen in validation_results.json. Keine Pipeline-Daten, anderen Abbildungen, Supplementdateien, Routing- oder Geocoding-Ergebnisse geändert.', '',
              '## Reproduktion', '', 'Mit der vorhandenen Python-Umgebung (pandas, numpy, matplotlib):', '', '```bash',
              'python figure_s1_short_names.py \\', f'  --repo "{repo}" \\', f'  --desktop "{desktop}" \\', '  --out "/Pfad/zu/einem/neuen/Ausgabeordner"', '```', '',
              'Die Namens-Websiteprüfung ist als datierte Evidenz eingebettet; ein erneuter Lauf ruft keine Websites ab. Daten-, XML-, S9- und Bounding-Box-Prüfungen werden erneut ausgeführt. Neue Exporte werden nur in einem noch nicht vorhandenen Ausgabeordner angelegt.']
    (out / 'CHANGE_REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k in ['counts','widest_label','widest_label_width_in','common_left_fraction','layout']},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
