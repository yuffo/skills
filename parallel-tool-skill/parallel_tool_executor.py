"""
并行工具调用执行器
支持多线程/协程并行执行 Python 命令，所有任务完成或出错后返回结果
"""

import asyncio
import subprocess
import json
import time
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import traceback


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]
    script_path: Optional[str] = None  # Python 脚本路径


@dataclass
class ToolResult:
    """工具执行结果"""
    id: str
    name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


class ParallelToolExecutor:
    """并行工具执行器"""
    
    def __init__(self, max_workers: int = 10, timeout: int = 60):
        """
        Args:
            max_workers: 最大并发线程数
            timeout: 单个任务超时时间 (秒)
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.tools: Dict[str, Callable] = {}
        
        # 注册内置工具
        self.register_tool("python", self._run_python_command)
    
    def register_tool(self, name: str, func: Callable):
        """注册自定义工具"""
        self.tools[name] = func
        print(f"[注册工具] {name}")
    
    async def execute_single(self, tool_call: ToolCall) -> ToolResult:
        """执行单个工具调用"""
        start_time = time.time()
        try:
            if tool_call.name not in self.tools:
                return ToolResult(
                    id=tool_call.id,
                    name=tool_call.name,
                    success=False,
                    error=f"未知工具：{tool_call.name}"
                )
            
            func = self.tools[tool_call.name]
            
            # 如果是协程，直接 await；如果是普通函数，在线程池执行
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(**tool_call.arguments),
                    timeout=self.timeout
                )
            else:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        lambda: func(**tool_call.arguments)
                    )
                    result = await asyncio.wait_for(
                        asyncio.wrap_future(future),
                        timeout=self.timeout
                    )
            
            execution_time = time.time() - start_time
            return ToolResult(
                id=tool_call.id,
                name=tool_call.name,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=f"执行超时 (>{self.timeout}秒)",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
                execution_time=time.time() - start_time
            )
    
    async def execute_batch(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """
        批量并行执行工具调用
        
        Args:
            tool_calls: 工具调用列表
        
        Returns:
            所有工具的执行结果列表
        """
        if not tool_calls:
            return []
        
        print(f"\n[开始批量执行] 共 {len(tool_calls)} 个任务，最大并发：{self.max_workers}")
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def bounded_execute(tool_call: ToolCall) -> ToolResult:
            async with semaphore:
                return await self.execute_single(tool_call)
        
        # 并行执行所有任务
        tasks = [bounded_execute(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常情况
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ToolResult(
                    id=tool_calls[i].id,
                    name=tool_calls[i].name,
                    success=False,
                    error=f"任务异常：{str(result)}"
                ))
            else:
                processed_results.append(result)
        
        # 统计结果
        success_count = sum(1 for r in processed_results if r.success)
        fail_count = len(processed_results) - success_count
        total_time = sum(r.execution_time for r in processed_results)
        
        print(f"[执行完成] 成功：{success_count}, 失败：{fail_count}, 总耗时：{total_time:.2f}秒")
        
        return processed_results
    
    def _run_python_command(self, script_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        执行 Python 命令（同步）
        
        Args:
            script_path: Python 脚本路径
            args: 命令行参数列表
        
        Returns:
            执行结果 {stdout, stderr, returncode}
        """
        cmd = ["python", script_path]
        if args:
            cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='ignore'
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "script": script_path
            }
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"脚本执行超时：{script_path}")
        except Exception as e:
            raise RuntimeError(f"执行失败：{str(e)}")


# ============ 使用示例 ============

async def demo():
    """演示用法"""
    
    # 1. 创建执行器
    executor = ParallelToolExecutor(max_workers=5, timeout=30)
    
    # 2. 注册自定义工具（可选）
    def query_node_skeleton(node_name: str) -> Dict[str, Any]:
        """查询节点骨架（模拟）"""
        return {
            "node_name": node_name,
            "inputs": ["image", "mask"],
            "outputs": ["image"],
            "category": "image"
        }
    
    def query_all_nodes() -> List[str]:
        """查询所有节点（模拟）"""
        return ["LoadImage", "SaveImage", "PreviewImage", "KSampler", "VAEDecode"]
    
    executor.register_tool("query_node_skeleton", query_node_skeleton)
    executor.register_tool("query_all_nodes", query_all_nodes)
    
    # 3. 准备批量任务
    tool_calls = [
        ToolCall(id="call_1", name="query_all_nodes", arguments={}),
        ToolCall(id="call_2", name="query_node_skeleton", arguments={"node_name": "LoadImage"}),
        ToolCall(id="call_3", name="query_node_skeleton", arguments={"node_name": "SaveImage"}),
        ToolCall(id="call_4", name="query_node_skeleton", arguments={"node_name": "PreviewImage"}),
        ToolCall(id="call_5", name="python", arguments={
            "script_path": "test.py",
            "args": ["--arg1", "value1"]
        }),
    ]
    
    # 4. 并行执行
    results = await executor.execute_batch(tool_calls)
    
    # 5. 处理结果
    print("\n=== 执行结果 ===")
    for result in results:
        if result.success:
            print(f"[OK] {result.id} ({result.name}): {result.result}")
        else:
            print(f"[FAIL] {result.id} ({result.name}): {result.error}")

    return results


