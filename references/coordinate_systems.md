# 坐标系参考

## 地理坐标系（Geographic CRS）

使用经纬度表示位置，单位为度。

### WGS84 (EPSG:4326)

**描述：** World Geodetic System 1984，GPS使用的坐标系

**参数：**
- 椭球体：WGS84
- 长半轴：6378137.0 m
- 扁率：1/298.257223563
- 经度范围：-180° ~ 180°
- 纬度范围：-90° ~ 90°

**适用场景：** GPS数据、国际数据交换、Web地图

---

### CGCS2000 (EPSG:4490)

**描述：** 中国大地坐标系2000，中国国家法定坐标系

**参数：**
- 椭球体：CGCS2000
- 长半轴：6378137.0 m
- 扁率：1/298.257222101
- 经度范围：73° ~ 135°（中国范围）
- 纬度范围：3° ~ 54°（中国范围）

**与WGS84差异：** 在厘米级精度下可视为相同

**适用场景：** 中国国内测绘、国土数据、规划数据

---

## 投影坐标系（Projected CRS）

使用平面坐标表示位置，单位通常为米。

### UTM（通用横轴墨卡托）

**描述：** 将地球分为60个带，每带6度

**中国相关带：**
| 带号 | 经度范围 | EPSG（北半球） |
|------|----------|----------------|
| 43 | 66°-72° | 32643 |
| 44 | 72°-78° | 32644 |
| 45 | 78°-84° | 32645 |
| 46 | 84°-90° | 32646 |
| 47 | 90°-96° | 32647 |
| 48 | 96°-102° | 32648 |
| 49 | 102°-108° | 32649 |
| 50 | 108°-114° | 32650 |
| 51 | 114°-120° | 32651 |
| 52 | 120°-126° | 32652 |
| 53 | 126°-132° | 32653 |

**Python转换：**
```python
from pyproj import Transformer

# WGS84 -> UTM Zone 50N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32650", always_xy=True)
x, y = transformer.transform(lon, lat)
```

---

### 高斯-克吕格投影

**描述：** 中国常用的投影方式，分为3度带和6度带

**3度带带号：**
| 带号 | 中央经线 | EPSG |
|------|----------|------|
| 25 | 75° | 2425 |
| 26 | 78° | 2426 |
| ... | ... | ... |
| 45 | 135° | 2445 |

**6度带带号：**
| 带号 | 中央经线 | EPSG |
|------|----------|------|
| 13 | 75° | 21413 |
| 14 | 81° | 21414 |
| ... | ... | ... |
| 23 | 135° | 21423 |

---

### Web Mercator (EPSG:3857)

**描述：** Web地图常用的投影坐标系

**特点：**
- 基于WGS84
- 保持角度不变（等角）
- 高纬度地区变形严重
- 适合在线地图显示

**适用场景：** Google Maps、OpenStreetMap、百度地图、高德地图

---

## 中国特殊坐标系

### GCJ-02（火星坐标系）

**描述：** 中国国家测绘局制定的加密坐标系

**特点：**
- 对WGS84进行非线性偏移
- 高德地图、腾讯地图使用
- 偏移量约100-700米

**转换工具：**
```python
import math

def wgs84_to_gcj02(lng, lat):
    """WGS84转GCJ02"""
    a = 6378245.0
    ee = 0.00669342162296594323

    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)

    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)

    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)

    return lng + dlng, lat + dlat

def _transform_lat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transform_lng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret
```

---

### BD-09（百度坐标系）

**描述：** 百度地图使用的坐标系，在GCJ-02基础上二次加密

**特点：**
- 在GCJ-02基础上额外偏移
- 百度地图专用

**转换工具：**
```python
import math

def gcj02_to_bd09(lng, lat):
    """GCJ02转BD09"""
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * math.pi * 3000.0 / 180.0)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * math.pi * 3000.0 / 180.0)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return bd_lng, bd_lat

def bd09_to_gcj02(bd_lng, bd_lat):
    """BD09转GCJ02"""
    x = bd_lng - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * math.pi * 3000.0 / 180.0)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000.0 / 180.0)
    lng = z * math.cos(theta)
    lat = z * math.sin(theta)
    return lng, lat
```

---

## 坐标系转换

### 使用pyproj

```python
from pyproj import Transformer

# 基本转换
def transform_coords(x, y, from_epsg, to_epsg):
    """坐标转换"""
    transformer = Transformer.from_crs(f"EPSG:{from_epsg}", f"EPSG:{to_epsg}", always_xy=True)
    return transformer.transform(x, y)

# 示例：WGS84 -> CGCS2000
lon_new, lat_new = transform_coords(116.4, 39.9, 4326, 4490)

# 示例：WGS84 -> UTM Zone 50N
x, y = transform_coords(116.4, 39.9, 4326, 32650)
```

### 批量转换

```python
import numpy as np
from pyproj import Transformer

def batch_transform(lons, lats, from_epsg, to_epsg):
    """批量坐标转换"""
    transformer = Transformer.from_crs(f"EPSG:{from_epsg}", f"EPSG:{to_epsg}", always_xy=True)
    return transformer.transform(lons, lats)

# 使用numpy数组
lons = np.array([116.4, 121.5, 113.3])
lats = np.array([39.9, 31.2, 23.1])
new_lons, new_lats = batch_transform(lons, lats, 4326, 3857)
```

---

## 坐标系判断方法

### 从元数据读取

```python
import rasterio
import geopandas as gpd

# 栅格数据
with rasterio.open('data.tif') as src:
    print(f"CRS: {src.crs}")
    print(f"EPSG: {src.crs.to_epsg()}")

# 矢量数据
gdf = gpd.read_file('data.shp')
print(f"CRS: {gdf.crs}")
print(f"EPSG: {gdf.crs.to_epsg()}")
```

### 从坐标范围判断

```python
def guess_crs_from_bounds(bounds):
    """根据坐标范围猜测坐标系"""
    west, south, east, north = bounds

    # 经纬度范围（WGS84/CGCS2000）
    if -180 <= west <= 180 and -90 <= south <= 90:
        return 4326  # WGS84

    # UTM范围（米）
    if 100000 <= west <= 900000:
        # 根据经度范围判断UTM带号
        center_lon = (west + east) / 2
        zone = int((center_lon + 180) / 6) + 1
        return 32600 + zone  # 北半球

    return None
```

---

## 常见问题

### Q: WGS84和CGCS2000有什么区别？
A: 两者在厘米级精度下几乎相同，主要区别在于椭球参数的微小差异。对于大多数应用可以互换使用。

### Q: 如何判断数据是GCJ-02还是WGS84？
A: 如果在中国境内，将数据叠加到已知的WGS84底图上，如果出现约100-700米的偏移，很可能是GCJ-02。

### Q: 如何选择UTM带号？
A: 根据数据的中心经度计算：`带号 = (经度 + 180) / 6 + 1`，取整。
