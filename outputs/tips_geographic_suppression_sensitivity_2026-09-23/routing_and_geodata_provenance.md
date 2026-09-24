# Routing and geodata provenance

## OpenRouteService

- Engine/software version: **9.8.0**. Evidence: stored runtime status in `outputs/late_stage_accessibility_193_113_2026-08-14/inputs_verified/routing_environment_metadata.json`, repeated in `outputs/late_stage_accessibility_193_113_recovery_2026-08-15/preflight/docker_ors_environment_identity.json` and the ORS log startup line. Status: demonstrated by run artifacts.
- `graph_version`: **4**. This is a graph-format value and is not evidence of the ORS software version.
- Container tag: `openrouteservice/openrouteservice:latest`. The tag was mutable and is not sufficient version evidence by itself.
- Image ID: `sha256:2ee0dcf4aeccd7852f443dfbae03a0ea96537753360e42e682a32cb9e72f929b`.
- Image digest: `openrouteservice/openrouteservice@sha256:2ee0dcf4aeccd7852f443dfbae03a0ea96537753360e42e682a32cb9e72f929b`. Status: demonstrated by stored Docker inspection metadata.
- Routing profile: `driving-car`. Status: demonstrated by runtime status and graph metadata.
- Isochrone parameters: time ranges of 30 and 60 minutes, `range_type=time`, `attributes=[area]`, stable validated longitude/latitude pairs and the established helper's largest exterior polygon. Network polygons use `shapely.unary_union`. No new routing was performed for this sensitivity analysis.
- Engine build date: `2026-03-30T12:22:34Z`. Graph date: `2026-04-01T12:04:19Z`. OSM data timestamp: `2026-03-29T20:20:46Z`.
- OSM extract: `ors-docker/files/germany-latest.osm.pbf`, SHA-256 `4b6f82c2fa58dc9828cf92d1fc5299b8565781a0bc6862840c15f1d2f2dc927f`, source filename `germany-latest.osm.pbf`. Germany coverage is indicated by the filename, graph bounds and configuration. The upstream provider, download URL and actual download timestamp are not reconstructable. The filesystem modification time is not treated as a download date.
- Graph construction is evidenced by `ors-docker/logs/ors.log`, which records graph creation from `files/germany-latest.osm.pbf` beginning on 2026-04-01 and by `ors-docker/graphs/driving-car/graph_build_info.yml`. The effective source path was supplied by the stored container environment and overrode the example path in the YAML configuration.

## Population, settlement and boundary data

- GHS-POP: `spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif`, SHA-256 `fe3bfa375b0c4e46551afc63d40212b43c01950ff02b9b386bbb228785b483ba`, GHS-POP R2023A, epoch 2025, 3 arcsec, original CRS `EPSG:4326`, pixel size `0.0008333333300326924 × 0.000833333329979504` degrees. Evidence: filename, raster metadata and `outputs/late_stage_accessibility_193_113_2026-08-14/inputs_verified/population_settlement_metadata.json`. Status: demonstrated by run artifacts.
- GHS-SMOD: `spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif`, SHA-256 `fd076785d1639a5ebf0b1ef2021d28c984cdba0c9e9d4839d64044531d34b7cc`, GHS-SMOD R2023A, epoch 2025, 1,000 m, original CRS `ESRI:54009`. Evidence: filename, raster metadata and `outputs/late_stage_accessibility_193_113_2026-08-14/inputs_verified/population_settlement_metadata.json`. Status: demonstrated by run artifacts.
- Germany boundary: `spatial/germany-detailed-boundary_917.geojson`, SHA-256 `f9e1271cb34b336ad9dd62eb1c62dbceca5f5b58dfbde2c33af249d1f01da0d7`. The boundary clips both denominators and coverage geometries. Exact upstream release and licence are not embedded and are not reconstructable from the run artifacts.
- Population overlay: the Germany boundary and isochrones are handled in EPSG:4326. GHS-SMOD is reprojected to each GHS-POP processing window with nearest-neighbour resampling. GHS-POP values are not resampled. Raster inclusion uses `all_touched=False`. EPSG:3035 is used only for geometry-area QA.
- Settlement aggregation: GHS-SMOD codes 30, 23, 22 and 21 map to urban. Codes 13, 12 and 11 map to rural. Every other value maps to other. Point classification uses the original SMOD value sampled at each validated site coordinate.
- Population denominators from the actual raster overlay are national 83,194,666.82777423, urban 60,644,251.4457971, rural 22,550,345.888311617 and other 69.49366551530291 before rounding. The reported integer denominators are 83,194,667, 60,644,251, 22,550,346 and 69. Independently rounded class denominators sum to one fewer person than the independently rounded national denominator.

## Evidence classification

- Demonstrated by run artifacts: ORS 9.8.0, image ID and digest, driving-car profile, graph and OSM timestamps, isochrone parameters, exact raster files, raster metadata, reprojection and resampling, class mapping and analysis denominators.
- Configuration only: the mutable image tag `latest` and paths appearing solely in configuration are not treated as proof without the stored runtime metadata.
- Not reconstructable: OSM provider and download URL, actual OSM download time, exact upstream release/licence of the Germany boundary and any routing parameter left at the ORS default rather than explicitly sent.
