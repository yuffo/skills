#!/usr/bin/env python3
"""
ComfyUI 自定义节点 GitHub 仓库查询工具

用法：
    # 搜索节点仓库
    python scripts/comfyui_custom_nodes.py search <关键词>
    
    # 查看已安装插件信息
    python scripts/comfyui_custom_nodes.py list
    
    # 获取安装命令
    python scripts/comfyui_custom_nodes.py install <插件名>
"""

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path


# 常用 ComfyUI 自定义节点仓库索引
# 数据来源：https://github.com/ltdrdata/ComfyUI-Manager
KNOWN_REPOS = {
    # 基础工具
    "comfyui-controlnet-aux": "https://github.com/Fannovel16/comfyui_controlnet_aux",
    "comfyui-videohelpersuite": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
    "comfyui-ipadapter-plus": "https://github.com/cubiq/ComfyUI_IPAdapter_plus",
    "comfyui-instantid": "https://github.com/cubiq/ComfyUI_InstantID",
    "comfyui-ic-light": "https://github.com/kijai/ComfyUI-IC-Light",
    
    # 常用节点包
    "comfyui-easy-use": "https://github.com/yolain/ComfyUI-Easy-Use",
    "comfyui-essentials": "https://github.com/cubiq/ComfyUI_essentials",
    "was-node-suite": "https://github.com/WASasquatch/was-node-suite-comfyui",
    "comfyui-nodes": "https://github.com/pzc163/ComfyUI-Nodes",
    
    # AI 功能
    "comfyui-wd14-tagger": "https://github.com/pythongosssss/ComfyUI-WD14-Tagger",
    "comfyui-animatediff": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved",
    "comfyui-layerdiffuse": "https://github.com/huchenlei/ComfyUI-layerdiffuse",
    "comfyui-segment-anything": "https://github.com/storyicon/comfyui_segment_anything",
    
    # 模型加载
    "comfyui-smart-connection": "https://github.com/nagolinc/ComfyUI-Smart-Connection",
    "comfyui-model-downloader": "https://github.com/civitai/ComfyUI-Model-Downloader",
    
    # 图像处理
    "comfyui-imagick": "https://github.com/paulo-correia/ComfyUI-Imagick",
    "comfyui-image-filter": "https://github.com/Extraltodeus/ComfyUI-Image-Filter",
}


class ComfyUICustomNodesHelper:
    """自定义节点帮助工具"""
    
    def __init__(self, comfyui_path: str = None):
        self.comfyui_path = Path(comfyui_path) if comfyui_path else Path(os.environ.get("COMFYUI_PATH", "F:/SD/comfy"))
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
    
    def list_installed(self) -> list:
        """列出已安装的插件"""
        if not self.custom_nodes_path.exists():
            return []
        
        plugins = []
        for item in self.custom_nodes_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                plugin_info = {
                    "name": item.name,
                    "path": str(item),
                }
                
                # 尝试读取 git 信息
                git_dir = item / ".git"
                if git_dir.exists():
                    plugin_info["git"] = True
                    # 尝试读取远程仓库
                    try:
                        config_file = git_dir / "config"
                        if config_file.exists():
                            content = config_file.read_text(encoding="utf-8", errors="ignore")
                            match = re.search(r'url\s*=\s*(.+)', content)
                            if match:
                                plugin_info["repo"] = match.group(1).strip()
                    except:
                        pass
                
                plugins.append(plugin_info)
        
        return sorted(plugins, key=lambda x: x["name"].lower())
    
    def search_repo(self, keyword: str) -> list:
        """搜索节点仓库"""
        keyword_lower = keyword.lower()
        results = []
        
        for name, url in KNOWN_REPOS.items():
            if keyword_lower in name.lower():
                results.append({
                    "name": name,
                    "url": url,
                    "installed": self._is_installed(name)
                })
        
        return results
    
    def _is_installed(self, plugin_name: str) -> bool:
        """检查插件是否已安装"""
        plugin_dir = self.custom_nodes_path / plugin_name
        return plugin_dir.exists()
    
    def get_install_command(self, plugin_name: str) -> str:
        """获取安装命令"""
        # 先检查是否已知仓库
        for name, url in KNOWN_REPOS.items():
            if plugin_name.lower() in name.lower():
                install_path = self.custom_nodes_path / name
                return f"cd {self.custom_nodes_path} && git clone {url}"
        
        # 尝试从 GitHub 搜索
        return f"# 未找到仓库，请手动搜索:\n# https://github.com/search?q=ComfyUI+{plugin_name}&type=repositories"
    
    def search_github(self, keyword: str) -> list:
        """搜索 GitHub (提示用户手动操作)"""
        # 由于 GitHub API 限制，这里提供搜索 URL
        search_url = f"https://github.com/search?q=ComfyUI+{keyword}&type=repositories"
        return [{
            "hint": "请在浏览器中打开以下链接搜索",
            "url": search_url
        }]


