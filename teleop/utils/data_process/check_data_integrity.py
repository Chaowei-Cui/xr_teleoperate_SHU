#!/usr/bin/env python3
"""
数据完整性检查脚本 - 简洁版
"""

import json
import sys
from pathlib import Path
from collections import Counter


class DataChecker:
    """数据完整性检查器"""
    
    def __init__(self, data_path: str, verbose=False):
        self.data_path = Path(data_path)
        self.data_dir = self.data_path.parent
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.stats = {}
        
    def check(self):
        """执行检查"""
        # 加载数据
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            self.errors.append(f"无法读取文件: {e}")
            return False
        
        # 基本结构检查
        if 'data' not in data:
            self.errors.append("缺少data字段")
            return False
        
        frames = data['data']
        self.stats['total_frames'] = len(frames)
        self.stats['file_size_mb'] = self.data_path.stat().st_size / (1024 * 1024)
        
        # 检查帧结构
        for i, frame in enumerate(frames):
            # 检查必需字段
            if 'idx' not in frame or frame['idx'] != i:
                self.errors.append(f"帧{i}: idx不匹配")
            
            if 'colors' not in frame:
                self.errors.append(f"帧{i}: 缺少colors")
            elif frame['colors']:
                # 检查图像文件存在性
                for cam, img_path in frame['colors'].items():
                    if not (self.data_dir / img_path).exists():
                        self.errors.append(f"帧{i}: 图像文件不存在 {img_path}")
                        break
            
            # 检查states和actions
            for section in ['states', 'actions']:
                if section not in frame:
                    self.errors.append(f"帧{i}: 缺少{section}")
                    continue
                for part in ['left_arm', 'right_arm', 'left_ee', 'right_ee', 'body']:
                    if part in frame[section] and 'qpos' not in frame[section][part]:
                        self.errors.append(f"帧{i}: {section}.{part}缺少qpos")
        
        # 统计相机
        if frames and 'colors' in frames[0]:
            self.stats['cameras'] = list(frames[0]['colors'].keys())
        
        # 检查sub_index
        self._check_sub_index(frames)
        
        return len(self.errors) == 0
    
    def _check_sub_index(self, frames):
        """检查sub_index"""
        sub_indices = [f.get('sub_index') for f in frames]
        
        # 检查缺失
        if None in sub_indices:
            missing_count = sub_indices.count(None)
            self.errors.append(f"{missing_count}帧缺少sub_index")
            return
        
        # 统计分布
        counter = Counter(sub_indices)
        self.stats['sub_tasks'] = len(counter)
        self.stats['sub_index_dist'] = dict(counter)
        
        # 查找切换点
        transitions = []
        for i in range(1, len(sub_indices)):
            if sub_indices[i] != sub_indices[i-1]:
                transitions.append((i, sub_indices[i-1], sub_indices[i]))
        self.stats['transitions'] = transitions
        
        # 检查单调性
        for i in range(1, len(sub_indices)):
            if sub_indices[i] < sub_indices[i-1]:
                self.warnings.append(f"sub_index回退: 帧{i-1}→{i}")
    
    def get_summary(self):
        """获取摘要"""
        return {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.stats
        }


