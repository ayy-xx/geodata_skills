"""
栅格对齐工具
将多个栅格图层对齐到统一的空间参考
"""

import os
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import from_bounds
from datetime import datetime


class RasterAligner:
    """栅格对齐器"""

    # 支持的重采样方法
    RESAMPLING_METHODS = {
        'nearest': Resampling.nearest,
        'bilinear': Resampling.bilinear,
        'cubic': Resampling.cubic,
        'cubic_spline': Resampling.cubic_spline,
        'lanczos': Resampling.lanczos,
        'average': Resampling.average,
        'mode': Resampling.mode,
        'sum': Resampling.sum
    }

    def __init__(self, reference_path):
        """
        初始化对齐器

        参数:
            reference_path: 基准栅格文件路径
        """
        self.reference_path = reference_path
        self.ref_profile = None
        self.ref_bounds = None
        self.ref_crs = None
        self.ref_transform = None
        self.ref_shape = None

        self._load_reference()

    def _load_reference(self):
        """加载基准栅格信息"""
        with rasterio.open(self.reference_path) as ref:
            self.ref_profile = ref.profile.copy()
            self.ref_bounds = ref.bounds
            self.ref_crs = ref.crs
            self.ref_transform = ref.transform
            self.ref_shape = (ref.height, ref.width)

        print(f"基准栅格信息:")
        print(f"  路径: {self.reference_path}")
        print(f"  尺寸: {self.ref_shape[1]} x {self.ref_shape[0]} (宽x高)")
        print(f"  范围: {self.ref_bounds}")
        print(f"  坐标系: {self.ref_crs}")
        print(f"  分辨率: {abs(self.ref_transform.a):.6f} x {abs(self.ref_transform.e):.6f}")

    def analyze_data_characteristics(self, data_path):
        """
        分析栅格数据特性

        返回: 数据特性字典
        """
        with rasterio.open(data_path) as src:
            data = src.read(1)
            nodata = src.nodata
            dtype = src.dtypes[0]

            # 排除nodata值进行分析
            if nodata is not None:
                valid_data = data[data != nodata]
            else:
                valid_data = data.flatten()

            if len(valid_data) == 0:
                return {
                    'dtype': dtype,
                    'nodata': nodata,
                    'unique_count': 0,
                    'unique_ratio': 0,
                    'is_integer': np.issubdtype(dtype, np.integer),
                    'is_float': np.issubdtype(dtype, np.floating),
                    'min': None,
                    'max': None,
                    'mean': None,
                    'std': None
                }

            unique_count = len(np.unique(valid_data))
            unique_ratio = unique_count / len(valid_data)

            return {
                'dtype': dtype,
                'nodata': nodata,
                'unique_count': unique_count,
                'unique_ratio': unique_ratio,
                'is_integer': np.issubdtype(dtype, np.integer),
                'is_float': np.issubdtype(dtype, np.floating),
                'min': float(np.nanmin(valid_data)),
                'max': float(np.nanmax(valid_data)),
                'mean': float(np.nanmean(valid_data)),
                'std': float(np.nanstd(valid_data))
            }

    def recommend_resampling(self, data_path, threshold=0.01):
        """
        根据数据特性推荐重采样方法

        参数:
            data_path: 数据文件路径
            threshold: 唯一值比例阈值，低于此值认为是分类数据

        返回:
            recommended_method: 推荐的重采样方法
            reason: 推荐原因
            needs_confirmation: 是否需要用户确认
        """
        chars = self.analyze_data_characteristics(data_path)

        # 整数类型 + 唯一值比例低 → 分类数据 → 最近邻
        if chars['is_integer'] and chars['unique_ratio'] < threshold:
            return 'nearest', f"分类数据（{chars['unique_count']}个唯一值，整数类型）", False

        # 整数类型 + 唯一值数量少 → 可能是分类数据
        if chars['is_integer'] and chars['unique_count'] < 50:
            return 'nearest', f"可能的分类数据（{chars['unique_count']}个唯一值）", True

        # 浮点类型 → 连续数据 → 双线性
        if chars['is_float']:
            return 'bilinear', f"连续数据（浮点类型，{chars['unique_count']}个唯一值）", False

        # 默认最近邻
        return 'nearest', "默认方法", True

    def get_resampling_method(self, data_path, user_method='auto'):
        """
        获取重采样方法

        参数:
            data_path: 数据文件路径
            user_method: 用户指定的方法，'auto'表示自动判断

        返回:
            method: 重采样方法
            reason: 选择原因
        """
        if user_method != 'auto':
            if user_method in self.RESAMPLING_METHODS:
                return user_method, f"用户指定: {user_method}"
            else:
                print(f"警告: 不支持的重采样方法 '{user_method}'，使用自动判断")

        recommended, reason, needs_confirm = self.recommend_resampling(data_path)

        if needs_confirm:
            print(f"\n数据特性分析:")
            chars = self.analyze_data_characteristics(data_path)
            print(f"  数据类型: {chars['dtype']}")
            print(f"  唯一值数量: {chars['unique_count']}")
            print(f"  值域范围: {chars['min']:.4f} ~ {chars['max']:.4f}")
            print(f"\n推荐重采样方法: {recommended}")
            print(f"原因: {reason}")
            print(f"\n请选择:")
            print(f"  1. 最近邻法 (nearest) - 适用于分类数据")
            print(f"  2. 双线性插值 (bilinear) - 适用于连续数据")
            print(f"  3. 使用推荐方法 ({recommended})")

            choice = input("\n请输入选择 [1/2/3]: ").strip()

            if choice == '1':
                return 'nearest', "用户选择: 最近邻法"
            elif choice == '2':
                return 'bilinear', "用户选择: 双线性插值"
            else:
                return recommended, reason

        return recommended, reason

    def align(self, source_path, output_path, resampling_method='auto'):
        """
        对齐栅格到基准图层

        参数:
            source_path: 待对齐的栅格文件路径
            output_path: 输出文件路径
            resampling_method: 重采样方法，'auto'表示自动判断

        返回:
            dict: 对齐结果信息
        """
        # 获取重采样方法
        method, reason = self.get_resampling_method(source_path, resampling_method)
        resampling = self.RESAMPLING_METHODS[method]

        print(f"\n开始对齐:")
        print(f"  源文件: {source_path}")
        print(f"  输出文件: {output_path}")
        print(f"  重采样方法: {method} ({reason})")

        # 读取源文件
        with rasterio.open(source_path) as src:
            src_data = src.read(1)
            src_crs = src.crs
            src_transform = src.transform
            src_nodata = src.nodata
            src_dtype = src.dtypes[0]
            src_shape = (src.height, src.width)

            # 准备输出profile
            out_profile = self.ref_profile.copy()
            out_profile.update({
                'dtype': src_dtype,
                'count': 1,
                'nodata': src_nodata
            })

            # 创建输出文件
            with rasterio.open(output_path, 'w', **out_profile) as dst:
                # 执行重投影
                reproject(
                    source=rasterio.band(src, 1),
                    destination=rasterio.band(dst, 1),
                    src_transform=src_transform,
                    src_crs=src_crs,
                    dst_transform=self.ref_transform,
                    dst_crs=self.ref_crs,
                    resampling=resampling
                )

        # 验证对齐结果
        with rasterio.open(output_path) as result:
            result_shape = (result.height, result.width)
            result_bounds = result.bounds

        # 检查是否对齐成功
        shape_match = result_shape == self.ref_shape
        bounds_match = all(abs(a - b) < 1e-6 for a, b in zip(result_bounds, self.ref_bounds))

        result_info = {
            'source_path': source_path,
            'output_path': output_path,
            'resampling_method': method,
            'resampling_reason': reason,
            'source_shape': src_shape,
            'target_shape': self.ref_shape,
            'result_shape': result_shape,
            'shape_match': shape_match,
            'bounds_match': bounds_match,
            'success': shape_match and bounds_match,
            'timestamp': datetime.now().isoformat()
        }

        print(f"\n对齐结果:")
        print(f"  源尺寸: {src_shape[1]} x {src_shape[0]}")
        print(f"  目标尺寸: {self.ref_shape[1]} x {self.ref_shape[0]}")
        print(f"  结果尺寸: {result_shape[1]} x {result_shape[0]}")
        print(f"  尺寸匹配: {'✓' if shape_match else '✗'}")
        print(f"  范围匹配: {'✓' if bounds_match else '✗'}")

        if result_info['success']:
            print(f"  状态: ✓ 对齐成功")
        else:
            print(f"  状态: ⚠ 对齐可能存在问题")

        return result_info

    def align_batch(self, source_files, output_dir, resampling_method='auto', naming='suffix'):
        """
        批量对齐栅格文件

        参数:
            source_files: 源文件路径列表
            output_dir: 输出目录
            resampling_method: 重采样方法
            naming: 命名方式，'suffix'（添加后缀）或'replace'（替换原文件名）

        返回:
            list: 对齐结果列表
        """
        os.makedirs(output_dir, exist_ok=True)
        results = []

        print(f"批量对齐开始:")
        print(f"  文件数量: {len(source_files)}")
        print(f"  输出目录: {output_dir}")
        print(f"  重采样方法: {resampling_method}")
        print()

        for i, source_path in enumerate(source_files, 1):
            filename = os.path.basename(source_path)
            name, ext = os.path.splitext(filename)

            if naming == 'suffix':
                output_filename = f"{name}_aligned{ext}"
            else:
                output_filename = filename

            output_path = os.path.join(output_dir, output_filename)

            print(f"[{i}/{len(source_files)}] 处理: {filename}")
            result = self.align(source_path, output_path, resampling_method)
            results.append(result)
            print()

        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        print(f"批量对齐完成:")
        print(f"  成功: {success_count}/{len(results)}")
        print(f"  失败: {len(results) - success_count}/{len(results)}")

        return results


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='栅格对齐工具')
    parser.add_argument('reference', help='基准栅格文件路径')
    parser.add_argument('source', nargs='+', help='待对齐的栅格文件路径')
    parser.add_argument('-o', '--output', default='.', help='输出目录')
    parser.add_argument('-m', '--method', default='auto',
                       choices=['auto', 'nearest', 'bilinear', 'cubic'],
                       help='重采样方法')
    parser.add_argument('-y', '--yes', action='store_true',
                       help='自动确认，不询问用户')

    args = parser.parse_args()

    aligner = RasterAligner(args.reference)

    if len(args.source) == 1:
        output_path = os.path.join(args.output, os.path.basename(args.source[0]))
        aligner.align(args.source[0], output_path, args.method)
    else:
        aligner.align_batch(args.source, args.output, args.method)


if __name__ == '__main__':
    main()
