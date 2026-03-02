---
name: parallel-tool
description: 并行工具调用，批量执行 Python 脚本/命令,合并多次调用减少TOKEN消耗
---

# Parallel Tool - 并行工具调用执行器

## 描述
通用的并行工具调用框架，支持批量执行 Python 脚本和自定义工具。
所有任务并行执行，完成后统一返回结果。
适用于需要多次调用工具、减少 API 往返次数的场景。

**核心优势：**
- **并行执行** - 多线程/协程并发，大幅提升效率
- **减少调用** - 一次返回所有 tool_calls，减少 API 往返次数
- **减少上下文堆积** - 批量执行后一次性返回结果，避免上下文重复发送
- **错误隔离** - 单个任务失败不影响其他任务
- **通用性** - 支持 Python 脚本和自定义工具

## 使用方法

### 基础用法 - 多脚本并行执行

```bash
# 多个脚本并行执行（各自带参数）
python parallel_tool_executor.py -s script1.py:arg1,arg2 script2.py:arg3,arg4 script3.py

# 输出到文件
python parallel_tool_executor.py -s script1.py:arg1 script2.py:arg2 -o results.json
```

### 高级用法 - JSON 批量调用

```bash
# 使用 JSON 配置文件（适合复杂场景）
python parallel_tool_executor.py -j tool_calls.json
```

**tool_calls.json 格式：**
```json
{
  "tool_calls": [
    {
      "id": "call_1",
      "name": "python",
      "arguments": {
        "script_path": "script1.py",
        "args": ["arg1", "arg2"]
      }
    },
    {
      "id": "call_2",
      "name": "custom_tool",
      "arguments": {
        "param1": "value1"
      }
    }
  ],
  "config": {
    "max_workers": 10,
    "timeout": 30
  }
}
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-s, --scripts` | 脚本列表，格式：script.py 或 script.py:arg1,arg2 | 必填（与 -j 二选一） |
| `-j, --json` | JSON 配置文件路径 | 必填（与 -s 二选一） |
| `-w, --workers` | 最大并发数（控制同时执行的任务数） | 10 |
| `-t, --timeout` | 单个任务超时 (秒) | 30 |
| `-o, --output` | 输出文件路径 | 控制台输出 |

### 参数语法

```
script.py          - 无参数
script.py:a,b,c    - 带 3 个参数
script.py:"a,b,c"  - 参数含空格时用引号
```

## 示例

```bash
# 示例 1：ComfyUI 节点批量查询（各自带参数）
python parallel_tool_executor.py -s query_node.py:LoadImage query_node.py:SaveImage query_node.py:KSampler

# 示例 2：多脚本并行（不同参数）
python parallel_tool_executor.py -s process.py:input1,output1 process.py:input2,output2 -w 5

# 示例 3：输出到文件
python parallel_tool_executor.py -s script1.py:arg1 script2.py:arg2 -o results.json

# 示例 4：JSON 配置（复杂参数）
python parallel_tool_executor.py -j tool_calls.json -w 20 -t 60
```

## 典型应用场景

1. **ComfyUI 节点查询** - 批量查询多个节点骨架
2. **数据处理** - 并行处理多个文件
3. **API 批量调用** - 并发请求多个接口
4. **AI Agent 工具调用** - 减少 tool_calls 往返次数
5. **自动化脚本** - 批量执行任务

## 并发数说明

**并发数** 控制同时执行的任务数量，不是脚本总数。

| 场景 | 推荐并发数 | 说明 |
|------|-----------|------|
| IO 密集型（API/网络） | 50-100 | 等待响应时可执行其他任务 |
| CPU 密集型（计算/图像处理） | 4-8 | 等于 CPU 核心数 |
| 混合场景 | 10-20 | 默认值，适合大多数情况 |

**示例：** 100 个脚本，并发数 10 → 分 10 批执行，每批 10 个并行

## 输出格式

```json
{
  "results": [
    {
      "id": "script_0",
      "name": "python",
      "success": true,
      "result": {
        "stdout": "...",
        "stderr": "",
        "returncode": 0
      },
      "execution_time": 1.23
    }
  ],
  "summary": {
    "total": 3,
    "success": 3,
    "failed": 0,
    "total_time": 3.45
  }
}
```
