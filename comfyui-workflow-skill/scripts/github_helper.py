#!/usr/bin/env python3
"""
GitHub 项目浏览工具

用于减少 AI token 消耗，提供两个轻量级接口：
1. ls - 列出项目根目录文件/文件夹
2. readme - 只读取 README.md 文件

用法：
    python github_helper.py ls <owner/repo>
    python github_helper.py readme <owner/repo>
    
示例：
    python github_helper.py ls comfyanonymous/ComfyUI
    python github_helper.py readme cubiq/ComfyUI_IPAdapter_plus
"""

import argparse
import json
import ssl
import urllib.request
import urllib.error
from typing import Optional, List, Dict

# 创建 SSL 上下文（处理 SSL 连接问题）
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class GitHubHelper:
    """GitHub 项目浏览帮助工具"""
    
    API_BASE = "https://api.github.com"
    RAW_BASE = "https://raw.githubusercontent.com"
    
    def __init__(self, token: str = None):
        """
        初始化
        
        Args:
            token: GitHub Personal Access Token (可选，用于提高 API 限制)
        """
        self.token = token
    
    def _make_request(self, url: str, headers: dict = None) -> Optional[bytes]:
        """发送 HTTP 请求"""
        req_headers = {
            "User-Agent": "ComfyUI-Workflow-Skill/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            req_headers["Authorization"] = f"token {self.token}"
        if headers:
            req_headers.update(headers)
        
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            elif e.code == 403:
                print("API 限制，请稍后重试或设置 GitHub Token")
                return None
            raise
        except Exception as e:
            print(f"请求失败: {e}")
            return None
    
    def list_root(self, owner: str, repo: str, branch: str = "main") -> Dict:
        """
        列出项目根目录文件和文件夹
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            branch: 分支名称 (默认 main)
        
        Returns:
            {
                "repo": "owner/repo",
                "branch": "main",
                "tree": [
                    {"name": "README.md", "type": "file"},
                    {"name": "nodes", "type": "dir"},
                    ...
                ]
            }
        """
        # 尝试 main 分支，失败则尝试 master
        for try_branch in [branch, "main", "master"]:
            url = f"{self.API_BASE}/repos/{owner}/{repo}/git/trees/{try_branch}?recursive=1"
            data = self._make_request(url)
            if data:
                try:
                    result = json.loads(data)
                    tree = result.get("tree", [])
                    # 只返回根目录项目
                    root_items = []
                    for item in tree:
                        # 根目录项目：路径中不包含 /
                        if "/" not in item["path"]:
                            root_items.append({
                                "name": item["path"],
                                "type": item["type"]  # "blob" = file, "tree" = dir
                            })
                    return {
                        "repo": f"{owner}/{repo}",
                        "branch": try_branch,
                        "tree": root_items
                    }
                except json.JSONDecodeError:
                    pass
        
        return {"error": f"无法访问仓库 {owner}/{repo}"}
    
    def read_readme(self, owner: str, repo: str, branch: str = "main") -> Dict:
        """
        读取 README.md 文件（通过 GitHub API）
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            branch: 分支名称 (默认 main)
        
        Returns:
            {
                "repo": "owner/repo",
                "branch": "main",
                "readme": "...content..."
            }
        """
        import base64
        
        # 方法1: 使用 GitHub API 获取 README
        url = f"{self.API_BASE}/repos/{owner}/{repo}/readme"
        data = self._make_request(url)
        if data:
            try:
                result = json.loads(data)
                content = base64.b64decode(result["content"]).decode("utf-8")
                return {
                    "repo": f"{owner}/{repo}",
                    "branch": result.get("branch", branch),
                    "file": result.get("name", "README.md"),
                    "readme": content
                }
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                pass
        
        # 方法2: 尝试直接访问 raw (备用)
        readme_names = ["README.md", "README.MD", "Readme.md", "readme.md"]
        for try_branch in [branch, "main", "master"]:
            for readme_name in readme_names:
                url = f"{self.RAW_BASE}/{owner}/{repo}/{try_branch}/{readme_name}"
                data = self._make_request(url, {"Accept": "text/plain"})
                if data:
                    try:
                        content = data.decode("utf-8")
                        return {
                            "repo": f"{owner}/{repo}",
                            "branch": try_branch,
                            "file": readme_name,
                            "readme": content
                        }
                    except UnicodeDecodeError:
                        pass
        
        return {"error": f"未找到 README 文件 ({owner}/{repo})"}
    
    def get_install_command(self, owner: str, repo: str) -> str:
        """获取安装命令"""
        return f"cd $COMFYUI_PATH/custom_nodes && git clone https://github.com/{owner}/{repo}"


def format_tree_output(result: Dict) -> str:
    """格式化目录列表输出"""
    if "error" in result:
        return f"错误: {result['error']}"
    
    lines = [
        f"仓库: {result['repo']}",
        f"分支: {result['branch']}",
        "",
        "根目录内容:"
    ]
    
    # 分类：先目录后文件，按名称排序
    dirs = [i for i in result["tree"] if i["type"] == "tree"]
    files = [i for i in result["tree"] if i["type"] == "blob"]
    
    dirs.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())
    
    for item in dirs:
        lines.append(f"  [DIR]  {item['name']}")
    for item in files:
        lines.append(f"  [FILE] {item['name']}")
    
    lines.append(f"\n共 {len(dirs)} 个目录, {len(files)} 个文件")
    
    return "\n".join(lines)


