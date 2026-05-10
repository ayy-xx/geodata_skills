---
name: geodata
description: 地理数据处理工具，支持栅格对齐、空间分析、坐标转换、地图可视化，包含数据抽检质量控制流程
metadata:
    skill-author: Claude
---

# Geodata 地理数据处理

## 概述

专业的地理数据处理工具，支持矢量和栅格数据的读取、分析、转换和可视化。核心特色是**栅格智能对齐**和**数据抽检**功能，确保数据处理的准确性和一致性。

**核心能力：**
- 栅格数据智能对齐（自动选择重采样方法）
- 批量处理 + 抽检质量控制
- 矢量/栅格数据读取与格式转换
- 坐标系识别与转换
- 空间分析（缓冲区、叠加、插值等）
- 地图可视化（静态 + 交互式）

---

## 使用场景

当用户需要：
- 对齐多个栅格图层到统一的空间参考
- 批量处理时间序列栅格数据（如月度、年度）
- 进行地理空间分析
- 制作地图可视化
- 转换坐标系或数据格式
- 质量检查地理数据

---

## 支持的数据格式

### 矢量数据
| 格式 | 扩展名 | 说明 |
|------|--------|------|
| Shapefile | .shp | 最常用矢量格式 |
| GeoJSON | .geojson, .json | Web友好格式 |
| KML/KMZ | .kml, .kmz | Google Earth格式 |
| GeoPackage | .gpkg | OGC标准格式 |
| GML | .gml | 地理标记语言 |

### 栅格数据
| 格式 | 扩展名 | 说明 |
|------|--------|------|
| GeoTIFF | .tif, .tiff | 最常用栅格格式 |
| NetCDF | .nc, .nc4 | 科学数据格式 |
| HDF5 | .h5, .hdf5 | 层次数据格式 |
| ASCII Grid | .asc | 文本格式栅格 |
| ENVI | .dat | 遥感常用格式 |

---

## 核心功能模块

### 模块一：栅格对齐（Raster Alignment）

**功能：** 将多个栅格图层对齐到统一的空间参考（范围、分辨率、坐标系）

**使用方式：**
```
用户输入：
- 基准图层路径（reference raster）
- 待对齐图层路径（一个或多个）
- 可选：输出路径、重采样方法
```

**智能重采样选择：**

| 数据类型 | 推荐方法 | Python参数 | 适用场景 |
|----------|----------|------------|----------|
| 分类数据 | 最近邻法 | `resampling=nearest` | 土地利用、植被类型、行政区域 |
| 连续数据 | 双线性插值 | `resampling=bilinear` | 高程、温度、降水、NDVI |
| 累积数据 | 求和法 | `resampling=sum` | 降水量累计、人口密度 |
| 标签数据 | 模式法 | `resampling=mode` | 多数投票分类 |

**自动判断逻辑：**
1. 检查数据值类型（整数 vs 浮点）
2. 检查唯一值数量（少量唯一值 → 分类数据）
3. 检查数据来源元数据
4. **不确定时询问用户**

**对齐流程：**
```
Step 1: 读取基准图层的空间信息
        - 范围（bounds）
        - 分辨率（resolution）
        - 坐标系（CRS）
        - 形状（shape）

Step 2: 分析待对齐图层的数据特性
        - 数据类型（int/float）
        - 唯一值统计
        - 值域范围

Step 3: 确定重采样方法
        - 自动推荐 或 询问用户

Step 4: 执行对齐
        - 使用rasterio.warp.reproject
        - 保持基准图层的transform

Step 5: 验证对齐结果
        - 检查shape是否一致
        - 检查bounds是否一致
        - 检查nodata处理
```

