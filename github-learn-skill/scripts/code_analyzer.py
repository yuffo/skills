#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码骨架分析器 - 支持 Python / TypeScript / JavaScript
用法:
  python code_analyzer.py <文件路径>           # 分析单个文件骨架
  python code_analyzer.py --deps <目录路径>     # 分析项目依赖

说明:
  - Python 文件使用 Python AST 解析
  - JS/TS 文件调用 Node.js 脚本（js_analyzer.js）解析
"""

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any


class PythonAnalyzer:
    """Python 代码分析器"""
    
    def get_annotation(self, node) -> str:
        """将 AST 注解节点转换为字符串"""
        if node is None:
            return ''
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            value = self.get_annotation(node.value)
            slice_val = self.get_annotation(node.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(node, ast.Attribute):
            return f"{self.get_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.BinOp):
            left = self.get_annotation(node.left)
            right = self.get_annotation(node.right)
            return f"{left} | {right}"
        return ''
    
    def get_default_value(self, node) -> str:
        """获取参数默认值"""
        if node is None:
            return ''
        if isinstance(node, ast.Constant):
            return f" = {repr(node.value)}"
        elif isinstance(node, ast.Name):
            return f" = {node.id}"
        return " = ..."
    
    def format_function(self, node: ast.FunctionDef) -> str:
        """格式化函数签名"""
        args_info = []
        
        for i, a in enumerate(node.args.args):
            arg_str = a.arg
            if a.annotation:
                arg_str += f": {self.get_annotation(a.annotation)}"
            defaults_start = len(node.args.args) - len(node.args.defaults)
            if i >= defaults_start and node.args.defaults:
                default_idx = i - defaults_start
                arg_str += self.get_default_value(node.args.defaults[default_idx])
            args_info.append(arg_str)
        
        if node.args.vararg:
            vararg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg_str += f": {self.get_annotation(node.args.vararg.annotation)}"
            args_info.append(vararg_str)
        
        if node.args.kwarg:
            kwarg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg_str += f": {self.get_annotation(node.args.kwarg.annotation)}"
            args_info.append(kwarg_str)
        
        sig = f"{node.name}({', '.join(args_info)})"
        if node.returns:
            sig += f" -> {self.get_annotation(node.returns)}"
        return sig
    
    def analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """分析类定义"""
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self.format_function(item))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attr_type = self.get_annotation(item.annotation)
                attributes.append(f"{item.target.arg}: {attr_type}")
        
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        
        return {
            'name': node.name,
            'bases': bases,
            'attributes': attributes,
            'methods': methods
        }
    
    def analyze(self, file_path: Path) -> Dict[str, Any]:
        """分析 Python 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            result = {'file': str(file_path), 'imports': [], 'classes': [], 'functions': []}
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result['imports'].append(alias.asname if alias.asname else alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    names = [a.asname if a.asname else a.name for a in node.names]
                    result['imports'].append(f"from {module} import {', '.join(names)}")
                elif isinstance(node, ast.ClassDef):
                    result['classes'].append(self.analyze_class(node))
                elif isinstance(node, ast.FunctionDef):
                    result['functions'].append(self.format_function(node))
            
            return result
        except Exception as e:
            return {'file': str(file_path), 'error': str(e)}


class JSAnalyzer:
    """JavaScript/TypeScript 分析器（通过调用 Node.js 脚本）"""
    
    def __init__(self):
        self.js_script_path = Path(__file__).parent / 'js_analyzer.js'
    
    def analyze(self, file_path: Path) -> Dict[str, Any]:
        """调用 Node.js 脚本分析 JS/TS 文件"""
        try:
            # 检查 Node.js 脚本是否存在
            if not self.js_script_path.exists():
                return {
                    'file': str(file_path),
                    'error': f'Node.js 脚本不存在: {self.js_script_path}\n请确保 js_analyzer.js 在同级目录'
                }
            
            # 调用 Node.js 脚本
            result = subprocess.run(
                ['node', str(self.js_script_path), str(file_path)],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                return {
                    'file': str(file_path),
                    'error': f'Node.js 执行失败: {result.stderr}'
                }
            
            # Node.js 脚本直接输出格式化文本，不需要解析 JSON
            # 返回一个标记，让调用者知道这是 Node.js 输出
            return {
                'file': str(file_path),
                'nodejs_output': result.stdout
            }
            
        except FileNotFoundError:
            return {
                'file': str(file_path),
                'error': '未找到 node 命令\n请安装 Node.js 并添加到 PATH'
            }
        except Exception as e:
            return {'file': str(file_path), 'error': str(e)}


class DependencyAnalyzer:
    """项目依赖分析器"""
    
    def analyze_python_deps(self, project_path: Path) -> Dict[str, Any]:
        """分析 Python 项目依赖"""
        deps = {'type': 'python', 'files': [], 'packages': []}
        
        # 查找 requirements.txt
        req_file = project_path / 'requirements.txt'
        if req_file.exists():
            deps['files'].append('requirements.txt')
            with open(req_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 提取包名（忽略版本号）
                        pkg = re.split(r'[=<>!~]', line)[0].strip()
                        if pkg:
                            deps['packages'].append(pkg)
        
        # 查找 pyproject.toml
        pyproject = project_path / 'pyproject.toml'
        if pyproject.exists():
            deps['files'].append('pyproject.toml')
            with open(pyproject, 'r', encoding='utf-8') as f:
                content = f.read()
                # 简单提取 dependencies
                for match in re.finditer(r'"([^"]+)"\s*=', content):
                    pkg = match.group(1)
                    if pkg not in ['python', 'name', 'version', 'description']:
                        deps['packages'].append(pkg)
        
        # 查找 setup.py
        setup_py = project_path / 'setup.py'
        if setup_py.exists():
            deps['files'].append('setup.py')
        
        return deps
    
    def analyze_node_deps(self, project_path: Path) -> Dict[str, Any]:
        """分析 Node.js 项目依赖"""
        deps = {'type': 'nodejs', 'files': [], 'dependencies': [], 'devDependencies': []}
        
        # 查找 package.json
        pkg_file = project_path / 'package.json'
        if pkg_file.exists():
            deps['files'].append('package.json')
            try:
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                    deps['dependencies'] = list(pkg.get('dependencies', {}).keys())
                    deps['devDependencies'] = list(pkg.get('devDependencies', {}).keys())
                    deps['scripts'] = list(pkg.get('scripts', {}).keys())
            except Exception:
                pass
        
        # 查找 package-lock.json
        if (project_path / 'package-lock.json').exists():
            deps['files'].append('package-lock.json')
        
        # 查找 yarn.lock
        if (project_path / 'yarn.lock').exists():
            deps['files'].append('yarn.lock')
        
        # 查找 pnpm-lock.yaml
        if (project_path / 'pnpm-lock.yaml').exists():
            deps['files'].append('pnpm-lock.yaml')
        
        return deps
    
    def analyze_rust_deps(self, project_path: Path) -> Dict[str, Any]:
        """分析 Rust 项目依赖"""
        deps = {'type': 'rust', 'files': [], 'packages': []}
        
        cargo_toml = project_path / 'Cargo.toml'
        if cargo_toml.exists():
            deps['files'].append('Cargo.toml')
            with open(cargo_toml, 'r', encoding='utf-8') as f:
                content = f.read()
                # 提取 [dependencies] 下的包名
                in_deps = False
                for line in content.split('\n'):
                    line = line.strip()
                    if line == '[dependencies]':
                        in_deps = True
                        continue
                    elif line.startswith('[') and line.endswith(']'):
                        in_deps = False
                        continue
                    
                    if in_deps and line and not line.startswith('#'):
                        # 匹配: name = "version" 或 name = { ... }
                        match = re.match(r'(\w+)\s*=', line)
                        if match:
                            deps['packages'].append(match.group(1))
        
        return deps
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """分析项目依赖"""
        result = {
            'project_path': str(project_path),
            'detected_type': None,
            'dependencies': []
        }
        
        # 检测项目类型
        if (project_path / 'package.json').exists():
            result['detected_type'] = 'nodejs'
            result['dependencies'].append(self.analyze_node_deps(project_path))
        
        if any((project_path / f).exists() for f in ['requirements.txt', 'pyproject.toml', 'setup.py']):
            if result['detected_type'] is None:
                result['detected_type'] = 'python'
            result['dependencies'].append(self.analyze_python_deps(project_path))
        
        if (project_path / 'Cargo.toml').exists():
            if result['detected_type'] is None:
                result['detected_type'] = 'rust'
            result['dependencies'].append(self.analyze_rust_deps(project_path))
        
        if result['detected_type'] is None:
            result['detected_type'] = 'unknown'
        
        return result
    
    def generate_output(self, result: Dict[str, Any]) -> str:
        """生成依赖报告"""
        lines = [f"# 项目依赖分析: {result['project_path']}\n"]
        lines.append(f"检测类型: {result['detected_type']}\n")
        
        for dep in result['dependencies']:
            lines.append(f"## {dep['type'].upper()} 依赖")
            
            if dep.get('files'):
                lines.append(f"配置文件: {', '.join(dep['files'])}")
            
            if dep.get('packages'):
                lines.append(f"包数量: {len(dep['packages'])}")
                lines.append("主要包:")
                for pkg in dep['packages'][:20]:
                    lines.append(f"  - {pkg}")
                if len(dep['packages']) > 20:
                    lines.append(f"  ... 还有 {len(dep['packages'])-20} 个")
            
            if dep.get('dependencies'):
                lines.append(f"生产依赖: {len(dep['dependencies'])} 个")
                for pkg in dep['dependencies'][:15]:
                    lines.append(f"  - {pkg}")
                if len(dep['dependencies']) > 15:
                    lines.append(f"  ... 还有 {len(dep['dependencies'])-15} 个")
            
            if dep.get('devDependencies'):
                lines.append(f"开发依赖: {len(dep['devDependencies'])} 个")
                for pkg in dep['devDependencies'][:10]:
                    lines.append(f"  - {pkg}")
                if len(dep['devDependencies']) > 10:
                    lines.append(f"  ... 还有 {len(dep['devDependencies'])-10} 个")
            
            if dep.get('scripts'):
                lines.append(f"可用脚本: {', '.join(dep['scripts'][:10])}")
            
            lines.append("")
        
        return '\n'.join(lines)


def generate_file_output(result: Dict[str, Any], file_type: str) -> str:
    """生成文件骨架输出"""
    lines = [f"# 文件: {result['file']} ({file_type})\n"]
    
    if 'error' in result:
        lines.append(f"错误: {result['error']}")
        return '\n'.join(lines)
    
    # 导入
    if result.get('imports'):
        lines.append("## 导入")
        for imp in result['imports'][:15]:
            lines.append(f"  {imp}")
        if len(result['imports']) > 15:
            lines.append(f"  ... 还有 {len(result['imports'])-15} 个")
        lines.append("")
    
    # TypeScript 特有：类型别名
    if result.get('types'):
        lines.append("## 类型别名")
        for t in result['types'][:10]:
            lines.append(f"  type {t}")
        lines.append("")
    
    # TypeScript 特有：接口
    if result.get('interfaces'):
        lines.append("## 接口")
        for iface in result['interfaces'][:10]:
            lines.append(f"  interface {iface['name']}")
            if iface.get('extends'):
                lines.append(f"    继承: {', '.join(iface['extends'])}")
            if iface.get('properties'):
                for prop in iface['properties'][:8]:
                    lines.append(f"    - {prop}")
                if len(iface['properties']) > 8:
                    lines.append(f"    ... 还有 {len(iface['properties'])-8} 个属性")
        lines.append("")
    
    # 类
    for cls in result.get('classes', []):
        extends_info = ""
        if cls.get('extends'):
            extends_info = f" extends {cls['extends']}"
        if cls.get('bases'):
            extends_info = f" extends {', '.join(cls['bases'])}"
        if cls.get('implements'):
            extends_info += f" implements {', '.join(cls['implements'])}"
        
        lines.append(f"## 类: {cls['name']}{extends_info}")
        
        if cls.get('attributes'):
            lines.append("  属性:")
            for attr in cls['attributes'][:8]:
                lines.append(f"    - {attr}")
        
        if cls.get('methods'):
            lines.append("  方法:")
            for method in cls['methods'][:12]:
                lines.append(f"    - {method}")
            if len(cls['methods']) > 12:
                lines.append(f"    ... 还有 {len(cls['methods'])-12} 个方法")
        
        lines.append("")
    
    # 顶层函数
    if result.get('functions'):
        lines.append("## 顶层函数")
        for func in result['functions'][:20]:
            lines.append(f"  - {func}")
        if len(result['functions']) > 20:
            lines.append(f"  ... 还有 {len(result['functions'])-20} 个函数")
        lines.append("")
    
    return '\n'.join(lines)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python code_analyzer.py <文件路径>              # 分析单个文件")
        print("  python code_analyzer.py --deps <目录路径>       # 分析项目依赖")
        print("")
        print("示例:")
        print("  python code_analyzer.py ./main.py")
        print("  python code_analyzer.py ./src/index.ts")
        print("  python code_analyzer.py --deps ./my-project")
        sys.exit(1)
    
    # 依赖分析模式
    if sys.argv[1] == '--deps':
        if len(sys.argv) < 3:
            print("错误: 请指定项目目录路径")
            print("用法: python code_analyzer.py --deps <目录路径>")
            sys.exit(1)
        
        project_path = Path(sys.argv[2]).resolve()
        if not project_path.exists():
            print(f"错误: 路径不存在: {project_path}")
            sys.exit(1)
        
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(project_path)
        output = analyzer.generate_output(result)
        print(output)
        return
    
    # 单文件分析模式
    file_path = Path(sys.argv[1]).resolve()
    
    if not file_path.exists():
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)
    
    if not file_path.is_file():
        print(f"错误: 路径不是文件: {file_path}")
        print("提示: 如需分析项目依赖，请使用 --deps 参数")
        sys.exit(1)
    
    # 根据文件后缀选择分析器
    suffix = file_path.suffix.lower()
    
    if suffix == '.py':
        analyzer = PythonAnalyzer()
        result = analyzer.analyze(file_path)
        print(generate_file_output(result, 'Python'))
    
    elif suffix in ['.ts', '.tsx', '.js', '.jsx']:
        analyzer = JSAnalyzer()
        result = analyzer.analyze(file_path)
        
        # 检查是否是 Node.js 直接输出
        if 'nodejs_output' in result:
            print(result['nodejs_output'])
        elif 'error' in result:
            print(f"错误: {result['error']}")
            sys.exit(1)
        else:
            # 回退到旧格式
            print(generate_file_output(result, 'TypeScript' if 'ts' in suffix else 'JavaScript'))
    
    else:
        print(f"不支持的文件类型: {suffix}")
        print("支持的类型: .py, .ts, .tsx, .js, .jsx")
        sys.exit(1)


if __name__ == '__main__':
    main()
