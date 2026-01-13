#!/usr/bin/env python3
"""
数据完整性检查脚本
用于检查机器人遥操作数据集的完整性
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any


class DataIntegrityChecker:
    """数据完整性检查器"""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.data_dir = self.data_path.parent
        self.errors = []
        self.warnings = []
        self.stats = {}
        
    def check_all(self) -> Tuple[bool, Dict[str, Any]]:
        """执行所有检查"""
        print(f"开始检查数据: {self.data_path}")
        print("=" * 80)
        
        # 1. 检查文件存在性
        if not self._check_file_exists():
            return False, self._get_report()
        
        # 2. 加载JSON数据
        data = self._load_json()
        if data is None:
            return False, self._get_report()
        
        # 3. 检查数据结构
        self._check_data_structure(data)
        
        # 4. 检查info字段
        self._check_info_section(data.get('info', {}))
        
        # 5. 检查text字段
        self._check_text_section(data.get('text', {}))
        
        # 6. 检查data数组
        data_array = data.get('data', [])
        self._check_data_array(data_array)
        
        # 7. 检查图像文件
        self._check_image_files(data_array)
        
        # 8. 检查深度文件
        self._check_depth_files(data_array)
        
        # 9. 检查音频文件
        self._check_audio_files(data_array)
        
        # 10. 检查数据连续性
        self._check_data_continuity(data_array)
        
        # 11. 检查数值范围
        self._check_value_ranges(data_array)
        
        # 12. 检查sub_index
        self._check_sub_index(data_array)
        
        # 生成报告
        return len(self.errors) == 0, self._get_report()
    
    def _check_file_exists(self) -> bool:
        """检查文件是否存在"""
        if not self.data_path.exists():
            self.errors.append(f"数据文件不存在: {self.data_path}")
            return False
        
        if not self.data_path.is_file():
            self.errors.append(f"路径不是文件: {self.data_path}")
            return False
        
        file_size = self.data_path.stat().st_size
        self.stats['file_size_mb'] = file_size / (1024 * 1024)
        print(f"✓ 文件存在，大小: {self.stats['file_size_mb']:.2f} MB")
        return True
    
    def _load_json(self) -> Dict:
        """加载JSON数据"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✓ JSON格式正确")
            return data
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            self.errors.append(f"读取文件错误: {e}")
            return None
    
    def _check_data_structure(self, data: Dict):
        """检查顶层数据结构"""
        required_keys = ['info', 'text', 'data']
        for key in required_keys:
            if key not in data:
                self.errors.append(f"缺少必需字段: {key}")
            else:
                print(f"✓ 字段存在: {key}")
    
    def _check_info_section(self, info: Dict):
        """检查info部分"""
        print("\n检查 info 部分:")
        required_fields = ['version', 'date', 'author', 'image', 'depth', 'joint_names']
        
        for field in required_fields:
            if field not in info:
                self.errors.append(f"info缺少字段: {field}")
            else:
                print(f"  ✓ {field}")
        
        # 检查图像配置
        if 'image' in info:
            img_config = info['image']
            if img_config.get('width') and img_config.get('height'):
                self.stats['image_resolution'] = f"{img_config['width']}x{img_config['height']}"
                self.stats['image_fps'] = img_config.get('fps', 'N/A')
                print(f"  ✓ 图像配置: {self.stats['image_resolution']} @ {self.stats['image_fps']} fps")
        
        # 检查关节名称
        if 'joint_names' in info:
            joint_names = info['joint_names']
            for part in ['left_arm', 'right_arm', 'left_ee', 'right_ee']:
                if part in joint_names:
                    count = len(joint_names[part])
                    self.stats[f'{part}_joints'] = count
                    print(f"  ✓ {part}: {count} 个关节")
    
    def _check_text_section(self, text: Dict):
        """检查text部分"""
        print("\n检查 text 部分:")
        fields = ['goal', 'desc', 'steps']
        for field in fields:
            if field in text:
                value = text[field]
                if value:
                    print(f"  ✓ {field}: {value[:50]}..." if len(str(value)) > 50 else f"  ✓ {field}: {value}")
                else:
                    self.warnings.append(f"text.{field} 为空")
                    print(f"  ⚠ {field}: 空")
    
    def _check_data_array(self, data_array: List[Dict]):
        """检查data数组"""
        print(f"\n检查 data 数组:")
        
        if not data_array:
            self.errors.append("data数组为空")
            return
        
        self.stats['total_frames'] = len(data_array)
        print(f"  ✓ 总帧数: {self.stats['total_frames']}")
        
        # 检查每一帧的结构
        required_frame_keys = ['idx', 'colors', 'depths', 'states', 'actions']
        
        for i, frame in enumerate(data_array):
            for key in required_frame_keys:
                if key not in frame:
                    self.errors.append(f"帧 {i} 缺少字段: {key}")
            
            # 检查idx连续性
            if frame.get('idx') != i:
                self.errors.append(f"帧 {i} 的idx不匹配: 期望 {i}, 实际 {frame.get('idx')}")
            
            # 检查states和actions结构
            for section in ['states', 'actions']:
                if section in frame:
                    section_data = frame[section]
                    for part in ['left_arm', 'right_arm', 'left_ee', 'right_ee', 'body']:
                        if part in section_data:
                            part_data = section_data[part]
                            if 'qpos' not in part_data:
                                self.errors.append(f"帧 {i} {section}.{part} 缺少qpos")
        
        print(f"  ✓ 数据帧结构检查完成")
    
    def _check_image_files(self, data_array: List[Dict]):
        """检查图像文件"""
        print(f"\n检查图像文件:")
        
        missing_images = []
        camera_counts = {}
        
        for i, frame in enumerate(data_array):
            colors = frame.get('colors', {})
            for camera_id, img_path in colors.items():
                # 统计相机数量
                camera_counts[camera_id] = camera_counts.get(camera_id, 0) + 1
                
                # 检查文件存在性
                full_path = self.data_dir / img_path
                if not full_path.exists():
                    missing_images.append(f"帧 {i}: {img_path}")
        
        self.stats['cameras'] = list(camera_counts.keys())
        self.stats['camera_counts'] = camera_counts
        
        print(f"  ✓ 相机数量: {len(camera_counts)}")
        for camera_id, count in camera_counts.items():
            print(f"    - {camera_id}: {count} 张图像")
        
        if missing_images:
            self.errors.append(f"缺少 {len(missing_images)} 个图像文件")
            if len(missing_images) <= 10:
                for img in missing_images:
                    self.errors.append(f"  缺失: {img}")
            else:
                for img in missing_images[:5]:
                    self.errors.append(f"  缺失: {img}")
                self.errors.append(f"  ... 还有 {len(missing_images) - 5} 个文件缺失")
        else:
            print(f"  ✓ 所有图像文件存在")
    
    def _check_depth_files(self, data_array: List[Dict]):
        """检查深度文件"""
        print(f"\n检查深度文件:")
        
        has_depth = False
        missing_depths = []
        
        for i, frame in enumerate(data_array):
            depths = frame.get('depths', {})
            if depths:
                has_depth = True
                for depth_id, depth_path in depths.items():
                    full_path = self.data_dir / depth_path
                    if not full_path.exists():
                        missing_depths.append(f"帧 {i}: {depth_path}")
        
        if not has_depth:
            self.warnings.append("没有深度数据")
            print(f"  ⚠ 没有深度数据")
        elif missing_depths:
            self.errors.append(f"缺少 {len(missing_depths)} 个深度文件")
        else:
            print(f"  ✓ 深度文件检查通过")
    
    def _check_audio_files(self, data_array: List[Dict]):
        """检查音频文件"""
        print(f"\n检查音频文件:")
        
        has_audio = False
        missing_audios = []
        
        for i, frame in enumerate(data_array):
            audios = frame.get('audios')
            if audios:
                has_audio = True
                if isinstance(audios, str):
                    full_path = self.data_dir / audios
                    if not full_path.exists():
                        missing_audios.append(f"帧 {i}: {audios}")
        
        if not has_audio:
            self.warnings.append("没有音频数据")
            print(f"  ⚠ 没有音频数据")
        elif missing_audios:
            self.errors.append(f"缺少 {len(missing_audios)} 个音频文件")
        else:
            print(f"  ✓ 音频文件检查通过")
    
    def _check_data_continuity(self, data_array: List[Dict]):
        """检查数据连续性"""
        print(f"\n检查数据连续性:")
        
        if len(data_array) < 2:
            self.warnings.append("数据帧数太少，无法检查连续性")
            return
        
        # 检查idx连续性
        idx_gaps = []
        for i in range(1, len(data_array)):
            expected_idx = data_array[i-1]['idx'] + 1
            actual_idx = data_array[i]['idx']
            if actual_idx != expected_idx:
                idx_gaps.append(f"帧 {i-1} -> {i}: idx从 {data_array[i-1]['idx']} 跳到 {actual_idx}")
        
        if idx_gaps:
            self.warnings.append(f"发现 {len(idx_gaps)} 处idx不连续")
            for gap in idx_gaps[:5]:
                self.warnings.append(f"  {gap}")
        else:
            print(f"  ✓ idx连续")
        
        # 检查关节位置突变
        self._check_joint_continuity(data_array)
    
    def _check_joint_continuity(self, data_array: List[Dict]):
        """检查关节位置连续性"""
        max_jump_threshold = 0.5  # 最大允许跳变（弧度）
        
        large_jumps = []
        
        for i in range(1, min(len(data_array), 100)):  # 只检查前100帧
            prev_frame = data_array[i-1]
            curr_frame = data_array[i]
            
            for part in ['left_arm', 'right_arm']:
                if part in prev_frame.get('states', {}) and part in curr_frame.get('states', {}):
                    prev_qpos = prev_frame['states'][part].get('qpos', [])
                    curr_qpos = curr_frame['states'][part].get('qpos', [])
                    
                    if len(prev_qpos) == len(curr_qpos):
                        for j, (prev_q, curr_q) in enumerate(zip(prev_qpos, curr_qpos)):
                            diff = abs(curr_q - prev_q)
                            if diff > max_jump_threshold:
                                large_jumps.append(f"帧 {i} {part}[{j}]: 跳变 {diff:.3f}")
        
        if large_jumps:
            self.warnings.append(f"发现 {len(large_jumps)} 处关节位置大幅跳变")
            for jump in large_jumps[:5]:
                self.warnings.append(f"  {jump}")
        else:
            print(f"  ✓ 关节位置连续（前100帧）")
    
    def _check_value_ranges(self, data_array: List[Dict]):
        """检查数值范围"""
        print(f"\n检查数值范围:")
        
        # 检查关节位置范围（一般在-π到π之间）
        joint_range_errors = []
        
        for i, frame in enumerate(data_array[:100]):  # 只检查前100帧
            for part in ['left_arm', 'right_arm']:
                if part in frame.get('states', {}):
                    qpos = frame['states'][part].get('qpos', [])
                    for j, q in enumerate(qpos):
                        if abs(q) > 10:  # 超出合理范围
                            joint_range_errors.append(f"帧 {i} {part}[{j}]: {q:.3f}")
        
        if joint_range_errors:
            self.warnings.append(f"发现 {len(joint_range_errors)} 处关节位置超出正常范围")
            for err in joint_range_errors[:5]:
                self.warnings.append(f"  {err}")
        else:
            print(f"  ✓ 关节位置在正常范围内（前100帧）")
    
    def _check_sub_index(self, data_array: List[Dict]):
        """检查sub_index字段"""
        print(f"\n检查 sub_index:")
        
        if not data_array:
            return
        
        # 统计sub_index
        from collections import Counter
        sub_indices = []
        missing_sub_index = []
        
        for i, frame in enumerate(data_array):
            if 'sub_index' not in frame:
                missing_sub_index.append(i)
                sub_indices.append(None)
            else:
                sub_indices.append(frame['sub_index'])
        
        # 检查缺失
        if missing_sub_index:
            self.errors.append(f"有 {len(missing_sub_index)} 帧缺少sub_index字段")
            if len(missing_sub_index) <= 10:
                for idx in missing_sub_index:
                    self.errors.append(f"  帧 {idx} 缺少sub_index")
            else:
                for idx in missing_sub_index[:5]:
                    self.errors.append(f"  帧 {idx} 缺少sub_index")
                self.errors.append(f"  ... 还有 {len(missing_sub_index) - 5} 帧缺失")
            return
        
        # 统计分布
        sub_index_counts = Counter(sub_indices)
        self.stats['sub_index_distribution'] = dict(sub_index_counts)
        self.stats['sub_index_count'] = len(sub_index_counts)
        
        print(f"  ✓ 所有帧都有sub_index字段")
        print(f"  ✓ 子任务数量: {len(sub_index_counts)}")
        
        # 显示每个sub_index的帧数
        for sub_idx in sorted(sub_index_counts.keys()):
            count = sub_index_counts[sub_idx]
            percentage = count / len(data_array) * 100
            print(f"    - sub_index {sub_idx}: {count} 帧 ({percentage:.1f}%)")
        
        # 查找sub_index变化点
        transitions = []
        for i in range(1, len(data_array)):
            if sub_indices[i] != sub_indices[i-1]:
                transitions.append({
                    'from_idx': i-1,
                    'to_idx': i,
                    'from_sub': sub_indices[i-1],
                    'to_sub': sub_indices[i]
                })
        
        self.stats['sub_index_transitions'] = len(transitions)
        
        if transitions:
            print(f"  ✓ 发现 {len(transitions)} 个子任务切换点:")
            for trans in transitions:
                print(f"    - 帧 {trans['from_idx']} -> {trans['to_idx']}: "
                      f"sub_index {trans['from_sub']} -> {trans['to_sub']}")
        else:
            print(f"  ✓ 没有子任务切换（单一任务）")
        
        # 检查sub_index是否连续
        unique_sub_indices = sorted(set(sub_indices))
        expected_sequence = list(range(len(unique_sub_indices)))
        
        if unique_sub_indices != expected_sequence:
            self.warnings.append(f"sub_index不连续: {unique_sub_indices}, 期望: {expected_sequence}")
            print(f"  ⚠ sub_index不连续")
        else:
            print(f"  ✓ sub_index连续 (0 到 {len(unique_sub_indices)-1})")
        
        # 检查sub_index是否单调递增
        non_monotonic = []
        for i in range(1, len(sub_indices)):
            if sub_indices[i] < sub_indices[i-1]:
                non_monotonic.append(f"帧 {i-1} -> {i}: {sub_indices[i-1]} -> {sub_indices[i]}")
        
        if non_monotonic:
            self.warnings.append(f"sub_index不是单调递增的，发现 {len(non_monotonic)} 处回退")
            for item in non_monotonic[:5]:
                self.warnings.append(f"  {item}")
            print(f"  ⚠ sub_index有回退")
        else:
            print(f"  ✓ sub_index单调递增")
        
        # 检查每个sub_index段的长度
        print(f"\n  子任务段统计:")
        current_sub = sub_indices[0]
        segment_start = 0
        segments = []
        
        for i in range(1, len(sub_indices)):
            if sub_indices[i] != current_sub:
                segment_length = i - segment_start
                segments.append({
                    'sub_index': current_sub,
                    'start': segment_start,
                    'end': i - 1,
                    'length': segment_length
                })
                print(f"    - sub_index {current_sub}: 帧 {segment_start}-{i-1} ({segment_length} 帧)")
                current_sub = sub_indices[i]
                segment_start = i
        
        # 最后一段
        segment_length = len(sub_indices) - segment_start
        segments.append({
            'sub_index': current_sub,
            'start': segment_start,
            'end': len(sub_indices) - 1,
            'length': segment_length
        })
        print(f"    - sub_index {current_sub}: 帧 {segment_start}-{len(sub_indices)-1} ({segment_length} 帧)")
        
        self.stats['sub_index_segments'] = segments
        
        # 检查段长度是否合理（太短可能有问题）
        min_segment_length = 10  # 最小合理段长度
        short_segments = [s for s in segments if s['length'] < min_segment_length]
        
        if short_segments:
            self.warnings.append(f"发现 {len(short_segments)} 个过短的子任务段（< {min_segment_length} 帧）")
            for seg in short_segments:
                self.warnings.append(f"  sub_index {seg['sub_index']}: {seg['length']} 帧")
            print(f"  ⚠ 有过短的子任务段")
    
    def _get_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        return {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.stats
        }
    
    def print_report(self, report: Dict[str, Any]):
        """打印检查报告"""
        print("\n" + "=" * 80)
        print("检查报告")
        print("=" * 80)
        
        # 统计信息
        if report['stats']:
            print("\n统计信息:")
            for key, value in report['stats'].items():
                print(f"  {key}: {value}")
        
        # 警告
        if report['warnings']:
            print(f"\n⚠ 警告 ({len(report['warnings'])}):")
            for warning in report['warnings']:
                print(f"  {warning}")
        
        # 错误
        if report['errors']:
            print(f"\n✗ 错误 ({len(report['errors'])}):")
            for error in report['errors']:
                print(f"  {error}")
        
        # 总结
        print("\n" + "=" * 80)
        if report['success']:
            print("✓ 数据完整性检查通过！")
        else:
            print(f"✗ 数据完整性检查失败！发现 {len(report['errors'])} 个错误")
        print("=" * 80)