**代码模板：**
```python
import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np

def align_raster(reference_path, source_path, output_path, resampling_method='auto'):
    """
    将栅格对齐到基准图层

    参数:
        reference_path: 基准图层路径
        source_path: 待对齐图层路径
        output_path: 输出路径
        resampling_method: 'nearest', 'bilinear', 'auto'
    """
    # 读取基准图层
    with rasterio.open(reference_path) as ref:
        ref_profile = ref.profile.copy()
        ref_transform = ref.transform
        ref_crs = ref.crs
        ref_shape = (ref.height, ref.width)
        ref_bounds = ref.bounds

    # 读取源图层
    with rasterio.open(source_path) as src:
        src_data = src.read(1)
        src_nodata = src.nodata
        src_dtype = src.dtypes[0]

        # 自动判断重采样方法
        if resampling_method == 'auto':
            resampling_method = determine_resampling(src_data, src_dtype)

        # 准备输出profile
        out_profile = ref_profile.copy()
        out_profile.update(dtype=src_dtype, count=1)

        # 执行重投影
        with rasterio.open(output_path, 'w', **out_profile) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling[resampling_method]
            )

    return output_path, resampling_method

def determine_resampling(data, dtype):
    """
    根据数据特性自动判断重采样方法

    返回: 'nearest' 或 'bilinear'
    """
    # 整数数据且唯一值较少 → 分类数据 → 最近邻
    if np.issubdtype(dtype, np.integer):
        unique_ratio = len(np.unique(data)) / data.size
        if unique_ratio < 0.01:  # 唯一值占比小于1%
            return 'nearest'

    # 浮点数据 → 连续数据 → 双线性
    if np.issubdtype(dtype, np.floating):
        return 'bilinear'

    # 默认使用最近邻（更安全）
    return 'nearest'
```

---

### 模块二：数据抽检（Quality Sampling）

**功能：** 批量生成数据后，通过抽检验证数据质量

**使用场景：**
- 生成12个月的NDVI数据后，抽检某个月份
- 批量处理多年降水数据后，抽检某一年
- 生成多个站点数据后，抽检部分站点

**抽检流程：**
```
Step 1: 批量生成
        - 按用户需求批量处理数据
        - 保存到指定目录

Step 2: 选择抽检样本
        - 用户指定 或 随机选择
        - 记录抽检项目

Step 3: 独立重新生成
        - 对抽检样本单独重新处理
        - 保存到临时目录（如 _sampling_temp/）

Step 4: 对比验证
        - 逐像元比较批量结果和抽检结果
        - 计算差异统计（最大差异、均值差异、RMSE）
        - 生成验证报告

Step 5: 用户确认
        - 展示验证结果
        - 用户确认通过/不通过

Step 6: 清理
        - 通过：删除临时抽检数据
        - 不通过：保留数据供排查，提示可能问题
```