def check_directory(directory: str, verbose=False):
    """检查目录下所有数据"""
    dir_path = Path(directory)
    data_files = sorted(dir_path.glob("*/data.json"))
    
    if not data_files:
        print(f"❌ 未找到数据文件: {directory}")
        return False
    
    print(f"检查 {len(data_files)} 个数据集...")
    print("=" * 80)
    
    results = []
    for data_file in data_files:
        episode = data_file.parent.name
        checker = DataChecker(str(data_file), verbose)
        success = checker.check()
        summary = checker.get_summary()
        
        results.append({
            'episode': episode,
            'success': success,
            'summary': summary
        })
        
        # 打印单个结果
        status = "✅" if success else "❌"
        stats = summary['stats']
        info = f"{stats.get('total_frames', 0)}帧"
        if 'sub_tasks' in stats:
            info += f", {stats['sub_tasks']}个子任务"
        if 'cameras' in stats:
            info += f", {len(stats['cameras'])}相机"
        
        print(f"{status} {episode:20s} {info}")
        
        if not success and verbose:
            for err in summary['errors'][:3]:
                print(f"     ↳ {err}")
    
    # 总结
    print("=" * 80)
    success_count = sum(1 for r in results if r['success'])
    total_frames = sum(r['summary']['stats'].get('total_frames', 0) for r in results)
    
    print(f"\n📊 总体统计:")
    print(f"  数据集: {success_count}/{len(results)} 通过")
    print(f"  总帧数: {total_frames}")
    
    # 显示失败的
    failed = [r for r in results if not r['success']]
    if failed:
        print(f"\n❌ 失败的数据集:")
        for r in failed:
            print(f"  {r['episode']}: {len(r['summary']['errors'])}个错误")
            if verbose:
                for err in r['summary']['errors'][:5]:
                    print(f"    - {err}")
    
    # 显示警告
    all_warnings = []
    for r in results:
        all_warnings.extend(r['summary']['warnings'])
    if all_warnings and verbose:
        print(f"\n⚠️  警告 ({len(all_warnings)}):")
        for w in all_warnings[:10]:
            print(f"  {w}")
    
    print("\n" + ("✅ 全部通过！" if success_count == len(results) else f"❌ {len(failed)}个数据集有问题"))
    
    return success_count == len(results)


def check_single_file(file_path: str, verbose=True):
    """检查单个文件"""
    checker = DataChecker(file_path, verbose)
    success = checker.check()
    summary = checker.get_summary()
    
    print("=" * 80)
    print(f"检查: {Path(file_path).parent.name}")
    print("=" * 80)
    
    stats = summary['stats']
    print(f"\n📊 数据概览:")
    print(f"  总帧数: {stats.get('total_frames', 0)}")
    print(f"  文件大小: {stats.get('file_size_mb', 0):.2f} MB")
    if 'cameras' in stats:
        print(f"  相机: {', '.join(stats['cameras'])}")
    
    if 'sub_tasks' in stats:
        print(f"\n🔖 子任务:")
        print(f"  数量: {stats['sub_tasks']}")
        for sub_idx, count in sorted(stats['sub_index_dist'].items()):
            pct = count / stats['total_frames'] * 100
            print(f"    sub_index {sub_idx}: {count}帧 ({pct:.1f}%)")
        if stats.get('transitions'):
            print(f"  切换点: {len(stats['transitions'])}")
            for idx, from_sub, to_sub in stats['transitions']:
                print(f"    帧{idx}: {from_sub}→{to_sub}")
    
    if summary['warnings']:
        print(f"\n⚠️  警告 ({len(summary['warnings'])}):")
        for w in summary['warnings']:
            print(f"  {w}")
    
    if summary['errors']:
        print(f"\n❌ 错误 ({len(summary['errors'])}):")
        for e in summary['errors'][:20]:
            print(f"  {e}")
        if len(summary['errors']) > 20:
            print(f"  ... 还有{len(summary['errors'])-20}个错误")
    
    print("\n" + "=" * 80)
    print("✅ 检查通过！" if success else f"❌ 发现{len(summary['errors'])}个错误")
    print("=" * 80)
    
    return success


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  检查单个文件: python check_data_integrity.py <data.json>")
        print("  检查整个目录: python check_data_integrity.py <目录>")
        print("\n选项:")
        print("  -v, --verbose  显示详细信息")
        sys.exit(1)
    
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    target = sys.argv[1] if sys.argv[1] not in ['-v', '--verbose'] else sys.argv[2]
    path = Path(target)
    
    if path.is_file():
        success = check_single_file(target, verbose)
    elif path.is_dir():
        success = check_directory(target, verbose)
    else:
        print(f"❌ 路径不存在: {target}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
