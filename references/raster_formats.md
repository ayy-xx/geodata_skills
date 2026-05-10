# 栅格数据格式参考

## GeoTIFF (.tif, .tiff)

**描述：** 最常用的地理栅格格式，基于TIFF格式扩展

**特点：**
- 支持地理参考信息嵌入
- 支持多种数据类型（int8/16/32, float32/64）
- 支持多波段
- 支持压缩（LZW, DEFLATE, PACKBITS）
- 支持分块存储

**Python读取：**
```python
import rasterio

with rasterio.open('data.tif') as src:
    data = src.read(1)  # 读取第1波段
    transform = src.transform
    crs = src.crs
    bounds = src.bounds
    nodata = src.nodata
    profile = src.profile
```

**Python写入：**
```python
import rasterio
from rasterio.transform import from_bounds

profile = {
    'driver': 'GTiff',
    'dtype': 'float32',
    'width': 1000,
    'height': 1000,
    'count': 1,
    'crs': 'EPSG:4326',
    'transform': from_bounds(west, south, east, north, 1000, 1000),
    'nodata': -9999
}

with rasterio.open('output.tif', 'w', **profile) as dst:
    dst.write(data, 1)
```

**适用场景：** 通用栅格数据存储，遥感影像，高程模型

---

## NetCDF (.nc, .nc4)

**描述：** 网络通用数据格式，常用于气象和海洋数据

**特点：**
- 支持多维数据（时间、高度、经纬度）
- 自描述元数据
- 支持压缩
- 支持追加数据

**Python读取：**
```python
import netCDF4 as nc
import xarray as xr

# 方法1：netCDF4
dataset = nc.Dataset('data.nc', 'r')
temp = dataset.variables['temperature'][:]
lat = dataset.variables['latitude'][:]
lon = dataset.variables['longitude'][:]

# 方法2：xarray（推荐）
ds = xr.open_dataset('data.nc')
temp = ds['temperature']
```

**Python写入：**
```python
import xarray as xr
import numpy as np

ds = xr.Dataset(
    {
        'temperature': (['time', 'lat', 'lon'], temp_data),
        'precipitation': (['time', 'lat', 'lon'], precip_data)
    },
    coords={
        'time': pd.date_range('2023-01-01', periods=12, freq='M'),
        'lat': np.linspace(-90, 90, 180),
        'lon': np.linspace(-180, 180, 360)
    }
)

ds.to_netcdf('output.nc')
```

**适用场景：** 气象数据、海洋数据、气候模型输出

---

## HDF5 (.h5, .hdf5)

**描述：** 层次数据格式，适合存储复杂数据结构

**特点：**
- 支持大规模数据
- 层次化组织（类似文件系统）
- 支持压缩
- 支持部分读取

**Python读取：**
```python
import h5py

with h5py.File('data.h5', 'r') as f:
    # 列出所有数据集
    print(list(f.keys()))

    # 读取数据
    data = f['dataset_name'][:]
    metadata = f['dataset_name'].attrs['description']
```

**Python写入：**
```python
import h5py
import numpy as np

with h5py.File('output.h5', 'w') as f:
    f.create_dataset('data', data=np.array([1, 2, 3]), compression='gzip')
    f['data'].attrs['units'] = 'meters'
```

**适用场景：** NASA EarthData, MODIS数据, 大规模遥感数据

---

## ASCII Grid (.asc)

**描述：** 文本格式的栅格数据，简单易读

**特点：**
- 纯文本格式，可直接编辑
- 文件较大（无压缩）
- 头部信息包含空间参考
- 适合小数据集

**文件格式：**
```
ncols         100
nrows         100
xllcorner     0
yllcorner     0
cellsize      1
NODATA_value  -9999
1.0 2.0 3.0 ...
```

**Python读取：**
```python
import numpy as np

def read_ascii_grid(filepath):
    with open(filepath, 'r') as f:
        # 读取头信息
        header = {}
        for _ in range(6):
            key, value = f.readline().split()
            header[key.lower()] = float(value)

        # 读取数据
        data = np.loadtxt(f)

    return data, header
```

**适用场景：** 简单栅格数据交换，教学示例

---

## ENVI (.dat)

**描述：** 遥感软件ENVI的标准格式

**特点：**
- 数据和头文件分离（.dat + .hdr）
- 支持多种数据类型
- 支持多波段
- 支持地理参考

**头文件示例（.hdr）：**
```
ENVI
samples = 1000
lines   = 1000
bands   = 3
data type = 4
interleave = bsq
map info = {geographic, 1.0, 1.0, 0.0, 0.0, 0.000277777, 0.000277777, wgs-84}
```

**Python读取：**
```python
import spectral

img = spectral.open_image('data.hdr')
data = img.load()
```

**适用场景：** 遥感影像处理，ENVI软件输出

---

## 重采样方法选择指南

| 数据类型 | 特征 | 推荐方法 | 原因 |
|----------|------|----------|------|
| 土地利用 | 整数，少量唯一值 | 最近邻 | 保持类别不变 |
| 高程模型 | 浮点，连续变化 | 双线性 | 平滑插值 |
| 温度数据 | 浮点，空间相关 | 双线性 | 保持连续性 |
| 降水数据 | 浮点，累积值 | 求和法 | 保持总量 |
| 分类影像 | 整数，离散值 | 最近邻 | 避免产生新类别 |
| NDVI | 浮点，-1到1 | 双线性 | 保持指数含义 |
| 坡度坡向 | 浮点，派生数据 | 双线性 | 保持地形特征 |
| 人口密度 | 浮点，密度值 | 求和法 | 保持总量 |

**自动判断逻辑：**
```python
def determine_resampling(data, dtype):
    """根据数据特性判断重采样方法"""

    # 1. 整数类型 + 唯一值少 → 分类数据
    if np.issubdtype(dtype, np.integer):
        unique_count = len(np.unique(data[data != 0]))
        if unique_count < 50:  # 少于50个唯一值
            return 'nearest'

    # 2. 浮点类型 → 连续数据
    if np.issubdtype(dtype, np.floating):
        return 'bilinear'

    # 3. 默认最近邻
    return 'nearest'
```