**代码模板：**
```python
import os
import numpy as np
import rasterio
from datetime import datetime

class SamplingValidator:
    """数据抽检验证器"""

    def __init__(self, batch_dir, sampling_dir='_sampling_temp'):
        self.batch_dir = batch_dir
        self.sampling_dir = sampling_dir
        os.makedirs(sampling_dir, exist_ok=True)

    def select_samples(self, file_list, n_samples=1, method='user', user_choice=None):
        """
        选择抽检样本

        参数:
            file_list: 批量文件列表
            n_samples: 抽检数量
            method: 'user'(用户指定) 或 'random'(随机)
            user_choice: 用户指定的文件名
        """
        if method == 'user' and user_choice:
            samples = [f for f in file_list if user_choice in f]
        else:
            import random
            samples = random.sample(file_list, min(n_samples, len(file_list)))

        return samples

    def compare_rasters(self, batch_file, sampling_file):
        """
        对比两个栅格文件

        返回: 差异统计字典
        """
        with rasterio.open(batch_file) as src1:
            data1 = src1.read(1)
            nodata1 = src1.nodata

        with rasterio.open(sampling_file) as src2:
            data2 = src2.read(1)
            nodata2 = src2.nodata

        # 排除nodata
        if nodata1 is not None:
            mask = (data1 != nodata1) & (data2 != nodata2)
        else:
            mask = np.ones_like(data1, dtype=bool)

        if mask.sum() == 0:
            return {'error': 'No valid data to compare'}

        diff = data1[mask].astype(float) - data2[mask].astype(float)

        return {
            'batch_file': batch_file,
            'sampling_file': sampling_file,
            'valid_pixels': mask.sum(),
            'max_diff': float(np.max(np.abs(diff))),
            'mean_diff': float(np.mean(diff)),
            'std_diff': float(np.std(diff)),
            'rmse': float(np.sqrt(np.mean(diff**2))),
            'identical': bool(np.allclose(data1[mask], data2[mask], atol=1e-6)),
            'timestamp': datetime.now().isoformat()
        }

    def validate(self, sample_files, regenerate_func):
        """
        执行完整抽检流程

        参数:
            sample_files: 需要抽检的文件列表
            regenerate_func: 重新生成数据的函数
        """
        results = []

        for sample_file in sample_files:
            # 1. 重新生成
            print(f"抽检重新生成: {sample_file}")
            sampling_file = regenerate_func(sample_file, self.sampling_dir)

            # 2. 对比
            batch_path = os.path.join(self.batch_dir, sample_file)
            result = self.compare_rasters(batch_path, sampling_file)
            results.append(result)

            # 3. 输出结果
            if result.get('identical'):
                print(f"  ✓ 验证通过 - 数据完全一致")
            else:
                print(f"  ⚠ 存在差异 - RMSE: {result.get('rmse', 'N/A')}")

        return results

    def cleanup(self):
        """清理抽检临时目录"""
        import shutil
        if os.path.exists(self.sampling_dir):
            shutil.rmtree(self.sampling_dir)
            print(f"已清理临时目录: {self.sampling_dir}")

    def generate_report(self, results, output_path='sampling_report.md'):
        """生成抽检报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 数据抽检验证报告\n\n")
            f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 验证结果汇总\n\n")
            f.write("| 文件 | 状态 | RMSE | 最大差异 |\n")
            f.write("|------|------|------|----------|\n")

            for r in results:
                status = "✓ 通过" if r.get('identical') else "⚠ 有差异"
                f.write(f"| {r.get('batch_file', 'N/A')} | {status} | {r.get('rmse', 'N/A'):.6f} | {r.get('max_diff', 'N/A'):.6f} |\n")

            f.write("\n## 详细信息\n\n")
            for i, r in enumerate(results, 1):
                f.write(f"### 样本 {i}\n")
                f.write(f"- 批量文件: {r.get('batch_file')}\n")
                f.write(f"- 抽检文件: {r.get('sampling_file')}\n")
                f.write(f"- 有效像元: {r.get('valid_pixels')}\n")
                f.write(f"- 平均差异: {r.get('mean_diff', 'N/A'):.6f}\n")
                f.write(f"- 标准差: {r.get('std_diff', 'N/A'):.6f}\n\n")

        return output_path
```

---

### 模块三：坐标转换（Coordinate Transformation）

**支持的坐标系：**
- WGS84 (EPSG:4326) - GPS坐标系
- CGCS2000 (EPSG:4490) - 中国大地坐标系
- UTM各带 (EPSG:326xx/327xx) - 通用横轴墨卡托
- Web Mercator (EPSG:3857) - Web地图常用
- GCJ-02 / BD-09 - 中国地图偏移坐标系

**使用方式：**
```python
from pyproj import Transformer

def transform_coordinates(x, y, from_crs, to_crs):
    """坐标转换"""
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    return transformer.transform(x, y)
```

---

### 模块四：空间分析（Spatial Analysis）

**支持的分析类型：**

| 分析类型 | 函数 | 说明 |
|----------|------|------|
| 缓冲区 | `buffer_analysis()` | 点/线/面生成缓冲区 |
| 叠加分析 | `overlay_analysis()` | 交集、并集、裁剪 |
| 邻近分析 | `nearest_analysis()` | 最近距离计算 |
| 空间插值 | `interpolation()` | IDW、Kriging插值 |
| 空间统计 | `spatial_stats()` | Moran's I、热点分析 |

---