def format_plugin_list(plugins: list) -> str:
    """格式化插件列表"""
    if not plugins:
        return "未找到已安装的插件"
    
    lines = [f"\n已安装 {len(plugins)} 个插件:\n"]
    lines.append("=" * 60)
    
    for plugin in plugins:
        status = "[git]" if plugin.get("git") else "[   ]"
        repo = plugin.get("repo", "")
        if repo:
            # 简化 URL
            repo = repo.replace("https://github.com/", "").replace(".git", "")
            lines.append(f"  {status} {plugin['name']:35} ({repo})")
        else:
            lines.append(f"  {status} {plugin['name']}")
    
    return "\n".join(lines)


def format_search_results(results: list) -> str:
    """格式化搜索结果"""
    if not results:
        return "未找到匹配的仓库"
    
    lines = [f"\n找到 {len(results)} 个仓库:\n"]
    lines.append("=" * 60)
    
    for result in results:
        installed = "[已安装]" if result.get("installed") else "[未安装]"
        lines.append(f"\n{installed}")
        lines.append(f"  名称: {result['name']}")
        lines.append(f"  地址: {result['url']}")
        if not result.get("installed"):
            lines.append(f"  安装: git clone {result['url']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ComfyUI 自定义节点仓库查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s list                           # 列出已安装插件
  %(prog)s search controlnet              # 搜索 controlnet 相关仓库
  %(prog)s install ipadapter              # 获取安装命令
        """
    )
    
    parser.add_argument(
        "command",
        choices=["list", "search", "install"],
        help="命令: list=已安装列表, search=搜索仓库, install=获取安装命令"
    )
    
    parser.add_argument(
        "keyword",
        nargs="?",
        help="搜索关键词或插件名"
    )
    
    parser.add_argument(
        "--comfyui-path", "-p",
        default=os.environ.get("COMFYUI_PATH", "F:/SD/comfy"),
        help="ComfyUI 安装路径"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="JSON 格式输出"
    )
    
    args = parser.parse_args()
    
    helper = ComfyUICustomNodesHelper(args.comfyui_path)
    
    if args.command == "list":
        plugins = helper.list_installed()
        if args.json:
            print(json.dumps(plugins, indent=2, ensure_ascii=False))
        else:
            print(format_plugin_list(plugins))
    
    elif args.command == "search":
        if not args.keyword:
            print("错误: 请指定搜索关键词")
            return
        
        results = helper.search_repo(args.keyword)
        
        # 如果本地索引没找到，提示 GitHub 搜索
        if not results:
            github_results = helper.search_github(args.keyword)
            print(f"\n本地索引未找到 '{args.keyword}'")
            print(f"请访问: {github_results[0]['url']}")
        elif args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(format_search_results(results))
    
    elif args.command == "install":
        if not args.keyword:
            print("错误: 请指定插件名")
            return
        
        cmd = helper.get_install_command(args.keyword)
        print(f"\n安装命令:\n{cmd}")


if __name__ == "__main__":
    main()