def format_readme_output(result: Dict, max_lines: int = 200) -> str:
    """格式化 README 输出"""
    if "error" in result:
        return f"错误: {result['error']}"
    
    content = result["readme"]
    lines = content.split("\n")
    
    output_lines = [
        f"仓库: {result['repo']}",
        f"分支: {result['branch']}",
        f"文件: {result.get('file', 'README.md')}",
        "=" * 60,
        ""
    ]
    
    # 限制行数以节省 token
    if len(lines) > max_lines:
        output_lines.extend(lines[:max_lines])
        output_lines.append(f"\n... 省略 {len(lines) - max_lines} 行 ...")
    else:
        output_lines.extend(lines)
    
    return "\n".join(output_lines)


def main():
    parser = argparse.ArgumentParser(
        description="GitHub 项目浏览工具（轻量级，减少 token 消耗）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s ls comfyanonymous/ComfyUI
  %(prog)s readme cubiq/ComfyUI_IPAdapter_plus
  %(prog)s ls Kosinkadink/ComfyUI-VideoHelperSuite --json
        """
    )
    
    parser.add_argument(
        "command",
        choices=["ls", "readme"],
        help="命令: ls=列出根目录, readme=读取README"
    )
    
    parser.add_argument(
        "repo",
        help="仓库名称 (格式: owner/repo)"
    )
    
    parser.add_argument(
        "--branch", "-b",
        default="main",
        help="分支名称 (默认: main)"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="JSON 格式输出"
    )
    
    parser.add_argument(
        "--token", "-t",
        help="GitHub Personal Access Token (可选)"
    )
    
    parser.add_argument(
        "--max-lines",
        type=int,
        default=200,
        help="README 最大行数 (默认: 200)"
    )
    
    args = parser.parse_args()
    
    # 解析 owner/repo
    parts = args.repo.split("/")
    if len(parts) != 2:
        print("错误: 仓库名称格式应为 owner/repo")
        return
    
    owner, repo = parts
    helper = GitHubHelper(token=args.token)
    
    if args.command == "ls":
        result = helper.list_root(owner, repo, args.branch)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_tree_output(result))
    
    elif args.command == "readme":
        result = helper.read_readme(owner, repo, args.branch)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_readme_output(result, args.max_lines))


if __name__ == "__main__":
    main()