### 模块五：地图可视化（Map Visualization）

**静态地图（matplotlib + cartopy）：**
```python
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

def plot_static_map(data, bounds, title, output_path):
    """生成静态地图"""
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
    ax.imshow(data, extent=bounds, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_title(title)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
```

**交互式地图（folium）：**
```python
import folium

def plot_interactive_map(center, layers, output_path):
    """生成交互式HTML地图"""
    m = folium.Map(location=center, zoom_start=10)
    for layer in layers:
        folium.GeoJson(layer).add_to(m)
    m.save(output_path)
```

---

## 工作流程

### 标准流程
```
1. 项目初始化
   ├── 创建项目文件夹
   ├── 初始化Git仓库 (git init)
   ├── 创建 .gitignore
   └── 创建目录结构 (scripts/, data/, output/, docs/)

2. 数据检测
   ├── 识别文件格式
   ├── 读取坐标系
   ├── 获取空间范围
   └── 检查数据质量

3. 代码开发与版本控制
   ├── 编写Python处理脚本
   ├── 添加用途说明（文件头注释）
   ├── 多版本添加时间戳命名
   ├── Git提交 (git add + git commit)
   └── 记录变更日志

4. 数据处理
   ├── 坐标转换（如需要）
   ├── 栅格对齐（如多图层）
   ├── 空间分析（按需求）
   └── 格式转换（如需要）

5. 质量控制
   ├── 批量处理完成
   ├── 选择抽检样本
   ├── 独立重新生成
   ├── 对比验证
   └── 用户确认

6. 输出与归档
   ├── 生成结果数据
   ├── 生成可视化地图
   ├── 生成分析报告
   ├── Git最终提交
   └── 清理临时文件
```

---

## 交互规范

### 项目初始化与Git版本控制

**强制要求：** 每个新项目必须在项目文件夹中创建Git仓库，所有Python代码必须纳入版本控制。

#### 项目目录结构
```
project_name/
├── .git/                   # Git仓库
├── .gitignore              # Git忽略规则
├── scripts/                # Python处理脚本
│   ├── process_20240101.py # 带时间戳的版本
│   ├── process_20240115.py # 更新版本
│   └── utils.py           # 工具函数
├── data/                   # 原始数据（通常不纳入Git）
├── output/                 # 输出结果
│   ├── aligned/           # 对齐后的栅格
│   ├── sampling/          # 抽检数据
│   └── reports/           # 验证报告
└── docs/                   # 文档
    └── processing_log.md  # 处理日志
```

#### .gitignore 模板
```gitignore
# 数据文件（大文件不纳入Git）
*.tif
*.tiff
*.nc
*.h5
*.hdf5
*.shp
*.shx
*.dbf
*.prj

# 临时文件
_sampling_temp/
*.tmp
__pycache__/
*.pyc

# 输出大文件
output/data/

# 系统文件
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

#### Python脚本规范

**文件头注释模板：**
```python
"""
脚本名称：process_monthly_ndvi.py
用途：处理月度NDVI数据，包括裁剪、重投影、对齐
作者：[用户姓名]
创建时间：2024-01-15
最后更新：2024-01-20

输入：
    - data/raw/ndvi_monthly/*.tif - 原始月度NDVI数据
    - data/reference/study_area.shp - 研究区域矢量

输出：
    - output/aligned/ndvi_*.tif - 对齐后的NDVI数据
    - output/reports/alignment_report.md - 对齐报告

依赖：
    - rasterio >= 1.3.0
    - geopandas >= 0.12.0
    - numpy >= 1.24.0

版本历史：
    v1.0 (2024-01-15) - 初始版本，基本裁剪和重投影
    v1.1 (2024-01-18) - 添加智能重采样选择
    v1.2 (2024-01-20) - 添加数据抽检验证
"""
```

**多版本命名规则：**
```
脚本名_YYYYMMDD.py 或 脚本名_v1.0_YYYYMMDD.py

