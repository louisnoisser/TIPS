from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from gba_ops_reanalysis.gba_xml import report_files
from rebuild_tips_code_level_audit import parse_report

class ReportSelectionTest(TestCase):
    def test_case_insensitive_and_excluded_report_forms(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name in ['123-00-2012-XML.xml','124-00-2012-xml.XML','125-00-2012-xml.xml','126-Bund.xml','127-Land.xml','128-das.xml','notes.txt']:
                (p/name).write_text('<root/>')
            self.assertEqual({x.name for x in report_files(p)}, {'123-00-2012-XML.xml','124-00-2012-xml.XML','125-00-2012-xml.xml'})
            self.assertEqual([x.name for x in report_files(p,'123*')],['123-00-2012-XML.xml'])
    def collision(self, first, second):
        # Separate physical directories simulate case-sensitive filesystems even
        # on default case-insensitive APFS; mocked enumeration is one year.
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup);r=Path(tmp.name)
        (r/'a').mkdir();(r/'b').mkdir()
        p=r/'a'/'123-00-2012-xml.xml';q=r/'b'/'123-00-2012-XML.xml'
        p.write_text(first);q.write_text(second)
        return r,p,q
    def test_identical_case_variants_deduplicated(self):
        r,p,q=self.collision('<r/>','<r/>')
        with patch.object(Path,'iterdir',return_value=iter([q,p])):
            self.assertEqual(report_files(r),[p])
    def test_divergent_case_variants_raise_conflict(self):
        r,p,q=self.collision('<r/>','<different/>')
        with patch.object(Path,'iterdir',return_value=iter([p,q])):
            with self.assertRaisesRegex(ValueError,'Conflicting case-normalized'):report_files(r)
    def test_identical_names_different_years_not_merged(self):
        with TemporaryDirectory() as tmp:
            r=Path(tmp)
            for year in [2010,2012]:
                d=r/f'xml_{year}';d.mkdir();(d/'same-xml.xml').write_text('<r/>')
            self.assertEqual(sum(len(report_files(d)) for d in r.iterdir()),2)
    def test_repeated_department_records_kept_and_other_ops_excluded(self):
        payload=b'<root><Kontaktdaten><Name>Test</Name></Kontaktdaten>'+b'<Prozedur><OPS_301>8-839.80</OPS_301><Anzahl>5</Anzahl></Prozedur>'*2+b'<Prozedur><OPS_301>8-839.80</OPS_301><Anzahl_Datenschutz/></Prozedur>'*3+b'<Prozedur><OPS_301>5-839.8</OPS_301><Anzahl>999</Anzahl></Prozedur></root>'
        r=parse_report(Path('data/xml/xml_2012/261200220-00-2012-XML.xml'),payload,2012)
        self.assertEqual(len(r),1)
        self.assertEqual((r[0]['numeric_count'],r[0]['current_parser_numeric_count'],r[0]['raw_record_count'],r[0]['suppressed_record_count']),('10','10','5','3'))
