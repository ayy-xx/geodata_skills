# Geodata - Geographic Data Processing Skill

A professional geospatial data processing toolkit designed as a Claude Code skill. Supports raster alignment, spatial analysis, coordinate transformation, and map visualization, with built-in quality control through data sampling validation.

## Key Features

- **Raster Smart Alignment** - Auto-selects resampling methods based on data characteristics
- **Batch Processing + Sampling QC** - Validate batch results through independent regeneration and comparison
- **Vector/Raster I/O** - Read and write Shapefile, GeoJSON, GeoTIFF, NetCDF, HDF5, and more
- **Coordinate Transformation** - WGS84, CGCS2000, UTM, Web Mercator, GCJ-02/BD-09
- **Spatial Analysis** - Buffer, overlay, interpolation, spatial statistics
- **Map Visualization** - Static (matplotlib + cartopy) and interactive (folium) maps

## Supported Formats

| Type | Formats |
|------|---------|
| Vector | Shapefile, GeoJSON, KML/KMZ, GeoPackage, GML |
| Raster | GeoTIFF, NetCDF, HDF5, ASCII Grid, ENVI |

## Modules

| Module | Script | Description |
|--------|--------|-------------|
| Raster Alignment | `scripts/raster_align.py` | Align multiple rasters to a common spatial reference |
| Sampling Validator | `scripts/sampling_validator.py` | Quality control via independent regeneration and comparison |
| Geo Processor | `scripts/geo_processor.py` | Core processing: I/O, transformation, spatial analysis |

## Dependencies

```
rasterio>=1.3.0
geopandas>=0.12.0
pyproj>=3.4.0
shapely>=2.0.0
fiona>=1.8.0
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.6.0
cartopy>=0.21.0
folium>=0.14.0
```

## Directory Structure

```
geodata/
├── SKILL.md              # Skill definition and full documentation
├── README.md
├── scripts/
│   ├── geo_processor.py
│   ├── raster_align.py
│   └── sampling_validator.py
├── references/
│   ├── coordinate_systems.md
│   ├── raster_formats.md
│   └── vector_formats.md
└── assets/
    └── report_template.md
```

## License

Apache 2.0
