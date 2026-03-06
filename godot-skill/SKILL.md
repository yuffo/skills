---
name: godot-skill
description: Godot项目开发规范与最佳实践指南 (user)
---
# 本skill功能
- 指导AI编写godot代码 适应新版特性 避免废弃方法
- 提供精简API骨架供快速查阅

# 注意事项
- godot版本为4.6 而AIAgent缺乏新版本知识 如发生错误 需要参考文档
- 配置属性时默认不创建新资源文件 直接设置在属性上
- 未指明场景默认2dshader canvas_item类型

# API骨架使用
- godot-docs文档位于  F:\SD\godot-docs
- 文档可供参考 使用es命令搜索此位置的文档 rst文档非常大 谨慎访问 但api_skeleton有提供的简化代码骨架

## 目录结构
```
godot-docs/
├── api_skeleton/         # API骨架 917个类 (~1MB) - 快速查阅
├── api_yaml/             # 简化的API详细YAML文档
├── tutorials_md/         # 教程 
├── getting_started_md/   # 入门指南
└── engine_details_md/    # 引擎细节
```
- 大部分情况 参考api_skeleton/ 来解决问题
- 如果仅靠api_skeleton无法解决 参考api_yaml/
- 需要教程时 查看*_md/ 文件夹 内容较多 仅需要时访问
- 可使用rg命令进行内容搜索
- 文档根目录以上文件夹外rst严禁访问 一些api文档内容巨大造成token浪费

## 查询API
骨架格式示例 (api_skeleton/Node.txt):
```
class Node : Object
  var owner: Node
  var name: StringName
  signal ready()
  signal tree_entered()
  enum ProcessMode:
    PROCESS_MODE_INHERIT = 0
    PROCESS_MODE_PAUSABLE = 1
  func _process(delta: float) -> void virtual
  func get_child(idx: int) -> Node const
  func add_child(node: Node, force_readable_name: bool = false) -> void
```

使用方法:
1. 快速查类: 读取 `api_skeleton/{类名}.txt`
2. 查继承链: 父类也在骨架目录中
3. 详细教程: 查看对应 `api_yaml/` 子目录

## 骨架格式说明
- `var`: 属性
- `signal`: 信号
- `enum`: 枚举及常量
- `func`: 方法(含参数类型、返回类型、限定符virtual/const)
