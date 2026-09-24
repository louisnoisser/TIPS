# Inputs required for broader reproduction but excluded from this snapshot

| Input category | Source location in the working project | Reason excluded | Expected use |
|---|---|---|---|
| G-BA quality-report XML | `data/xml/` | Raw source collection and redistribution scope | Rebuild provider and activity tables |
| Official OPS catalogues | `ops_bfarm_2013_2024/` | Large third-party download collection | Rebuild year-specific code mappings |
| GHS-POP raster | `spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif` | Large raster | Population-weighted accessibility |
| GHS-SMOD raster | `spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif` | Large raster | Urban, rural and other classification |
| Germany boundaries | `spatial/` | Geospatial source assets | National and regional clipping |
| OSM extract | `ors-docker/files/germany-latest.osm.pbf` | Large third-party geodata | Routing graph construction |
| ORS graph and runtime state | `ors-docker/graphs/`, `ors-docker/logs/` | Large container and routing runtime data | Exact routing-environment reconstruction |
| Individual isochrone geometry bank | Recovery and final geography output folders | Large generated GeoJSON collection | Routing-free recomputation of network unions |
| Geocoding and population caches | `data/cache/` | Local caches | Offline repeatability and reduced network dependence |
| Python environment | `.venv/` | Machine-specific environment | Dependency execution environment |

The compact manifests and provenance reports retained in this snapshot identify many of these inputs by path, size and SHA-256. Their recorded presence in the original working project does not mean their bytes are included here.