def check_directory(directory: str):
    """检查目录下所有episode的data.json"""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"错误: 目录不存在: {directory}")
        return False
    
    # 查找所有data.json文件
    data_files = sorted(dir_path.glob("*/data.json"))
    
    if not data_files:
        print(f"错误: 在 {directory} 下没有找到任何 data.json 文件")
        return False
    
    print(f"找到 {len(data_files)} 个数据文件")
    print("=" * 80)
    
    results = []
    all_success = True
    
    for data_file in data_files:
        episode_name = data_file.parent.name
        print(f"\n{'#' * 80}")
        print(f"# 检查 {episode_name}")
        print(f"{'#' * 80}\n")
        
        checker = DataIntegrityChecker(str(data_file))
        success, report = checker.check_all()
        checker.print_report(report)
        
        results.append({
            'episode': episode_name,
            'path': str(data_file),
            'success': success,
            'errors': len(report['errors']),
            'warnings': len(report['warnings']),
            'stats': report['stats']
        })
        
        if not success:
            all_success = False
    
    # 打印总结
    print("\n" + "=" * 80)
    print("总体检查结果")
    print("=" * 80)
    
    for result in results:
        status = "✓" if result['success'] else "✗"
        print(f"{status} {result['episode']}: ", end="")
        if result['success']:
            print(f"通过 (警告: {result['warnings']})")
        else:
            print(f"失败 (错误: {result['errors']}, 警告: {result['warnings']})")
        
        # 显示关键统计
        if 'total_frames' in result['stats']:
            print(f"    帧数: {result['stats']['total_frames']}", end="")
        if 'cameras' in result['stats']:
            print(f", 相机: {len(result['stats']['cameras'])}", end="")
        if 'file_size_mb' in result['stats']:
            print(f", 大小: {result['stats']['file_size_mb']:.2f}MB", end="")
        print()
    
    print("\n" + "=" * 80)
    success_count = sum(1 for r in results if r['success'])
    print(f"总计: {success_count}/{len(results)} 个数据集通过检查")
    print("=" * 80)
    
    return all_success


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  检查单个文件: python check_data_integrity.py <data.json路径>")
        print("  检查整个目录: python check_data_integrity.py <目录路径>")
        print("\n示例:")
        print("  python check_data_integrity.py /path/to/episode_0002/data.json")
        print("  python check_data_integrity.py /path/to/open_charge_door/")
        sys.exit(1)
    
    target_path = sys.argv[1]
    path_obj = Path(target_path)
    
    # 判断是文件还是目录
    if path_obj.is_file():
        # 检查单个文件
        checker = DataIntegrityChecker(target_path)
        success, report = checker.check_all()
        checker.print_report(report)
        sys.exit(0 if success else 1)
    elif path_obj.is_dir():
        # 检查整个目录
        success = check_directory(target_path)
        sys.exit(0 if success else 1)
    else:
        print(f"错误: 路径不存在: {target_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
