#!/usr/bin/env python3
"""
将图片序列转换为视频
"""

import cv2
import sys
from pathlib import Path
from tqdm import tqdm


def images_to_video(episode_dir, camera_id='color_0', fps=15, output_name=None):
    """
    将指定相机的图片序列转换为视频
    
    Args:
        episode_dir: episode目录路径
        camera_id: 相机ID，默认'color_0'
        fps: 视频帧率，默认30
        output_name: 输出视频名称，默认为episode名称
    """
    episode_path = Path(episode_dir)
    colors_dir = episode_path / 'colors'
    
    if not colors_dir.exists():
        print(f"❌ 目录不存在: {colors_dir}")
        return False
    
    # 查找所有指定相机的图片
    pattern = f"*_{camera_id}.jpg"
    images = sorted(colors_dir.glob(pattern))
    
    if not images:
        print(f"❌ 未找到图片: {pattern}")
        return False
    
    print(f"找到 {len(images)} 张图片")
    
    # 读取第一张图片获取尺寸
    first_img = cv2.imread(str(images[0]))
    if first_img is None:
        print(f"❌ 无法读取图片: {images[0]}")
        return False
    
    height, width = first_img.shape[:2]
    
    # 设置输出文件名
    if output_name is None:
        output_name = f"{episode_path.name}_{camera_id}.mp4"
    elif not output_name.endswith('.mp4'):
        output_name += '.mp4'
    
    output_path = episode_path / output_name
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    if not writer.isOpened():
        print(f"❌ 无法创建视频文件: {output_path}")
        return False
    
    # 写入视频
    print(f"生成视频: {output_path}")
    for img_path in tqdm(images, desc="处理中"):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"⚠️  跳过损坏的图片: {img_path}")
            continue
        writer.write(img)
    
    writer.release()
    
    # 检查文件大小
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"✅ 完成！")
    print(f"   视频: {output_path}")
    print(f"   分辨率: {width}x{height}")
    print(f"   帧数: {len(images)}")
    print(f"   帧率: {fps} fps")
    print(f"   时长: {len(images)/fps:.2f} 秒")
    print(f"   大小: {file_size:.2f} MB")
    
    return True


def batch_convert(data_dir, camera_id='color_0', fps=30):
    """批量转换目录下所有episode"""
    data_path = Path(data_dir)
    
    # 查找所有episode目录
    episodes = sorted([d for d in data_path.iterdir() if d.is_dir() and (d / 'colors').exists()])
    
    if not episodes:
        print(f"❌ 未找到episode目录: {data_dir}")
        return False
    
    print(f"找到 {len(episodes)} 个episode")
    print("=" * 80)
    
    success_count = 0
    for episode in episodes:
        print(f"\n处理: {episode.name}")
        if images_to_video(episode, camera_id, fps):
            success_count += 1
        print("-" * 80)
    
    print(f"\n✅ 完成！成功转换 {success_count}/{len(episodes)} 个视频")
    return success_count == len(episodes)


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  转换单个episode: python images_to_video.py <episode目录> [相机ID] [帧率]")
        print("  批量转换:        python images_to_video.py <数据目录> --batch [相机ID] [帧率]")
        print("\n示例:")
        print("  python images_to_video.py episode_0002")
        print("  python images_to_video.py episode_0002 color_0 30")
        print("  python images_to_video.py open_charge_door --batch")
        print("  python images_to_video.py open_charge_door --batch color_1 30")
        sys.exit(1)
    
    target = sys.argv[1]
    
    # 检查是否批量模式
    if '--batch' in sys.argv:
        camera_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '--batch' else 'color_0'
        fps = int(sys.argv[4]) if len(sys.argv) > 4 else 30
        success = batch_convert(target, camera_id, fps)
    else:
        camera_id = sys.argv[2] if len(sys.argv) > 2 else 'color_0'
        fps = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        success = images_to_video(target, camera_id, fps)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
