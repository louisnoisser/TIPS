# Provenance of unmatched 2013 OPS code 8-839.80

## Final status

**`invalid_hospital_reported_legacy_code`**

`8-839.80` is a valid official OPS 2012 terminal code, labelled "Perkutanes Anlegen". It is not valid in OPS 2013. The official 2013 change commentary states that primary placement was subdivided into `8-839.87` for an uncovered stent and `8-839.88` for a covered stent.

The string occurs literally seven times in five 2013 hospital XML files. Every occurrence is an `OPS_301` value paired with `Anzahl_Datenschutz`. The files were produced by three independent quality-report software products. This rules out a parser-created value and makes a shared single-software artefact unlikely. The evidence is most consistent with hospitals carrying a retired 2012 code into 2013 reports.

No code has been remapped or discarded.

## Official references

- [Official OPS 2012 family](https://klassifikationen.bfarm.de/ops/kode-suche/htmlops2012/block-8-80...8-85.htm)
- [Official OPS 2013 family](https://klassifikationen.bfarm.de/ops/kode-suche/htmlops2013/block-8-80...8-85.htm)
- [Official OPS 2013 change commentary](https://klassifikationen.bfarm.de/ops/kode-suche/htmlops2013/zusatz-03-kommentar.htm)

## Five affected source files

| Source | IK | Physical site | Institution | Literal occurrences | Generated | Visible family activity | Threshold without 8-839.80 |
|---|---|---|---|---:|---|---:|---|
| `data/xml/xml_2013/260510018-00-2013-xml.xml` | `260510018` | `260510018-00` | Universitätsklinikum Düsseldorf | 1 | 2014-11-20 | 105 | 100-199 |
| `data/xml/xml_2013/260530283-00-2013-xml.xml` | `260530283` | `260530283-00` | Uniklinik Köln | 1 | 2014-12-05 | 22 | 20-49 |
| `data/xml/xml_2013/260620431-00-2013-xml.xml` | `260620431` | `260620431-00` | Universitätsklinikum Gießen und Marburg GmbH, Standort Marburg | 2 | 2014-12-10 | 0 | suppressed-only |
| `data/xml/xml_2013/261101015-00-2013-xml.xml` | `261101015` | `261101015-00` | Charite - Universitätsmedizin Berlin | 2 | 2014-12-12 | 83 | 50-99 |
| `data/xml/xml_2013/261500289-00-2013-xml.xml` | `261500289` | `261500289-00` | Universitätsklinikum Magdeburg A. ö. R. | 1 | 2014-12-15 | 11 | 4-19 |

## Analytical effects

- **Visible national activity:** unaffected. All seven occurrences are suppressed and contribute zero visible activity.
- **Site counts:** unaffected. Every file contains other `8-839.8*` records, so no site depends solely on `8-839.80` for identification.
- **Threshold classification:** unaffected because there is no visible numeric count attached to `8-839.80`.
- **Planned secondary-only analysis:** affected at the validation gate. The invalid legacy entries must remain explicit and receive an approved handling decision. They do not alter the substantive classification of these five hospital-years because each also reports valid 2013 primary placement code `.87` or `.88`, visibly or under suppression.

## Adjacent 8-839.8 family records by source

### `data/xml/xml_2013/260510018-00-2013-xml.xml`

8-839.81 [literal occurrences=1, visible=46, suppressed entries=0] | 8-839.82 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.83 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.86 [literal occurrences=1, visible=11, suppressed entries=0] | 8-839.87 [literal occurrences=1, visible=26, suppressed entries=0] | 8-839.88 [literal occurrences=1, visible=12, suppressed entries=0] | 8-839.8x [literal occurrences=1, visible=10, suppressed entries=0]

### `data/xml/xml_2013/260530283-00-2013-xml.xml`

8-839.81 [literal occurrences=1, visible=8, suppressed entries=0] | 8-839.86 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.87 [literal occurrences=1, visible=6, suppressed entries=0] | 8-839.88 [literal occurrences=1, visible=8, suppressed entries=0] | 8-839.8x [literal occurrences=1, visible=0, suppressed entries=1]

### `data/xml/xml_2013/260620431-00-2013-xml.xml`

8-839.81 [literal occurrences=3, visible=0, suppressed entries=3] | 8-839.88 [literal occurrences=2, visible=0, suppressed entries=2]

### `data/xml/xml_2013/261101015-00-2013-xml.xml`

8-839.81 [literal occurrences=3, visible=53, suppressed entries=2] | 8-839.84 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.85 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.86 [literal occurrences=2, visible=0, suppressed entries=2] | 8-839.87 [literal occurrences=2, visible=12, suppressed entries=1] | 8-839.88 [literal occurrences=2, visible=6, suppressed entries=1] | 8-839.8x [literal occurrences=1, visible=12, suppressed entries=0]

### `data/xml/xml_2013/261500289-00-2013-xml.xml`

8-839.81 [literal occurrences=5, visible=11, suppressed entries=3] | 8-839.83 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.85 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.86 [literal occurrences=2, visible=0, suppressed entries=2] | 8-839.87 [literal occurrences=5, visible=0, suppressed entries=5] | 8-839.88 [literal occurrences=1, visible=0, suppressed entries=1] | 8-839.8x [literal occurrences=3, visible=0, suppressed entries=3]

## Literal occurrences and XML context

### `260510018-00#1`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[2]/Prozeduren/Verpflichtend/Prozedur[567]/OPS_301`
- Department: `2` Klinik für Kardiologie, Pneumologie und Angiologie
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz />`
- Immediate nearby records: 8-839.42 [suppressed] | 8-839.44 [suppressed] | 8-839.80 [suppressed] | 8-839.82 [suppressed] | 8-839.83 [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur>
                        <OPS_301>8-839.44</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
                    <Prozedur>
                        <OPS_301>8-839.80</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
                    <Prozedur>
                        <OPS_301>8-839.82</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
```

### `260530283-00#1`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[4]/Prozeduren/Verpflichtend/Prozedur[156]/OPS_301`
- Department: `4` Klinik für Gastroenterologie und Hepatologie
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz/>`
- Immediate nearby records: 8-812.63 [suppressed] | 8-812.64 [suppressed] | 8-839.80 [suppressed] | 8-839.81 [visible=8] | 8-839.86 [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur>
						<OPS_301>8-812.64</OPS_301>
						<Anzahl_Datenschutz/>
					</Prozedur>
					<Prozedur>
						<OPS_301>8-839.80</OPS_301>
						<Anzahl_Datenschutz/>
					</Prozedur>
					<Prozedur>
						<OPS_301>8-839.81</OPS_301>
						<Anzahl>8</Anzahl>
					</Prozedur>
```

### `260620431-00#1`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[10]/Prozeduren/Verpflichtend/Prozedur[449]/OPS_301`
- Department: `10` Klinik für Innere Medizin - Gastroenterologie, Endokrinologie und Stoffwechsel
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz />`
- Immediate nearby records: 8-831.5 [visible=4] | 8-839.42 [suppressed] | 8-839.80 [suppressed] | 8-839.81 [suppressed] | 8-839.88 [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur><OPS_301>8-839.42</OPS_301><Anzahl_Datenschutz /></Prozedur><Prozedur><OPS_301>8-839.80</OPS_301><Anzahl_Datenschutz /></Prozedur><Prozedur><OPS_301>8-839.81</OPS_301><Anzahl_Datenschutz /></Prozedur>
```

### `260620431-00#2`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[32]/Prozeduren/Verpflichtend/Prozedur[276]/OPS_301`
- Department: `32` Klinik für Diagnostische und Interventionelle Radiologie
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz />`
- Immediate nearby records: 8-839.1 [visible=9] | 8-839.7 [visible=7] | 8-839.80 [suppressed] | 8-839.81 [suppressed] | 8-839.88 [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur><OPS_301>8-839.7</OPS_301><Anzahl>7</Anzahl></Prozedur><Prozedur><OPS_301>8-839.80</OPS_301><Anzahl_Datenschutz /></Prozedur><Prozedur><OPS_301>8-839.81</OPS_301><Anzahl_Datenschutz /></Prozedur>
```

### `261101015-00#1`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[52]/Prozeduren/Verpflichtend/Prozedur[442]/OPS_301`
- Department: `52` Institut für Radiologie (mit den Bereichen Kinderradiologie und Neuroradiologie) CBF/CCM/CVK
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz />`
- Immediate nearby records: 8-839.5 [suppressed] | 8-839.7 [suppressed] | 8-839.80 [suppressed] | 8-839.84 [suppressed] | 8-839.85 [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur>
                        <OPS_301>8-839.7</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
                    <Prozedur>
                        <OPS_301>8-839.80</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
                    <Prozedur>
                        <OPS_301>8-839.84</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
```

### `261101015-00#2`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[53]/Prozeduren/Verpflichtend/Prozedur[584]/OPS_301`
- Department: `53` Klinik für Anästhesiologie m. S. operative Intensivmedizin, CCM/CVK
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz />`
- Immediate nearby records: 8-836.m9 [suppressed] | 8-836.n1 [suppressed] | 8-839.80 [suppressed] | 8-83a.10 [suppressed] | 8-83a.12 [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur>
                        <OPS_301>8-836.n1</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
                    <Prozedur>
                        <OPS_301>8-839.80</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
                    <Prozedur>
                        <OPS_301>8-83a.10</OPS_301>
                        <Anzahl_Datenschutz />
                    </Prozedur>
```

### `261500289-00#1`

- XPath: `/Qualitaetsbericht/Organisationseinheiten_Fachabteilungen/Organisationseinheit_Fachabteilung[5]/Prozeduren/Verpflichtend/Prozedur[396]/OPS_301`
- Department: `5` Universitätsklinik für Gastroenterologie, Hepatologie und Infektiologie
- Literal element: `<OPS_301>8-839.80</OPS_301>`
- Suppression element: `<Anzahl_Datenschutz />`
- Immediate nearby records: 8-836.nh [suppressed] | 8-839.5 [suppressed] | 8-839.80 [suppressed] | 8-839.86 [suppressed] | 8-839.x [suppressed]

Exact source context, comprising the immediately preceding procedure, the affected procedure, and the immediately following procedure:

```xml
<Prozedur>
            <OPS_301>8-839.5</OPS_301>
            <Anzahl_Datenschutz />
          </Prozedur>
          <Prozedur>
            <OPS_301>8-839.80</OPS_301>
            <Anzahl_Datenschutz />
          </Prozedur>
          <Prozedur>
            <OPS_301>8-839.86</OPS_301>
            <Anzahl_Datenschutz />
          </Prozedur>
```

