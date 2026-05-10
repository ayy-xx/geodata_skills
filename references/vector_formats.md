# 矢量数据格式参考

## Shapefile (.shp)

**描述：** 最常用的矢量数据格式，由ESRI开发

**特点：**
- 多文件组成（.shp, .shx, .dbf, .prj）
- 支持点、线、面几何类型
- 属性表存储在.dbf文件
- 最大文件大小约2GB
- 字段名最长10字符

**必需文件：**
| 文件 | 说明 |
|------|------|
| .shp | 几何数据 |
| .shx | 空间索引 |
| .dbf | 属性表 |
| .prj | 坐标系定义（可选但推荐） |

**Python读取：**
```python
import geopandas as gpd

gdf = gpd.read_file('data.shp')
print(gdf.head())
print(gdf.crs)
print(gdf.bounds)
print(gdf.geometry.geom_type)
```

**Python写入：**
```python
gdf.to_file('output.shp', encoding='utf-8')
```

**注意事项：**
- 中文路径和字段名可能导致乱码，建议使用UTF-8编码
- 删除时需删除所有相关文件

---

## GeoJSON (.geojson, .json)

**描述：** 基于JSON的地理数据格式，Web友好

**特点：**
- 纯文本格式，人类可读
- 支持所有几何类型
- 支持属性数据
- 适合Web应用
- 可直接在浏览器中使用

**文件结构：**
```json
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [116.4, 39.9]
            },
            "properties": {
                "name": "北京",
                "population": 21540000
            }
        }
    ]
}
```

**Python读取：**
```python
import geopandas as gpd
import json

# 方法1：geopandas
gdf = gpd.read_file('data.geojson')

# 方法2：json模块
with open('data.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)
```

**Python写入：**
```python
# 方法1：geopandas
gdf.to_file('output.geojson', driver='GeoJSON')

# 方法2：手动构建
geojson = {
    "type": "FeatureCollection",
    "features": []
}
for idx, row in gdf.iterrows():
    feature = {
        "type": "Feature",
        "geometry": row.geometry.__geo_interface__,
        "properties": row.drop('geometry').to_dict()
    }
    geojson["features"].append(feature)

with open('output.geojson', 'w', encoding='utf-8') as f:
    json.dump(geojson, f, ensure_ascii=False)
```

**适用场景：** Web地图应用，数据交换，API接口

---

## KML/KMZ (.kml, .kmz)

**描述：** Keyhole标记语言，Google Earth标准格式

**特点：**
- XML格式
- 支持样式定义
- 支持层次结构
- KMZ是KML的压缩版本
- 支持网络链接

**文件结构：**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
        <name>数据图层</name>
        <Placemark>
            <name>点1</name>
            <Point>
                <coordinates>116.4,39.9,0</coordinates>
            </Point>
        </Placemark>
    </Document>
</kml>
```

**Python读取：**
```python
import geopandas as gpd

gdf = gpd.read_file('data.kml', driver='KML')
```

**Python写入：**
```python
gdf.to_file('output.kml', driver='KML')
```

**适用场景：** Google Earth，数据分享，公众展示

---

## GeoPackage (.gpkg)

**描述：** OGC标准格式，基于SQLite

**特点：**
- 单文件格式
- 支持矢量和栅格
- 无大小限制
- 支持事务
- 跨平台兼容

**Python读取：**
```python
import geopandas as gpd

# 读取指定图层
gdf = gpd.read_file('data.gpkg', layer='layer_name')

# 列出所有图层
import fiona
layers = fiona.listlayers('data.gpkg')
```

**Python写入：**
```python
# 写入单图层
gdf.to_file('output.gpkg', driver='GPKG')

# 追加图层
gdf.to_file('output.gpkg', driver='GPKG', layer='new_layer', mode='a')
```

**适用场景：** 现代GIS应用，替代Shapefile，多图层存储

---

## GML (.gml)

**描述：** 地理标记语言，基于XML

**特点：**
- OGC标准
- XML格式
- 支持复杂要素模型
- 自描述性强
- 文件较大

**Python读取：**
```python
import geopandas as gpd

gdf = gpd.read_file('data.gml')
```

**适用场景：** 数据交换，标准化存储，Web服务

---

## 几何类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| Point | 单点 | 城市位置、站点 |
| MultiPoint | 多点 | 采样点集合 |
| LineString | 线 | 道路、河流 |
| MultiLineString | 多线 | 水系网络 |
| Polygon | 面 | 行政区域、地块 |
| MultiPolygon | 多面 | 岛屿区域 |
| GeometryCollection | 几何集合 | 混合类型 |

---

## 坐标系识别

**从.prj文件读取：**
```python
with open('data.prj', 'r') as f:
    prj_content = f.read()
    print(prj_content)
```

**从GeoDataFrame读取：**
```python
import geopandas as gpd

gdf = gpd.read_file('data.shp')
print(gdf.crs)  # 输出坐标系信息
print(gdf.crs.to_epsg())  # 输出EPSG代码
```

**常见坐标系：**
| 名称 | EPSG | 说明 |
|------|------|------|
| WGS84 | 4326 | GPS坐标系 |
| CGCS2000 | 4490 | 中国大地坐标系 |
| Web Mercator | 3857 | Web地图常用 |
| UTM Zone 50N | 32650 | 中国东部地区 |
| UTM Zone 51N | 32651 | 中国东南部 |