示例：
- process_ndvi_20240115.py        # 2024年1月15日版本
- process_ndvi_20240120.py        # 2024年1月20日版本（更新）
- process_ndvi_v2.0_20240201.py   # 2.0版本
```

**代码内版本注释：**
```python
# 版本: 1.2
# 更新日期: 2024-01-20
# 更新内容: 添加数据抽检验证功能

def process_data(input_path, output_path):
    """
    处理数据函数

    版本历史:
        1.0 (2024-01-15) - 初始实现
        1.1 (2024-01-18) - 添加错误处理
        1.2 (2024-01-20) - 添加进度显示
    """
    pass
```

#### Git提交规范

**强制要求：** 每次代码更新完成后，必须询问用户是否提交到Git仓库，用户确认后再执行提交。

**交互流程：**
```
代码更新完成后，询问用户：

脚本 [filename] 已更新完成。

是否提交到Git仓库？
1. 是 - 提交并添加提交信息
2. 否 - 仅保存文件，不提交
3. 查看变更 - 先查看diff再决定

请选择 [1/2/3]:
```

**提交信息格式：**
```
<类型>: <简短描述>

<详细说明（可选）>

<关联信息（可选）>
```

**类型说明：**
| 类型 | 说明 | 示例 |
|------|------|------|
| feat | 新功能 | feat: 添加栅格对齐功能 |
| fix | 修复bug | fix: 修复坐标转换精度问题 |
| docs | 文档更新 | docs: 更新使用说明 |
| style | 代码格式 | style: 格式化代码 |
| refactor | 重构 | refactor: 重构抽检验证模块 |
| perf | 性能优化 | perf: 优化大文件处理 |
| test | 测试 | test: 添加单元测试 |
| chore | 构建/工具 | chore: 更新依赖 |

**提交示例：**
```bash
# 用户确认后提交
git add scripts/process_ndvi_20240115.py
git commit -m "feat: 添加NDVI月度数据处理脚本

- 实现批量裁剪和重投影
- 支持智能重采样选择
- 添加数据抽检验证"
```

#### 版本标签规范

**标签格式：** `v<主版本>.<次版本>.<修订号>_<日期>`

```bash
# 创建版本标签
git tag -a v1.0_20240115 -m "初始版本：基本数据处理功能"
git tag -a v1.1_20240120 -m "添加智能重采样选择"
git tag -a v2.0_20240201 -m "重大更新：添加完整抽检流程"
```

#### 处理日志模板

**docs/processing_log.md：**
```markdown
# 数据处理日志

## 项目信息
- 项目名称：[项目名]
- 开始日期：2024-01-15
- 负责人：[姓名]

## 处理记录

### 2024-01-15
- **脚本**：process_ndvi_20240115.py
- **功能**：原始数据裁剪和重投影
- **输入**：12个月NDVI原始数据
- **输出**：裁剪后的12个月数据
- **Git提交**：`a1b2c3d feat: 添加NDVI月度数据处理脚本`
- **备注**：初始版本

### 2024-01-18
- **脚本**：process_ndvi_20240118.py
- **功能**：添加智能重采样选择
- **修改内容**：
  - 根据数据类型自动选择重采样方法
  - 分类数据使用最近邻法
  - 连续数据使用双线性插值
- **Git提交**：`e4f5g6h feat: 更新NDVI处理脚本v1.1`

### 2024-01-20
- **脚本**：process_ndvi_20240120.py
- **功能**：添加数据抽检验证
- **抽检结果**：
  - 抽检月份：5月
  - RMSE：0.000001
  - 状态：通过
- **Git提交**：`i7j8k9l feat: 添加数据抽检验证`
- **备注**：抽检通过后删除临时数据
```

#### Git操作命令参考

```bash
# 初始化项目（项目开始时执行一次）
cd /path/to/project
git init
git add .gitignore
git commit -m "chore: 初始化项目结构"

# 添加新脚本（用户确认后）
git add scripts/process_ndvi_20240115.py
git commit -m "feat: 添加NDVI处理脚本"

