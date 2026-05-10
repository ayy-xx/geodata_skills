"""
数据抽检验证工具
批量生成数据后进行质量抽检
"""

import os
import shutil
import numpy as np
import rasterio
from datetime import datetime
import random
import json


class SamplingValidator:
    """数据抽检验证器"""

    def __init__(self, batch_dir, sampling_dir='_sampling_temp'):
        """
        初始化验证器

        参数:
            batch_dir: 批量生成数据的目录
            sampling_dir: 抽检临时目录
        """
        self.batch_dir = batch_dir
        self.sampling_dir = sampling_dir
        self.results = []
        self.sampling_files = []

        os.makedirs(sampling_dir, exist_ok=True)
        print(f"抽检验证器初始化:")
        print(f"  批量数据目录: {batch_dir}")
        print(f"  抽检临时目录: {sampling_dir}")

    def list_batch_files(self, pattern=None):
        """
        列出批量目录中的文件

        参数:
            pattern: 文件名模式过滤（如 '*.tif'）

        返回:
            list: 文件列表
        """
        files = []
        for f in os.listdir(self.batch_dir):
            if pattern:
                import fnmatch
                if fnmatch.fnmatch(f, pattern):
                    files.append(os.path.join(self.batch_dir, f))
            else:
                files.append(os.path.join(self.batch_dir, f))

        return sorted(files)

    def select_samples(self, n_samples=1, method='random', user_choice=None, exclude_pattern=None):
        """
        选择抽检样本

        参数:
            n_samples: 抽检数量
            method: 'user'(用户指定) 或 'random'(随机)
            user_choice: 用户指定的文件名关键词
            exclude_pattern: 排除的文件名模式

        返回:
            list: 选中的文件路径列表
        """
        # 获取所有文件
        all_files = self.list_batch_files('*.tif')
        if not all_files:
            all_files = self.list_batch_files()

        # 排除指定模式
        if exclude_pattern:
            import fnmatch
            all_files = [f for f in all_files if not fnmatch.fnmatch(os.path.basename(f), exclude_pattern)]

        if not all_files:
            print("错误: 没有找到可抽检的文件")
            return []

        print(f"\n可抽检文件列表:")
        for i, f in enumerate(all_files, 1):
            print(f"  {i}. {os.path.basename(f)}")

        if method == 'user' and user_choice:
            # 用户指定模式
            samples = [f for f in all_files if user_choice in os.path.basename(f)]
            if not samples:
                print(f"警告: 未找到包含 '{user_choice}' 的文件")
                return []
        elif method == 'random':
            # 随机选择
            samples = random.sample(all_files, min(n_samples, len(all_files)))
        else:
            # 交互式选择
            print(f"\n请选择抽检方式:")
            print(f"  1. 指定抽检文件（输入文件名关键词）")
            print(f"  2. 随机抽检（输入抽检数量）")

            choice = input("\n请输入选择 [1/2]: ").strip()

            if choice == '1':
                keyword = input("请输入文件名关键词: ").strip()
                samples = [f for f in all_files if keyword in os.path.basename(f)]
                if not samples:
                    print(f"未找到包含 '{keyword}' 的文件")
                    return []
            else:
                n = input(f"请输入抽检数量 [默认1]: ").strip()
                n = int(n) if n else 1
                samples = random.sample(all_files, min(n, len(all_files)))

        print(f"\n已选择 {len(samples)} 个抽检样本:")
        for s in samples:
            print(f"  - {os.path.basename(s)}")

        self.sampling_files = samples
        return samples

    def regenerate_sample(self, sample_file, regenerate_func, **kwargs):
        """
        重新生成抽检样本

        参数:
            sample_file: 样本文件路径
            regenerate_func: 重新生成函数
                           函数签名: func(filename, output_dir, **kwargs) -> output_path
            **kwargs: 传递给重新生成函数的额外参数

        返回:
            str: 重新生成的文件路径
        """
        filename = os.path.basename(sample_file)
        print(f"\n重新生成样本: {filename}")

        # 调用重新生成函数
        output_path = regenerate_func(filename, self.sampling_dir, **kwargs)

        if output_path and os.path.exists(output_path):
            print(f"  ✓ 重新生成成功: {output_path}")
            return output_path
        else:
            print(f"  ✗ 重新生成失败")
            return None

    def compare_rasters(self, batch_file, sampling_file, tolerance=1e-6):
        """
        对比两个栅格文件

        参数:
            batch_file: 批量生成的文件
            sampling_file: 抽检重新生成的文件
            tolerance: 容差

        返回:
            dict: 对比结果
        """
        try:
            with rasterio.open(batch_file) as src1:
                data1 = src1.read(1)
                nodata1 = src1.nodata
                profile1 = src1.profile

            with rasterio.open(sampling_file) as src2:
                data2 = src2.read(1)
                nodata2 = src2.nodata
                profile2 = src2.profile

            # 检查尺寸是否一致
            if data1.shape != data2.shape:
                return {
                    'batch_file': os.path.basename(batch_file),
                    'sampling_file': os.path.basename(sampling_file),
                    'status': 'error',
                    'error': f'尺寸不一致: {data1.shape} vs {data2.shape}',
                    'timestamp': datetime.now().isoformat()
                }

            # 创建有效数据掩码
            mask = np.ones_like(data1, dtype=bool)
            if nodata1 is not None:
                mask &= (data1 != nodata1)
            if nodata2 is not None:
                mask &= (data2 != nodata2)

            # 排除NaN
            mask &= ~np.isnan(data1.astype(float))
            mask &= ~np.isnan(data2.astype(float))

            if mask.sum() == 0:
                return {
                    'batch_file': os.path.basename(batch_file),
                    'sampling_file': os.path.basename(sampling_file),
                    'status': 'error',
                    'error': '没有有效数据可比较',
                    'timestamp': datetime.now().isoformat()
                }

            # 计算差异
            diff = data1[mask].astype(float) - data2[mask].astype(float)
            abs_diff = np.abs(diff)

            result = {
                'batch_file': os.path.basename(batch_file),
                'sampling_file': os.path.basename(sampling_file),
                'status': 'pass' if np.all(abs_diff < tolerance) else 'fail',
                'valid_pixels': int(mask.sum()),
                'total_pixels': int(data1.size),
                'max_diff': float(np.max(abs_diff)),
                'mean_diff': float(np.mean(abs_diff)),
                'std_diff': float(np.std(diff)),
                'rmse': float(np.sqrt(np.mean(diff**2))),
                'identical_pixels': int(np.sum(abs_diff == 0)),
                'diff_within_tolerance': int(np.sum(abs_diff < tolerance)),
                'tolerance': tolerance,
                'timestamp': datetime.now().isoformat()
            }

            # 计算差异分布
            result['diff_percentiles'] = {
                'p50': float(np.percentile(abs_diff, 50)),
                'p90': float(np.percentile(abs_diff, 90)),
                'p95': float(np.percentile(abs_diff, 95)),
                'p99': float(np.percentile(abs_diff, 99))
            }

            return result

        except Exception as e:
            return {
                'batch_file': os.path.basename(batch_file),
                'sampling_file': os.path.basename(sampling_file),
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def validate(self, regenerate_func, tolerance=1e-6, **kwargs):
        """
        执行完整抽检验证流程

        参数:
            regenerate_func: 重新生成函数
            tolerance: 容差
            **kwargs: 传递给重新生成函数的额外参数

        返回:
            list: 验证结果列表
        """
        if not self.sampling_files:
            print("错误: 未选择抽检样本，请先调用 select_samples()")
            return []

        self.results = []
        print(f"\n{'='*60}")
        print(f"开始抽检验证")
        print(f"{'='*60}")

        for i, sample_file in enumerate(self.sampling_files, 1):
            filename = os.path.basename(sample_file)
            print(f"\n[{i}/{len(self.sampling_files)}] 处理: {filename}")

            # 1. 重新生成
            sampling_path = self.regenerate_sample(sample_file, regenerate_func, **kwargs)

            if not sampling_path:
                self.results.append({
                    'batch_file': filename,
                    'status': 'regenerate_failed',
                    'timestamp': datetime.now().isoformat()
                })
                continue

            # 2. 对比验证
            batch_path = os.path.join(self.batch_dir, filename)
            result = self.compare_rasters(batch_path, sampling_path, tolerance)

            # 3. 输出结果
            if result['status'] == 'pass':
                print(f"  ✓ 验证通过")
                print(f"    - 有效像元: {result['valid_pixels']}")
                print(f"    - 最大差异: {result['max_diff']:.8f}")
                print(f"    - RMSE: {result['rmse']:.8f}")
            elif result['status'] == 'fail':
                print(f"  ⚠ 存在差异")
                print(f"    - 有效像元: {result['valid_pixels']}")
                print(f"    - 最大差异: {result['max_diff']:.8f}")
                print(f"    - RMSE: {result['rmse']:.8f}")
                print(f"    - 超出容差像元: {result['valid_pixels'] - result['diff_within_tolerance']}")
            else:
                print(f"  ✗ 验证错误: {result.get('error', '未知错误')}")

            self.results.append(result)

        # 4. 输出汇总
        self._print_summary()

        return self.results

    def _print_summary(self):
        """打印验证汇总"""
        if not self.results:
            return

        print(f"\n{'='*60}")
        print(f"抽检验证汇总")
        print(f"{'='*60}")

        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'pass')
        failed = sum(1 for r in self.results if r['status'] == 'fail')
        errors = sum(1 for r in self.results if r['status'] == 'error' or r['status'] == 'regenerate_failed')

        print(f"总样本数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"错误: {errors}")

        if failed > 0:
            print(f"\n失败样本详情:")
            for r in self.results:
                if r['status'] == 'fail':
                    print(f"  - {r['batch_file']}")
                    print(f"    最大差异: {r['max_diff']:.8f}, RMSE: {r['rmse']:.8f}")

    def confirm_and_cleanup(self, auto_confirm=False):
        """
        用户确认后清理抽检数据

        参数:
            auto_confirm: 是否自动确认（不询问用户）

        返回:
            bool: 是否确认通过
        """
        if not self.results:
            print("没有验证结果")
            return False

        passed = all(r['status'] == 'pass' for r in self.results)

        if not passed:
            print("\n验证未全部通过，保留抽检数据供排查")
            return False

        if auto_confirm:
            confirm = 'y'
        else:
            print(f"\n所有样本验证通过")
            confirm = input("是否确认并删除抽检临时数据？[y/n]: ").strip().lower()

        if confirm == 'y':
            self.cleanup()
            print("✓ 已确认并清理抽检数据")
            return True
        else:
            print("保留抽检数据")
            return False

    def cleanup(self):
        """清理抽检临时目录"""
        if os.path.exists(self.sampling_dir):
            shutil.rmtree(self.sampling_dir)
            print(f"已清理临时目录: {self.sampling_dir}")

    def generate_report(self, output_path='sampling_report.md'):
        """
        生成抽检报告

        参数:
            output_path: 报告输出路径

        返回:
            str: 报告文件路径
        """
        if not self.results:
            print("没有验证结果可生成报告")
            return None

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 数据抽检验证报告\n\n")
            f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 验证配置\n\n")
            f.write(f"- 批量数据目录: `{self.batch_dir}`\n")
            f.write(f"- 抽检临时目录: `{self.sampling_dir}`\n")
            f.write(f"- 抽检样本数: {len(self.results)}\n\n")

            f.write("## 验证结果汇总\n\n")
            f.write("| 文件 | 状态 | RMSE | 最大差异 | 有效像元 |\n")
            f.write("|------|------|------|----------|----------|\n")

            for r in self.results:
                if r['status'] == 'pass':
                    status = "✓ 通过"
                elif r['status'] == 'fail':
                    status = "⚠ 有差异"
                else:
                    status = "✗ 错误"

                rmse = f"{r.get('rmse', 0):.8f}" if 'rmse' in r else 'N/A'
                max_diff = f"{r.get('max_diff', 0):.8f}" if 'max_diff' in r else 'N/A'
                valid = str(r.get('valid_pixels', 'N/A'))

                f.write(f"| {r.get('batch_file', 'N/A')} | {status} | {rmse} | {max_diff} | {valid} |\n")

            f.write("\n## 详细信息\n\n")

            for i, r in enumerate(self.results, 1):
                f.write(f"### 样本 {i}: {r.get('batch_file', 'N/A')}\n\n")
                f.write(f"- **状态:** {r['status']}\n")
                f.write(f"- **抽检文件:** {r.get('sampling_file', 'N/A')}\n")
                f.write(f"- **时间戳:** {r.get('timestamp', 'N/A')}\n")

                if 'error' in r:
                    f.write(f"- **错误:** {r['error']}\n")
                else:
                    f.write(f"- **有效像元:** {r.get('valid_pixels', 'N/A')}\n")
                    f.write(f"- **总像元数:** {r.get('total_pixels', 'N/A')}\n")
                    f.write(f"- **完全一致像元:** {r.get('identical_pixels', 'N/A')}\n")
                    f.write(f"- **容差内像元:** {r.get('diff_within_tolerance', 'N/A')}\n")
                    f.write(f"- **容差:** {r.get('tolerance', 'N/A')}\n")
                    f.write(f"- **最大差异:** {r.get('max_diff', 'N/A'):.8f}\n")
                    f.write(f"- **平均差异:** {r.get('mean_diff', 'N/A'):.8f}\n")
                    f.write(f"- **标准差:** {r.get('std_diff', 'N/A'):.8f}\n")
                    f.write(f"- **RMSE:** {r.get('rmse', 'N/A'):.8f}\n")

                    if 'diff_percentiles' in r:
                        p = r['diff_percentiles']
                        f.write(f"- **差异分布:** P50={p['p50']:.8f}, P90={p['p90']:.8f}, P95={p['p95']:.8f}, P99={p['p99']:.8f}\n")

                f.write("\n")

            f.write("## 结论\n\n")
            passed = all(r['status'] == 'pass' for r in self.results)
            if passed:
                f.write("✓ **所有抽检样本验证通过，数据质量合格。**\n")
            else:
                f.write("⚠ **部分抽检样本存在差异，请检查数据处理流程。**\n")

        print(f"\n报告已生成: {output_path}")
        return output_path


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='数据抽检验证工具')
    parser.add_argument('batch_dir', help='批量数据目录')
    parser.add_argument('-n', '--n-samples', type=int, default=1, help='抽检样本数量')
    parser.add_argument('-o', '--output', default='sampling_report.md', help='报告输出路径')
    parser.add_argument('-t', '--tolerance', type=float, default=1e-6, help='对比容差')

    args = parser.parse_args()

    validator = SamplingValidator(args.batch_dir)

    # 选择样本
    samples = validator.select_samples(n_samples=args.n_samples)
    if not samples:
        return

    # 这里需要用户提供重新生成函数
    print("\n请提供重新生成函数，或使用 validate() 方法时传入")

    # 生成报告（示例，实际需要验证结果）
    # validator.generate_report(args.output)


if __name__ == '__main__':
    main()
