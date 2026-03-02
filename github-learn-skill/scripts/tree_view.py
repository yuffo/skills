#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录树生成器 - 类似 Linux tree 命令
生成项目的目录结构，过滤非代码文件
"""

import os
import sys
from pathlib import Path


def should_skip(name: str) -> bool:
    """判断是否应该跳过该目录/文件"""
    skip_patterns = [
        '.git', '.svn', '.hg',  # 版本控制
        'node_modules', 'bower_components',  # JS 依赖
        '__pycache__', '.pytest_cache', '.mypy_cache',  # Python 缓存
        'venv', 'env', '.env', '.venv', 'virtualenv', 'python',  # 虚拟环境
        '.idea', '.vscode',  # IDE
        'dist', 'build', 'target', 'out',  # 构建输出
        '.next', '.nuxt',  # 框架生成
        'coverage', '.coverage', 'htmlcov',  # 测试覆盖率
        '.github', '.gitlab-ci',  # CI/CD
    ]
    return name.startswith('.') or name in skip_patterns


def is_venv_dir(name: str) -> bool:
    """判断是否是虚拟环境目录（需要显示...省略）"""
    return name in ['python', 'venv', '.venv']


def should_include_file(name: str) -> bool:
    """判断是否应该包含该文件"""
    code_extensions = [
        '.py', '.js', '.ts', '.jsx', '.tsx',  # 脚本语言
        '.java', '.go', '.rs', '.swift', '.kt',  # 编译语言
        '.c', '.cpp', '.h', '.hpp', '.cs',  # C 系列
        '.rb', '.php', '.scala', '.r', '.m',  # 其他
        '.sql', '.sh', '.bat', '.ps1',  # 脚本
        '.md', '.rst', '.txt',  # 文档
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',  # 配置
    ]
    
    if name.startswith('.'):
        return False
    
    ext = Path(name).suffix.lower()
    return ext in code_extensions


def generate_tree(
    path: Path,
    prefix: str = "",
    is_last: bool = True,
    max_depth: int = 5,
    current_depth: int = 0
) -> str:
    """递归生成树形结构"""
    
    if current_depth > max_depth:
        return f"{prefix}{'└── ' if is_last else '├── '}... (深度限制)\n"
    
    result = ""
    name = path.name
    
    # 如果是根目录
    if current_depth == 0:
        result = f"{path}\n"
    else:
        connector = "└── " if is_last else "├── "
        result = f"{prefix}{connector}{name}\n"
    
    if path.is_dir():
        # 检查是否是虚拟环境目录（显示...省略内容）
        if is_venv_dir(path.name):
            connector = "└── " if is_last else "├── "
            return result + f"{prefix}{connector}...\n"
        
        try:
            items = list(path.iterdir())
        except PermissionError:
            return result + f"{prefix}    [权限拒绝]\n"
        
        # 过滤目录和文件
        dirs = []
        files = []
        
        for item in items:
            if should_skip(item.name):
                continue
            if item.is_dir():
                dirs.append(item)
            elif should_include_file(item.name):
                files.append(item)
        
        # 排序
        dirs.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())
        
        all_items = dirs + files
        
        for i, item in enumerate(all_items):
            is_last_item = i == len(all_items) - 1
            extension = "    " if is_last else "│   "
            result += generate_tree(
                item,
                prefix + extension,
                is_last_item,
                max_depth,
                current_depth + 1
            )
    
    return result


def get_stats(path: Path) -> dict:
    """获取项目统计信息"""
    stats = {
        'total_files': 0,
        'total_dirs': 0,
        'code_files': 0,
        'languages': {}
    }
    
    for root, dirs, files in os.walk(path):
        # 过滤目录（包括虚拟环境目录）
        dirs[:] = [d for d in dirs if not should_skip(d) and not is_venv_dir(d)]
        
        stats['total_dirs'] += len(dirs)
        
        for file in files:
            stats['total_files'] += 1
            if should_include_file(file):
                stats['code_files'] += 1
                ext = Path(file).suffix.lower()
                stats['languages'][ext] = stats['languages'].get(ext, 0) + 1
    
    return stats


def is_dangerous_path(path: Path) -> tuple[bool, str]:
    """检查路径是否是危险目录（仅拦截根目录和系统目录）"""
    path_str = str(path).lower()
    
    # 危险目录列表
    dangerous_paths = [
        '/', 'c:\\', 'd:\\', 'e:\\',  # 根目录
        'c:\\windows', 'c:\\program files', 'c:\\programdata',
        '/usr', '/bin', '/sbin', '/lib', '/sys', '/dev', '/etc',
    ]
    
    for dangerous in dangerous_paths:
        if path_str == dangerous or path_str.startswith(dangerous + '\\') or path_str.startswith(dangerous + '/'):
            return True, f"危险目录: {dangerous}"
    
    return False, "OK"


def main():
    if len(sys.argv) < 2:
        print("用法: python tree_view.py <项目路径>")
        print("示例: python tree_view.py ./my-project")
        print("\n⚠️ 警告: 不要在根目录或系统目录运行！")
        sys.exit(1)
    
    target_path = Path(sys.argv[1]).resolve()
    
    if not target_path.exists():
        print(f"错误: 路径不存在 {target_path}")
        sys.exit(1)
    
    # 安全检查
    is_dangerous, message = is_dangerous_path(target_path)
    if is_dangerous:
        print(f"错误: {message}")
        print(f"路径: {target_path}")
        print("请指定项目子目录")
        sys.exit(1)
    
    # 生成树
    print(generate_tree(target_path.resolve()))
    
    # 输出统计
    print("\n" + "="*50)
    stats = get_stats(target_path)
    print(f"总文件数: {stats['total_files']}")
    print(f"代码文件: {stats['code_files']}")
    print(f"目录数: {stats['total_dirs']}")
    
    if stats['languages']:
        print("\n文件类型分布:")
        for ext, count in sorted(stats['languages'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {ext or '(无扩展名)'}: {count}")


if __name__ == '__main__':
    main()
