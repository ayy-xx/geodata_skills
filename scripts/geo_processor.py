"""
地理数据处理核心工具
集成栅格处理、矢量处理、坐标转换等功能
"""

import os
import numpy as np
import rasterio
import geopandas as gpd
from pyproj import Transformer
from datetime import datetime


class GeoProcessor:
    """地理数据处理器"""

    def __init__(self):
        """初始化处理器"""
        self.supported_raster = ['.tif', '.tiff', '.img', '.dat', '.nc', '.h5', '.hdf5', '.asc']
        self.supported_vector = ['.shp', '.geojson', '.json', '.gpkg', '.kml', '.kmz', '.gml']

    def detect_format(self, filepath):
        """
        检测数据格式

        参数:
            filepath: 文件路径

        返回:
            dict: 格式信息
        """
        ext = os.path.splitext(filepath)[1].lower()

        if ext in self.supported_raster:
            return self._detect_raster(filepath, ext)
        elif ext in self.supported_vector:
            return self._detect_vector(filepath, ext)
        else:
            return {
                'type': 'unknown',
                'format': ext,
                'error': f'不支持的文件格式: {ext}'
            }

    def _detect_raster(self, filepath, ext):
        """检测栅格数据信息"""
        try:
            with rasterio.open(filepath) as src:
                return {
                    'type': 'raster',
                    'format': ext,
                    'path': filepath,
                    'size': os.path.getsize(filepath),
                    'width': src.width,
                    'height': src.height,
                    'count': src.count,
                    'dtype': src.dtypes[0],
                    'crs': str(src.crs),
                    'epsg': src.crs.to_epsg() if src.crs else None,
                    'bounds': {
                        'west': src.bounds.left,
                        'south': src.bounds.bottom,
                        'east': src.bounds.right,
                        'north': src.bounds.top
                    },
                    'transform': {
                        'xres': abs(src.transform.a),
                        'yres': abs(src.transform.e)
                    },
                    'nodata': src.nodata
                }
        except Exception as e:
            return {
                'type': 'raster',
                'format': ext,
                'path': filepath,
                'error': str(e)
            }

    def _detect_vector(self, filepath, ext):
        """检测矢量数据信息"""
        try:
            gdf = gpd.read_file(filepath)
            bounds = gdf.total_bounds

            return {
                'type': 'vector',
                'format': ext,
                'path': filepath,
                'size': os.path.getsize(filepath),
                'features': len(gdf),
                'geometry_type': gdf.geometry.geom_type.unique().tolist(),
                'columns': gdf.columns.tolist(),
                'crs': str(gdf.crs),
                'epsg': gdf.crs.to_epsg() if gdf.crs else None,
                'bounds': {
                    'west': float(bounds[0]),
                    'south': float(bounds[1]),
                    'east': float(bounds[2]),
                    'north': float(bounds[3])
                }
            }
        except Exception as e:
            return {
                'type': 'vector',
                'format': ext,
                'path': filepath,
                'error': str(e)
            }

    def transform_coordinates(self, x, y, from_epsg, to_epsg):
        """
        坐标转换

        参数:
            x: 经度或X坐标
            y: 纬度或Y坐标
            from_epsg: 源坐标系EPSG代码
            to_epsg: 目标坐标系EPSG代码

        返回:
            tuple: 转换后的坐标 (x, y)
        """
        transformer = Transformer.from_crs(f"EPSG:{from_epsg}", f"EPSG:{to_epsg}", always_xy=True)
        return transformer.transform(x, y)

    def batch_transform_coordinates(self, x_list, y_list, from_epsg, to_epsg):
        """
        批量坐标转换

        参数:
            x_list: X坐标列表
            y_list: Y坐标列表
            from_epsg: 源坐标系EPSG代码
            to_epsg: 目标坐标系EPSG代码

        返回:
            tuple: 转换后的坐标列表 (x_list, y_list)
        """
        transformer = Transformer.from_crs(f"EPSG:{from_epsg}", f"EPSG:{to_epsg}", always_xy=True)
        return transformer.transform(x_list, y_list)

    def get_utm_epsg(self, lon, lat):
        """
        根据经纬度获取UTM带号

        参数:
            lon: 经度
            lat: 纬度

        返回:
            int: EPSG代码
        """
        zone = int((lon + 180) / 6) + 1
        hemisphere = 'north' if lat >= 0 else 'south'

        if hemisphere == 'north':
            return 32600 + zone
        else:
            return 32700 + zone

    def clip_raster_by_vector(self, raster_path, vector_path, output_path):
        """
        使用矢量裁剪栅格

        参数:
            raster_path: 栅格文件路径
            vector_path: 矢量文件路径
            output_path: 输出文件路径

        返回:
            str: 输出文件路径
        """
        import rasterio.mask

        gdf = gpd.read_file(vector_path)

        with rasterio.open(raster_path) as src:
            # 确保矢量和栅格坐标系一致
            if gdf.crs != src.crs:
                gdf = gdf.to_crs(src.crs)

            out_image, out_transform = rasterio.mask.mask(src, gdf.geometry, crop=True)
            out_meta = src.meta.copy()

            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })

            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_image)

        return output_path

    def reproject_raster(self, input_path, output_path, target_epsg, resampling='nearest'):
        """
        重投影栅格

        参数:
            input_path: 输入文件路径
            output_path: 输出文件路径
            target_epsg: 目标坐标系EPSG代码
            resampling: 重采样方法

        返回:
            str: 输出文件路径
        """
        from rasterio.warp import calculate_default_transform, reproject, Resampling

        resampling_methods = {
            'nearest': Resampling.nearest,
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'average': Resampling.average,
            'mode': Resampling.mode
        }

        with rasterio.open(input_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, f"EPSG:{target_epsg}", src.width, src.height, *src.bounds
            )

            kwargs = src.meta.copy()
            kwargs.update({
                'crs': f"EPSG:{target_epsg}",
                'transform': transform,
                'width': width,
                'height': height
            })

            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=f"EPSG:{target_epsg}",
                        resampling=resampling_methods.get(resampling, Resampling.nearest)
                    )

        return output_path

    def reproject_vector(self, input_path, output_path, target_epsg):
        """
        重投影矢量

        参数:
            input_path: 输入文件路径
            output_path: 输出文件路径
            target_epsg: 目标坐标系EPSG代码

        返回:
            str: 输出文件路径
        """
        gdf = gpd.read_file(input_path)
        gdf = gdf.to_crs(epsg=target_epsg)

        # 根据输出扩展名选择驱动
        ext = os.path.splitext(output_path)[1].lower()
        drivers = {
            '.shp': 'ESRI Shapefile',
            '.geojson': 'GeoJSON',
            '.gpkg': 'GPKG',
            '.kml': 'KML'
        }
        driver = drivers.get(ext, 'GPKG')

        gdf.to_file(output_path, driver=driver)
        return output_path

    def calculate_statistics(self, raster_path, band=1):
        """
        计算栅格统计信息

        参数:
            raster_path: 栅格文件路径
            band: 波段号

        返回:
            dict: 统计信息
        """
        with rasterio.open(raster_path) as src:
            data = src.read(band)
            nodata = src.nodata

            if nodata is not None:
                valid_data = data[data != nodata]
            else:
                valid_data = data.flatten()

            # 移除NaN
            valid_data = valid_data[~np.isnan(valid_data.astype(float))]

            if len(valid_data) == 0:
                return {
                    'count': 0,
                    'min': None,
                    'max': None,
                    'mean': None,
                    'std': None,
                    'nodata': nodata
                }

            return {
                'count': len(valid_data),
                'min': float(np.min(valid_data)),
                'max': float(np.max(valid_data)),
                'mean': float(np.mean(valid_data)),
                'std': float(np.std(valid_data)),
                'median': float(np.median(valid_data)),
                'percentile_25': float(np.percentile(valid_data, 25)),
                'percentile_75': float(np.percentile(valid_data, 75)),
                'nodata': nodata
            }

    def validate_raster(self, raster_path):
        """
        验证栅格数据质量

        参数:
            raster_path: 栅格文件路径

        返回:
            dict: 验证结果
        """
        issues = []

        try:
            with rasterio.open(raster_path) as src:
                # 检查坐标系
                if src.crs is None:
                    issues.append("缺少坐标系信息")

                # 检查nodata
                if src.nodata is None:
                    issues.append("未定义nodata值")

                # 检查数据范围
                for i in range(1, src.count + 1):
                    data = src.read(i)
                    if np.all(np.isnan(data.astype(float))):
                        issues.append(f"波段{i}全部为NaN")

                    if src.nodata is not None:
                        nodata_ratio = np.sum(data == src.nodata) / data.size
                        if nodata_ratio > 0.5:
                            issues.append(f"波段{i} nodata比例过高: {nodata_ratio:.2%}")

                # 检查变换矩阵
                if src.transform.a == 0 or src.transform.e == 0:
                    issues.append("分辨率异常")

            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'path': raster_path
            }

        except Exception as e:
            return {
                'valid': False,
                'issues': [str(e)],
                'path': raster_path
            }

    def merge_rasters(self, input_paths, output_path):
        """
        合并多个栅格

        参数:
            input_paths: 输入文件路径列表
            output_path: 输出文件路径

        返回:
            str: 输出文件路径
        """
        from rasterio.merge import merge

        src_files = [rasterio.open(p) for p in input_paths]
        mosaic, out_trans = merge(src_files)

        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans
        })

        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(mosaic)

        # 关闭源文件
        for src in src_files:
            src.close()

        return output_path

    def resample_raster(self, input_path, output_path, target_resolution, resampling='nearest'):
        """
        重采样栅格到目标分辨率

        参数:
            input_path: 输入文件路径
            output_path: 输出文件路径
            target_resolution: 目标分辨率 (xres, yres)
            resampling: 重采样方法

        返回:
            str: 输出文件路径
        """
        from rasterio.warp import reproject, Resampling

        resampling_methods = {
            'nearest': Resampling.nearest,
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'average': Resampling.average
        }

        with rasterio.open(input_path) as src:
            # 计算新的尺寸
            new_width = int((src.bounds.right - src.bounds.left) / target_resolution[0])
            new_height = int((src.bounds.top - src.bounds.bottom) / target_resolution[1])

            # 创建新的变换矩阵
            from rasterio.transform import from_bounds
            new_transform = from_bounds(
                src.bounds.left, src.bounds.bottom,
                src.bounds.right, src.bounds.top,
                new_width, new_height
            )

            kwargs = src.meta.copy()
            kwargs.update({
                'transform': new_transform,
                'width': new_width,
                'height': new_height
            })

            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=new_transform,
                        dst_crs=src.crs,
                        resampling=resampling_methods.get(resampling, Resampling.nearest)
                    )

        return output_path


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='地理数据处理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # detect命令
    detect_parser = subparsers.add_parser('detect', help='检测数据格式')
    detect_parser.add_argument('input', help='输入文件路径')

    # transform命令
    transform_parser = subparsers.add_parser('transform', help='坐标转换')
    transform_parser.add_argument('input', help='输入文件路径')
    transform_parser.add_argument('output', help='输出文件路径')
    transform_parser.add_argument('--target-epsg', type=int, required=True, help='目标EPSG代码')

    # clip命令
    clip_parser = subparsers.add_parser('clip', help='矢量裁剪栅格')
    clip_parser.add_argument('raster', help='栅格文件路径')
    clip_parser.add_argument('vector', help='矢量文件路径')
    clip_parser.add_argument('output', help='输出文件路径')

    # stats命令
    stats_parser = subparsers.add_parser('stats', help='计算统计信息')
    stats_parser.add_argument('input', help='输入文件路径')

    # validate命令
    validate_parser = subparsers.add_parser('validate', help='验证数据质量')
    validate_parser.add_argument('input', help='输入文件路径')

    args = parser.parse_args()

    processor = GeoProcessor()

    if args.command == 'detect':
        result = processor.detect_format(args.input)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == 'transform':
        output = processor.reproject_raster(args.input, args.output, args.target_epsg)
        print(f"转换完成: {output}")

    elif args.command == 'clip':
        output = processor.clip_raster_by_vector(args.raster, args.vector, args.output)
        print(f"裁剪完成: {output}")

    elif args.command == 'stats':
        stats = processor.calculate_statistics(args.input)
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif args.command == 'validate':
        result = processor.validate_raster(args.input)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == '__main__':
    import json
    main()