def run_python_batch(scripts: List[Dict[str, Any]], max_workers: int = 5) -> List[Dict[str, Any]]:
    """
    简化版：并行执行多个 Python 脚本
    
    Args:
        scripts: 脚本列表 [{"script_path": "xxx.py", "args": ["arg1", "arg2"]}, ...]
        max_workers: 最大并发数
    
    Returns:
        执行结果列表
    """
    async def _run():
        executor = ParallelToolExecutor(max_workers=max_workers)
        
        tool_calls = [
            ToolCall(
                id=f"script_{i}",
                name="python",
                arguments={
                    "script_path": s["script_path"],
                    "args": s.get("args", [])
                }
            )
            for i, s in enumerate(scripts)
        ]
        
        results = await executor.execute_batch(tool_calls)
        return [asdict(r) for r in results]
    
    return asyncio.run(_run())


if __name__ == "__main__":
    import sys
    import io
    # Windows 控制台 UTF-8 支持
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="并行工具调用执行器 - 批量执行 Python 脚本/命令",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 并行执行多个脚本（各自带参数）
  python parallel_tool_executor.py -s script1.py:arg1,arg2 script2.py:arg3,arg4 script3.py

  # 使用 JSON 配置（适合复杂场景）
  python parallel_tool_executor.py -j tool_calls.json

  # 输出到文件
  python parallel_tool_executor.py -s script1.py:arg1 script2.py:arg2 -o results.json

参数语法:
  script.py          - 无参数
  script.py:a,b,c    - 带 3 个参数
  script.py:"a,b,c"  - 参数含空格时用引号
        """
    )

    parser.add_argument("-s", "--scripts", nargs="+", help="脚本路径列表，格式：script.py 或 script.py:arg1,arg2")
    parser.add_argument("-j", "--json", dest="json_file", help="JSON 配置文件路径")
    parser.add_argument("-w", "--workers", type=int, default=10, help="最大并发数 (默认：10)")
    parser.add_argument("-t", "--timeout", type=int, default=30, help="单个任务超时秒数 (默认：30)")
    parser.add_argument("-o", "--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    if not args.scripts and not args.json_file:
        # 无参数运行演示
        print("=== 演示模式 ===")
        asyncio.run(demo())
    else:
        # 执行批量任务
        async def run_batch():
            executor = ParallelToolExecutor(max_workers=args.workers, timeout=args.timeout)
            
            if args.json_file:
                # 从 JSON 加载
                with open(args.json_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        name=tc["name"],
                        arguments=tc["arguments"]
                    )
                    for tc in config.get("tool_calls", [])
                ]
                
                # 覆盖配置
                if "config" in config:
                    executor.max_workers = config["config"].get("max_workers", args.workers)
                    executor.timeout = config["config"].get("timeout", args.timeout)
            else:
                # 从命令行加载 - 支持 script.py:arg1,arg2 语法
                # 注意：Windows 路径含冒号 (C:)，需要找最后一个冒号
                tool_calls = []
                for i, script_entry in enumerate(args.scripts):
                    # 找最后一个冒号（避开 Windows 盘符 C:）
                    last_colon = script_entry.rfind(":")
                    if last_colon > 1:  # 冒号不在开头且不是盘符
                        script_path = script_entry[:last_colon]
                        args_str = script_entry[last_colon+1:]
                        script_args = args_str.split(",") if args_str else []
                    else:
                        script_path = script_entry
                        script_args = []
                    
                    tool_calls.append(
                        ToolCall(
                            id=f"script_{i}",
                            name="python",
                            arguments={
                                "script_path": script_path,
                                "args": script_args
                            }
                        )
                    )
            
            # 执行
            results = await executor.execute_batch(tool_calls)
            
            # 输出
            output_data = {
                "results": [asdict(r) for r in results],
                "summary": {
                    "total": len(results),
                    "success": sum(1 for r in results if r.success),
                    "failed": sum(1 for r in results if not r.success),
                    "total_time": sum(r.execution_time for r in results)
                }
            }
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存到：{args.output}")
            else:
                print("\n=== 执行结果 ===")
                print(json.dumps(output_data, ensure_ascii=False, indent=2))
        
        asyncio.run(run_batch())