# 更新脚本 - 保存新版本
cp scripts/process_ndvi_20240115.py scripts/process_ndvi_20240120.py
# 编辑新版本...

# 查看变更（供用户决策）
git diff scripts/process_ndvi_20240115.py scripts/process_ndvi_20240120.py
git status

# 用户确认后提交
git add scripts/process_ndvi_20240120.py
git commit -m "feat: 更新NDVI处理脚本v1.2"

# 查看版本历史
git log --oneline
git log --oneline --graph

# 查看某个文件的历史
git log --follow scripts/process_ndvi_*.py

# 创建版本标签（用户确认后）
git tag -a v1.0_20240115 -m "初始版本"

# 查看所有标签
git tag -l

# 回滚到某个版本（谨慎使用，需用户确认）
git checkout v1.0_20240115 -- scripts/process_ndvi_20240115.py

# 比较两个版本的差异
git diff v1.0_20240115..v1.1_20240120 -- scripts/
```

**重要提醒：**
- 不要自动执行 `git add` 和 `git commit`
- 每次代码更新后询问用户是否提交
- 用户可以选择查看diff后再决定
- 用户可以跳过提交，仅保存文件

### 重采样方法确认
当无法自动判断时，询问用户：
```
检测到图层 [文件名] 的数据特征：
- 数据类型：整数/浮点
- 唯一值数量：N个
- 值域范围：X - Y

建议使用：
1. 最近邻法 - 适用于分类数据（如土地利用类型）
2. 双线性插值 - 适用于连续数据（如高程、温度）

请选择 [1/2]，或输入其他重采样方法：
```

### 抽检确认
```
批量处理完成，共生成 N 个文件。

请选择抽检方式：
1. 指定抽检文件（输入文件名关键词）
2. 随机抽检（输入抽检数量）
3. 跳过抽检

请选择 [1/2/3]：
```

### 抽检结果确认
```
抽检验证结果：
- 抽检文件：xxx.tif
- 状态：✓ 通过 / ⚠ 存在差异
- RMSE：0.000001
- 最大差异：0.0001

是否确认通过？
1. 确认通过（删除抽检临时数据）
2. 不通过（保留数据供排查）
```

---

## 依赖库

```python
# 核心库
rasterio>=1.3.0        # 栅格处理
geopandas>=0.12.0      # 矢量处理
pyproj>=3.4.0          # 坐标转换
shapely>=2.0.0         # 几何操作
fiona>=1.8.0           # 矢量IO

# 分析库
numpy>=1.24.0          # 数值计算
scipy>=1.10.0          # 科学计算
pysal>=23.0            # 空间统计

# 可视化库
matplotlib>=3.6.0      # 绑图
cartopy>=0.21.0        # 地图投影
folium>=0.14.0         # 交互地图

# 可选库
netCDF4>=1.6.0         # NetCDF支持
h5py>=3.8.0            # HDF5支持
```

---

## 常见问题

### Q: 如何处理大文件？
使用分块处理：
```python
with rasterio.open('large.tif') as src:
    for ji, window in src.block_windows(1):
        data = src.read(1, window=window)
        # 处理数据
```

### Q: 如何处理坐标系不一致？
先统一坐标系再处理：
```python
import geopandas as gpd
gdf = gdf.to_crs(epsg=4326)  # 转换到WGS84
```

### Q: 如何处理nodata值？
检查并统一nodata：
```python
with rasterio.open('data.tif') as src:
    nodata = src.nodata
    data = src.read(1)
    data[data == nodata] = np.nan  # 转换为NaN
```

---

## 资源目录

### scripts/
- `geo_processor.py` - 核心处理脚本
- `raster_align.py` - 栅格对齐工具
- `sampling_validator.py` - 抽检验证工具
- `map_generator.py` - 地图生成工具

### references/
- `raster_formats.md` - 栅格格式参考
- `vector_formats.md` - 矢量格式参考
- `coordinate_systems.md` - 坐标系参考

### assets/
- `report_template.md` - 报告模板
