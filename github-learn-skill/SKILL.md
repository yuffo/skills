---
name: github-learn-skill
description: 从github仓库(已下载到本地)学习知识 制作教科书/代码骨架分析/目录结构扫描/代码结构分析 支持Python/JS/TS (user)
---

# 功能概述
- 本 skill 用于分析本地 GitHub 仓库，提取核心知识并生成结构化的学习文档。
- 由于包含代码骨架分析和目录结构脚本 也可以用于代码分析 (现包含nodejs/ts/python)

# 工作流程

1. 汉化README.md 新增文件为README_ZH.md 由AI AGENT处理汉化 意译 而不使用翻译软件
2. 可以参考项目中包含的examples 写一份examples的目录 列出表格 包含列名: example标题,描述,输入/输出.   描述内容写这个example用于做什么  输入输出为这个example核心代码的输入类型 输出类型
3. 按需使用脚本扫描仓库结构，识别关键文件
4. 结合脚本解析和README文件 写一份新的结构化文档MD  文档包含 1. 项目用途 2. 简短demo 文件名demo_1.py 链接在文档 能快速启动,直接运行,能解释代码核心内容 3. 功能展示demo 文件名demo_2.ipynb 链接在文档 生成一个ipynb文件展示各种功能

- 脚本模板: 
```markdown
    # 项目名

    ## 1. 项目概述
    - 一句话描述
    - 适用场景
    - 技术栈（从依赖分析提取）

    ## 2. 快速开始
    - 安装命令
    - demo_1.py 链接和简介
    - 运行结果预览

    ## 3. 核心功能展示
    - 功能点表格（名称、说明、对应demo单元格）
    - demo_2.ipynb 链接

    ## 4. 项目结构说明
    - 关键目录/文件解释
    - 入口文件

    ## 5. 参考资料
    - 原始README_ZH.md 链接
    - examples目录链接

    ## 6. 核心部分原理
    - 可以提及大概的执行流程
    - 可以说明代码遵循的一些业界规范 比如说明一个项目是遵循OPENAI接口规范 也就是说这部分是可替换为其他模型 其他代理商 可替换图形界面的软件

    ## 7. 可自定义部分内容
    - 说明哪些部分是用户一般可以自定义的 而有些部分是固定代码 一般不可变
```

# 注意事项
- 确认此技能运行在一个项目目录
- 可能会运行到一半开启新对话 将执行进度记录到AITODO.md 当新对话时打开这个文件查看任务进度 从任务进度开始执行 
- 如输出表格 表格形式如下 注意表格对齐 已使用等宽字体 中文字体是英文字体两倍宽度
    | 列1 | 列2 | 列3 |
    |-----|-----|---- |
    | A   | B   | C   |
    | 1   | 2   | 3   |
    | 甲  | 乙  | 丙  |
- 尽量使用中文
- 在输出示例代码后 简述这个示例的输入内容和输出内容是什么
- 使用脚本分析代码结构以节约token:
    - **分析流程**：
            ```
        第1层：目录结构 → tree_view.py <目录>     （AI 了解项目全貌）
            ↓
        第2层：依赖分析 → code_analyzer.py --deps <目录>  （了解项目依赖）
            ↓
        第3层：文件骨架 → code_analyzer.py <文件>   （AI 了解类/函数签名）
            ↓
        必要时查看完整源码
            ```
    - **脚本列表**：
        | 脚本                 | 功能             | 用法                                            | 输出                 |
        |----------------------|------------------|-------------------------------------------------|----------------------|
        | `tree_view.py`       | 目录树结构       | `python tree_view.py ./project`                 | 文件树 + 统计        |
        | `code_analyzer.py`   | 单文件骨架分析   | `python code_analyzer.py ./project/main.py`     | 类/函数/属性签名     |
        | `code_analyzer.py`   | 项目依赖分析     | `python code_analyzer.py --deps ./project`      | 依赖列表 + 脚本      |
    - **支持语言**：Python (.py), TypeScript (.ts/.tsx), JavaScript (.js/.jsx)
    - **使用示例**：
        ```bash
        # 1. 先看目录结构
        python scripts/tree_view.py ./my-project
        
        # 2. 分析项目依赖（了解技术栈）
        python scripts/code_analyzer.py --deps ./my-project
        
        # 3. 分析单个文件骨架（AI 根据目录结构选择）
        python scripts/code_analyzer.py ./my-project/core/module.py
        python scripts/code_analyzer.py ./my-project/src/index.ts
        ```
    - **code_analyzer.py 文件分析输出**：
        ```markdown
        # 文件: ./my-project/core/module.py (Python)
        
        ## 导入
          from typing import List, Dict
          import os
        
        ## 类: MyClass extends BaseClass
          属性:
            - name: str
            - items: List[Item]
          方法:
            - __init__(self, name: str) -> None
            - process(self, data: Dict) -> Result
        
        ## 顶层函数
          - helper_function(input: str) -> bool
        ```
    - **code_analyzer.py 依赖分析输出**：
        ```markdown
        # 项目依赖分析: ./my-project
        检测类型: nodejs
        
        ## NODEJS 依赖
        配置文件: package.json, package-lock.json
        生产依赖: 15 个
          - react
          - express
          - ...
        开发依赖: 8 个
          - typescript
          - jest
          - ...
        可用脚本: build, test, dev, start
        ```






