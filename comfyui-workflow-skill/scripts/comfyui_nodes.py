#!/usr/bin/env python3
"""
ComfyUI 节点查询工具
通过静态解析 Python 文件获取节点信息（不加载 Python，支持未安装依赖的节点）

用法：
    python comfyui_nodes.py list              # 列出所有节点
    python comfyui_nodes.py info <节点名称>    # 查看节点详情
    python comfyui_nodes.py search <关键词>    # 搜索节点
"""

import argparse
import ast
import json
import os
import re
from pathlib import Path
from typing import Optional


class NodeClassVisitor(ast.NodeVisitor):
    """AST 访问器，提取节点类信息"""
    
    def __init__(self):
        self.classes = {}  # 类名 -> 类信息
        self.node_mappings = {}  # 节点名称 -> 类名
        self.current_class = None
    
    def visit_Assign(self, node):
        """处理赋值语句，提取 NODE_CLASS_MAPPINGS"""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "NODE_CLASS_MAPPINGS":
                if isinstance(node.value, ast.Dict):
                    for key, value in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Constant) and isinstance(value, ast.Name):
                            self.node_mappings[key.value] = value.id
                elif isinstance(node.value, ast.Name):
                    # NODE_CLASS_MAPPINGS = some_dict
                    pass
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node):
        """处理带注解的赋值（Python 3.6+）"""
        if isinstance(node.target, ast.Name) and node.target.id == "NODE_CLASS_MAPPINGS":
            if isinstance(node.value, ast.Dict):
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and isinstance(value, ast.Name):
                        self.node_mappings[key.value] = value.id
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """处理类定义"""
        self.current_class = node.name
        class_info = {
            "name": node.name,
            "bases": [self._get_name(base) for base in node.bases],
            "attributes": {},
            "methods": [],
        }
        
        # 提取类属性和方法
        for item in node.body:
            # 类属性赋值
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info["attributes"][target.id] = self._eval_node(item.value)
            
            # 带注解的赋值（RETURN_TYPES: tuple = ...）
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    class_info["attributes"][item.target.id] = self._eval_node(item.value)
            
            # 方法定义
            elif isinstance(item, ast.FunctionDef):
                class_info["methods"].append(item.name)
                # 特别处理 INPUT_TYPES 方法
                if item.name == "INPUT_TYPES":
                    class_info["input_types_method"] = True
        
        self.classes[node.name] = class_info
        self.current_class = None
        self.generic_visit(node)
    
    def _get_name(self, node):
        """获取名称节点的字符串表示"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ""
    
    def _eval_node(self, node):
        """尝试静态求值 AST 节点"""
        if node is None:
            return None
        
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(el) for el in node.elts)
        
        elif isinstance(node, ast.List):
            return [self._eval_node(el) for el in node.elts]
        
        elif isinstance(node, ast.Dict):
            keys = [self._eval_node(k) for k in node.keys]
            values = [self._eval_node(v) for v in node.values]
            return dict(zip(keys, values))
        
        elif isinstance(node, ast.Name):
            return f"<{node.id}>"
        
        elif isinstance(node, ast.Attribute):
            return f"<{self._get_name(node)}>"
        
        elif isinstance(node, ast.Call):
            return f"<call:{self._get_name(node.func)}>"
        
        elif isinstance(node, ast.BinOp):
            # 字符串拼接
            if isinstance(node.op, ast.Add):
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
            return "<binop>"
        
        return None


class ComfyUINodesScanner:
    """ComfyUI 节点扫描器"""
    
    def __init__(self, comfyui_path: str):
        self.comfyui_path = Path(comfyui_path)
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self._cache = None
    
    def scan_all(self, use_cache: bool = True) -> dict:
        """扫描所有节点"""
        if use_cache and self._cache is not None:
            return self._cache
        
        nodes = {}
        
        # 添加 ComfyUI 核心内置节点
        nodes.update(self._get_builtin_nodes())
        
        # 扫描 custom_nodes
        if self.custom_nodes_path.exists():
            for plugin_dir in sorted(self.custom_nodes_path.iterdir()):
                if plugin_dir.is_dir() and not plugin_dir.name.startswith("."):
                    plugin_nodes = self._scan_plugin(plugin_dir)
                    nodes.update(plugin_nodes)
        
        self._cache = nodes
        return nodes
    
    def _find_nodes_py(self) -> Optional[Path]:
        """查找 ComfyUI 核心节点文件 nodes.py
        
        支持数据目录和核心代码目录分离的场景：
        - COMFYUI_PATH 指向数据目录 (custom_nodes, models 等)
        - nodes.py 可能在同级或父级的 ComfyUI 安装目录中
        """
        # 1. 当前路径下的标准位置
        possible_paths = [
            self.comfyui_path / "nodes.py",
            self.comfyui_path / "comfy" / "nodes.py",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # 2. 在父目录下搜索 ComfyUI 安装（数据目录和核心代码分离的情况）
        parent_dir = self.comfyui_path.parent
        if parent_dir.exists():
            # 常见的 ComfyUI 安装目录名
            comfyui_names = ["ComfyUI", "comfyui", "ComfyUI-aki-v2.1", "ComfyUI_windows_portable"]
            
            for name in comfyui_names:
                # 检查 父目录/名称/nodes.py
                candidate = parent_dir / name / "nodes.py"
                if candidate.exists():
                    return candidate
                
                # 检查 父目录/名称/ComfyUI/nodes.py (便携版结构)
                candidate = parent_dir / name / "ComfyUI" / "nodes.py"
                if candidate.exists():
                    return candidate
            
            # 3. 广泛搜索：父目录下所有包含 nodes.py 的 ComfyUI 目录
            for subdir in parent_dir.iterdir():
                if subdir.is_dir():
                    candidate = subdir / "nodes.py"
                    if candidate.exists() and candidate.stat().st_size > 50000:  # nodes.py 通常 > 50KB
                        return candidate
                    candidate = subdir / "ComfyUI" / "nodes.py"
                    if candidate.exists() and candidate.stat().st_size > 50000:
                        return candidate
        
        return None
    
    def _get_builtin_nodes(self) -> dict:
        """扫描 ComfyUI 核心内置节点"""
        nodes = {}
        
        # 查找 nodes.py 文件
        nodes_py = self._find_nodes_py()
        
        if nodes_py is None:
            # 找不到 nodes.py，返回空字典
            # 用户可能只设置了数据目录，没有完整的 ComfyUI 安装
            return nodes
        
        try:
            # 解析 nodes.py 文件
            result = self._parse_python_file(nodes_py)
            
            node_mappings = result.get("node_mappings", {})
            classes = result.get("classes", {})
            
            # 构建节点信息
            for node_name, class_name in node_mappings.items():
                class_info = classes.get(class_name, {})
                node_info = self._build_node_info(node_name, class_name, class_info, "built-in")
                nodes[node_name] = node_info
        
        except Exception as e:
            pass
        
        return nodes
    
    def _scan_plugin(self, plugin_dir: Path) -> dict:
        """扫描单个插件"""
        nodes = {}
        init_file = plugin_dir / "__init__.py"
        
        if not init_file.exists():
            return nodes
        
        try:
            # 解析 __init__.py
            init_result = self._parse_python_file(init_file)
            
            # 获取节点映射
            node_mappings = init_result.get("node_mappings", {})
            classes = init_result.get("classes", {})
            
            # 检查是否有动态加载的子模块
            submodules = self._detect_submodules(init_file)
            
            # 如果有子模块，扫描子模块
            for submodule_path in submodules:
                sub_result = self._parse_python_file(submodule_path)
                node_mappings.update(sub_result.get("node_mappings", {}))
                classes.update(sub_result.get("classes", {}))
            
            # 如果没有找到映射，扫描所有 .py 文件
            if not node_mappings:
                for py_file in plugin_dir.rglob("*.py"):
                    if py_file.name == "__init__.py":
                        continue
                    file_result = self._parse_python_file(py_file)
                    node_mappings.update(file_result.get("node_mappings", {}))
                    classes.update(file_result.get("classes", {}))
            
            # 构建节点信息
            for node_name, class_name in node_mappings.items():
                class_info = classes.get(class_name, {})
                node_info = self._build_node_info(node_name, class_name, class_info, plugin_dir.name)
                nodes[node_name] = node_info
        
        except Exception as e:
            pass
        
        return nodes
    
    def _detect_submodules(self, init_file: Path) -> list:
        """检测动态加载的子模块"""
        submodules = []
        
        try:
            content = init_file.read_text(encoding="utf-8", errors="ignore")
            plugin_dir = init_file.parent
            
            # 模式1: importlib.import_module(".py.nodes.xxx", __name__)
            pattern = r'importlib\.import_module\s*\(\s*["\']([^"\']+)["\']'
            for match in re.finditer(pattern, content):
                module_path = match.group(1)
                # 转换相对路径为实际路径
                if module_path.startswith("."):
                    module_path = module_path[1:]  # 移除开头的点
                    parts = module_path.replace(".", "/").split("/")
                    py_file = plugin_dir.joinpath(*parts).with_suffix(".py")
                    if py_file.exists():
                        submodules.append(py_file)
                    # 也检查目录下的 __init__.py
                    py_dir = plugin_dir.joinpath(*parts)
                    if py_dir.is_dir():
                        init = py_dir / "__init__.py"
                        if init.exists():
                            submodules.append(init)
            
            # 模式2: from .xxx import NODE_CLASS_MAPPINGS
            pattern2 = r'from\s+["\']?\.([^"\'\s]+)["\']?\s+import'
            for match in re.finditer(pattern2, content):
                module_path = match.group(1)
                parts = module_path.replace(".", "/").split("/")
                py_file = plugin_dir.joinpath(*parts).with_suffix(".py")
                if py_file.exists():
                    submodules.append(py_file)
        
        except Exception:
            pass
        
        return list(set(submodules))
    
    def _parse_python_file(self, py_file: Path) -> dict:
        """解析 Python 文件，提取节点信息"""
        result = {
            "node_mappings": {},
            "classes": {},
        }
        
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_file))
            
            visitor = NodeClassVisitor()
            visitor.visit(tree)
            
            result["node_mappings"] = visitor.node_mappings
            result["classes"] = visitor.classes
            
            # 尝试提取动态构建的 NODE_CLASS_MAPPINGS
            dynamic_mappings = self._extract_dynamic_mappings(content)
            result["node_mappings"].update(dynamic_mappings)
            
        except SyntaxError:
            # AST 解析失败，回退到正则
            result["node_mappings"] = self._extract_node_mappings_regex(py_file)
        
        except Exception:
            pass
        
        return result
    
    def _extract_dynamic_mappings(self, content: str) -> dict:
        """尝试提取动态构建的映射（如遍历目录加载）"""
        mappings = {}
        
        # 匹配 NODE_CLASS_MAPPINGS[...] = ... 格式
        pattern = r'NODE_CLASS_MAPPINGS\s*\[\s*["\']([^"\']+)["\']\s*\]\s*='
        for match in re.finditer(pattern, content):
            mappings[match.group(1)] = match.group(1)  # 暂用名称作为类名
        
        return mappings
    
    def _extract_node_mappings_regex(self, py_file: Path) -> dict:
        """正则方式提取节点映射（AST 解析失败时的后备方案）"""
        mappings = {}
        
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            
            # 匹配 "NodeName": ClassName 格式
            pattern = r'"([^"]+)"\s*:\s*(\w+)'
            for match in re.finditer(pattern, content):
                node_name, class_name = match.groups()
                # 过滤一些非节点名称
                if not node_name.startswith("__") and len(node_name) > 2:
                    mappings[node_name] = class_name
        
        except Exception:
            pass
        
        return mappings
    
    def _build_node_info(self, node_name: str, class_name: str, class_info: dict, plugin_name: str) -> dict:
        """构建节点信息"""
        attrs = class_info.get("attributes", {})
        
        # 解析 INPUT_TYPES（支持大小写）
        input_types = self._parse_input_types(attrs.get("INPUT_TYPES") or attrs.get("input_types"))
        
        info = {
            "name": node_name,
            "class": class_name,
            "category": attrs.get("CATEGORY") or attrs.get("category") or f"custom_nodes/{plugin_name}",
            "plugin": plugin_name,
        }
        
        # 输入参数
        if input_types:
            info["input"] = input_types
        
        # 返回类型（支持大小写）
        return_types = attrs.get("RETURN_TYPES") or attrs.get("return_types")
        if return_types:
            info["return_types"] = return_types
        
        return_names = attrs.get("RETURN_NAMES") or attrs.get("return_names")
        if return_names:
            info["return_names"] = return_names
        
        # 执行函数（支持大小写）
        function = attrs.get("FUNCTION") or attrs.get("function")
        if function:
            info["function"] = function
        
        # 输出节点（支持大小写）
        if attrs.get("OUTPUT_NODE") or attrs.get("output_node"):
            info["output_node"] = True
        
        return info
    
    def _parse_input_types(self, value) -> dict:
        """解析 INPUT_TYPES 属性值"""
        if value is None:
            return {}
        
        # 如果已经是字典
        if isinstance(value, dict):
            return value
        
        # 如果是函数调用标记
        if isinstance(value, str) and value.startswith("<call:"):
            return {"_dynamic": "INPUT_TYPES 由方法动态生成，需要运行时获取"}
        
        return {}
    
    def get_node(self, node_name: str) -> Optional[dict]:
        """获取单个节点"""
        nodes = self.scan_all()
        return nodes.get(node_name)
    
    def search(self, keyword: str) -> dict:
        """搜索节点"""
        nodes = self.scan_all()
        keyword_lower = keyword.lower()
        
        return {
            name: info for name, info in nodes.items()
            if keyword_lower in name.lower() 
            or keyword_lower in info.get("category", "").lower()
            or keyword_lower in info.get("plugin", "").lower()
        }
    
    def by_input_type(self, type_name: str) -> dict:
        """根据输入类型查询节点"""
        nodes = self.scan_all()
        type_upper = type_name.upper()
        results = {}
        
        for name, info in nodes.items():
            input_data = info.get("input", {})
            
            # 检查 required 和 optional 参数类型
            for section in ["required", "optional"]:
                section_data = input_data.get(section, {})
                for param, details in section_data.items():
                    # 提取类型
                    param_type = None
                    if isinstance(details, dict):
                        param_type = details.get("type") or (details[0] if details else None)
                    elif isinstance(details, (list, tuple)) and len(details) > 0:
                        param_type = details[0]
                    
                    if param_type and isinstance(param_type, str) and param_type.upper() == type_upper:
                        results[name] = info
                        break
                if name in results:
                    break
        
        return results
    
    def by_output_type(self, type_name: str) -> dict:
        """根据输出类型查询节点"""
        nodes = self.scan_all()
        type_upper = type_name.upper()
        results = {}
        
        for name, info in nodes.items():
            return_types = info.get("return_types", [])
            
            # 检查返回类型
            if return_types:
                for ret_type in return_types:
                    if isinstance(ret_type, str) and ret_type.upper() == type_upper:
                        results[name] = info
                        break
        
        return results
    
    def list_types(self) -> dict:
        """列出所有已知的输入/输出类型"""
        nodes = self.scan_all()
        input_types = set()
        output_types = set()
        
        for info in nodes.values():
            # 收集输入类型
            input_data = info.get("input", {})
            for section in ["required", "optional"]:
                for details in input_data.get(section, {}).values():
                    if isinstance(details, dict):
                        t = details.get("type") or (details[0] if details else None)
                    elif isinstance(details, (list, tuple)) and len(details) > 0:
                        t = details[0]
                    else:
                        t = None
                    if t and isinstance(t, str):
                        t_upper = t.upper()
                        # 过滤无效类型
                        if len(t_upper) >= 2 and not t_upper.startswith("<") and t_upper.isupper():
                            input_types.add(t_upper)
            
            # 收集输出类型
            for ret_type in info.get("return_types", []):
                if isinstance(ret_type, str):
                    t_upper = ret_type.upper()
                    # 过滤无效类型
                    if len(t_upper) >= 2 and not t_upper.startswith("<") and t_upper.isupper():
                        output_types.add(t_upper)
        
        return {
            "input_types": sorted(input_types),
            "output_types": sorted(output_types)
        }


def format_node_list(nodes: dict, detailed: bool = False) -> str:
    """格式化节点列表输出"""
    if not nodes:
        return "未找到任何节点"
    
    lines = [f"共 {len(nodes)} 个节点"]
    
    if detailed:
        lines.append("=" * 50)
        sorted_nodes = sorted(nodes.items(), key=lambda x: (x[1].get("category", ""), x[0]))
        current_category = None
        for name, info in sorted_nodes:
            category = info.get("category", "unknown")
            if category != current_category:
                lines.append(f"\n[{category}]")
                current_category = category
            lines.append(f"  {name}")
    else:
        # 简洁模式：只输出节点名，每行多个
        names = sorted(nodes.keys())
        for i in range(0, len(names), 3):
            line = "  ".join(f"{n:25}" for n in names[i:i+3])
            lines.append(f"  {line}")
    
    return "\n".join(lines)


def format_node_detail(node_name: str, info: dict) -> str:
    """格式化节点详情"""
    if not info:
        return f"未找到节点: {node_name}"
    
    lines = [
        "\n" + "=" * 70,
        f"节点: {node_name}",
        "=" * 70,
        f"\n分类: {info.get('category', 'N/A')}",
        f"类名: {info.get('class', 'N/A')}",
        f"插件: {info.get('plugin', 'N/A')}",
    ]
    
    # 输入参数
    if "input" in info:
        lines.append("\n输入参数:")
        input_data = info["input"]
        
        for section in ["required", "optional"]:
            if section in input_data:
                lines.append(f"  [{section.upper()}]")
                section_data = input_data[section]
                
                for param, details in section_data.items():
                    if isinstance(details, dict):
                        param_type = details.get("type", details[0] if details else "unknown")
                        default = details.get("default", "")
                        lines.append(f"    - {param}: {param_type}" + (f" = {default}" if default else ""))
                    elif isinstance(details, (list, tuple)) and len(details) > 0:
                        lines.append(f"    - {param}: {details[0]}")
                    else:
                        lines.append(f"    - {param}")
    
    # 返回类型
    if "return_types" in info:
        lines.append("\n返回类型:")
        return_names = info.get("return_names", [])
        return_types = info["return_types"]
        
        for i, ret_type in enumerate(return_types):
            name = return_names[i] if i < len(return_names) else ""
            lines.append(f"  {i+1}. {ret_type}" + (f" ({name})" if name else ""))
    
    # 执行函数
    if "function" in info:
        lines.append(f"\n执行函数: {info['function']}")
    
    # 输出节点
    if info.get("output_node"):
        lines.append("\n[OUTPUT_NODE] True")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ComfyUI 节点查询工具（静态解析，无需启动 ComfyUI）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s list                    # 列出所有节点
  %(prog)s list -d                 # 详细模式
  %(prog)s info KSampler           # 查看节点详情
  %(prog)s search sampler          # 搜索节点
  %(prog)s by-input IMAGE          # 查找接受 IMAGE 输入的节点
  %(prog)s by-output MASK          # 查找输出 MASK 的节点
  %(prog)s types                   # 列出所有已知类型
  %(prog)s list --json             # JSON 输出
        """
    )
    
    parser.add_argument(
        "command",
        choices=["list", "info", "search", "by-input", "by-output", "types"],
        help="命令: list=列出节点, info=节点详情, search=搜索, by-input=按输入类型, by-output=按输出类型, types=列出类型"
    )
    
    parser.add_argument(
        "node_name",
        nargs="?",
        help="节点名称或搜索关键词"
    )
    
    parser.add_argument(
        "--comfyui-path", "-p",
        default=os.environ.get("COMFYUI_PATH", "F:/SD/comfy"),
        help="ComfyUI 安装路径 (默认: F:/SD/comfy 或 COMFYUI_PATH)"
    )
    
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="显示详细信息"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="JSON 格式输出"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用缓存，重新扫描"
    )
    
    args = parser.parse_args()
    
    scanner = ComfyUINodesScanner(args.comfyui_path)
    
    if args.command == "list":
        nodes = scanner.scan_all(use_cache=not args.no_cache)
        if args.json:
            print(json.dumps(nodes, indent=2, ensure_ascii=False))
        else:
            print(format_node_list(nodes, args.detailed))
    
    elif args.command == "info":
        if not args.node_name:
            print("错误: 请指定节点名称")
            return
        
        info = scanner.get_node(args.node_name)
        if args.json:
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            print(format_node_detail(args.node_name, info))
    
    elif args.command == "search":
        if not args.node_name:
            print("错误: 请指定搜索关键词")
            return
        
        results = scanner.search(args.node_name)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n搜索 '{args.node_name}' 找到 {len(results)} 个节点:")
            print(format_node_list(results, args.detailed))
    
    elif args.command == "by-input":
        if not args.node_name:
            print("错误: 请指定输入类型")
            return
        
        results = scanner.by_input_type(args.node_name)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n接受 '{args.node_name.upper()}' 输入的节点 ({len(results)} 个):")
            print(format_node_list(results, args.detailed))
    
    elif args.command == "by-output":
        if not args.node_name:
            print("错误: 请指定输出类型")
            return
        
        results = scanner.by_output_type(args.node_name)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n输出 '{args.node_name.upper()}' 的节点 ({len(results)} 个):")
            print(format_node_list(results, args.detailed))
    
    elif args.command == "types":
        types_info = scanner.list_types()
        if args.json:
            print(json.dumps(types_info, indent=2, ensure_ascii=False))
        else:
            print("\n已知的输入类型:")
            for t in types_info["input_types"]:
                print(f"  {t}")
            print(f"\n已知的输出类型:")
            for t in types_info["output_types"]:
                print(f"  {t}")


if __name__ == "__main__":
    main()
