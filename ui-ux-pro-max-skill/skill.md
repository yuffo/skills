---
name: ui-ux-pro-max-skill
description: AI驱动的UI/UX设计智能工具包 提供设计系统生成/样式推荐/配色方案/字体配对 支持15种AI助手平台 (user)
---

# 功能概述
- 本 skill 为 AI 编程助手提供 UI/UX 设计智能，自动推荐设计系统、样式、配色、字体等
- 核心是 BM25 搜索引擎 + 100条行业推理规则，可根据产品类型自动生成完整设计系统

# 核心能力

| 能力             | 数据量 | 说明                                    |
|------------------|--------|-----------------------------------------|
| UI样式推荐       | 67种   | Glassmorphism/Minimalism/Brutalism等    |
| 配色方案         | 96种   | SaaS/电商/医疗/金融等行业专属           |
| 字体配对         | 57种   | Google Fonts精选组合                    |
| 图表类型         | 25种   | 仪表盘和分析推荐                        |
| UX指南           | 99条   | 最佳实践/反模式/无障碍规则              |
| 行业推理规则     | 100条  | 自动匹配产品类型→设计系统               |
| 技术栈指南       | 13种   | React/Next.js/Vue/SwiftUI/Flutter等     |

# 使用方式

## 1. 设计系统生成（核心功能）

```bash
# 生成完整设计系统
python scripts/search.py "SaaS dashboard" --design-system -p "MyApp"

# Markdown格式输出
python scripts/search.py "fintech banking" --design-system -f markdown

# 持久化到 design-system/ 目录
python scripts/search.py "beauty spa" --design-system --persist -p "SerenitySpa"
```

**输出示例**:
```
+----------------------------------------------------------------------------------------+
|  TARGET: MyApp - RECOMMENDED DESIGN SYSTEM                                             |
+----------------------------------------------------------------------------------------+
|  PATTERN: Hero + Features + CTA                                                        |
|  STYLE: Minimalism & Swiss Style                                                       |
|  COLORS: Primary #2563EB | Secondary #3B82F6 | CTA #F97316                            |
|  TYPOGRAPHY: Inter / Inter                                                             |
|  KEY EFFECTS: Subtle hover transitions, smooth shadows                                 |
|  AVOID: Emojis as icons, missing cursor:pointer, low contrast text                     |
+----------------------------------------------------------------------------------------+
```

## 2. 领域搜索

```bash
# 样式搜索
python scripts/search.py "glassmorphism" --domain style

# 配色搜索
python scripts/search.py "fintech" --domain color

# 字体搜索
python scripts/search.py "elegant serif" --domain typography

# 落地页模式
python scripts/search.py "conversion" --domain landing

# 图表推荐
python scripts/search.py "dashboard" --domain chart

# UX指南
python scripts/search.py "accessibility" --domain ux

# 产品类型
python scripts/search.py "SaaS" --domain product
```

## 3. 技术栈搜索

```bash
# React指南
python scripts/search.py "form validation" --stack react

# Next.js指南
python scripts/search.py "server component" --stack nextjs

# SwiftUI指南
python scripts/search.py "navigation" --stack swiftui

# Flutter指南
python scripts/search.py "state management" --stack flutter
```

**可用技术栈**: html-tailwind, react, nextjs, astro, vue, nuxtjs, nuxt-ui, svelte, swiftui, react-native, flutter, shadcn, jetpack-compose

# 持久化设计系统（Master + Overrides模式）

```bash
# 生成全局设计系统
python scripts/search.py "SaaS" --design-system --persist -p "MyApp"

# 生成页面特定覆盖
python scripts/search.py "SaaS" --design-system --persist -p "MyApp" --page "dashboard"
```

**生成的文件结构**:
```
design-system/
└── myapp/
    ├── MASTER.md           # 全局设计规范（颜色/字体/间距/组件）
    └── pages/
        └── dashboard.md    # 页面特定覆盖规则
```

**使用逻辑**:
1. 构建页面时，先检查 `design-system/pages/[page].md`
2. 如果存在，其规则**覆盖**MASTER.md
3. 如果不存在，严格遵循MASTER.md

# 推理规则示例

| 产品类型   | 推荐样式              | 配色情绪   | 反模式警告                    |
|------------|-----------------------|------------|-------------------------------|
| SaaS       | Minimalism + Flat     | Professional | 避免过度装饰                 |
| Fintech    | Glassmorphism + Dark  | Trust       | 禁用AI紫粉渐变               |
| Healthcare | Soft UI + Accessible  | Calm        | 避免鲜艳霓虹色               |
| E-commerce | Vibrant + Block-based | Energetic  | 避免暗黑模式                 |
| Gaming     | Cyberpunk + 3D        | Immersive  | 避免扁平设计                 |

# 预交付检查清单

生成设计系统时自动包含以下检查项:
- [ ] 不使用emoji作为图标（使用SVG: Heroicons/Lucide）
- [ ] 所有可点击元素有cursor:pointer
- [ ] 悬停状态有平滑过渡（150-300ms）
- [ ] 浅色模式文字对比度≥4.5:1
- [ ] 键盘导航有可见焦点状态
- [ ] 尊重prefers-reduced-motion
- [ ] 响应式: 375px, 768px, 1024px, 1440px

# 文件结构

```
ui-ux-pro-max-skill/
├── skill.md                    # 本文件
├── scripts/                    # Python搜索引擎
│   ├── core.py                 # BM25搜索引擎核心
│   ├── search.py               # CLI入口
│   └── design_system.py        # 设计系统生成器
└── data/                       # CSV数据库
    ├── styles.csv              # 67种UI样式
    ├── colors.csv              # 96种配色方案
    ├── typography.csv          # 57种字体配对
    ├── charts.csv              # 25种图表类型
    ├── landing.csv             # 8种落地页模式
    ├── products.csv            # 产品类型推荐
    ├── ux-guidelines.csv       # 99条UX指南
    ├── ui-reasoning.csv        # 100条推理规则
    └── stacks/                 # 13种技术栈指南
```

# 注意事项

- 需要Python 3.x环境
- 搜索引擎使用BM25算法，无需额外依赖
- CSV数据库位于 `data/` 目录，可直接编辑扩展
- 推理规则位于 `data/ui-reasoning.csv`，可添加新行业规则
- 输出格式支持ASCII（默认）和Markdown两种