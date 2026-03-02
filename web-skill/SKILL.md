---
name: web-extract
description: 网页提取,替代内置web-fetch
---

# Web Extract - 网页内容提取工具

## 描述
codebuddy的内置web-fetch工具会返回网页文本内容(更少token) 但是访问失败时会返回原始网页内容导致token消耗
此工具为解决此问题设计 此工具脚本会附带页面文本以及超链接和部分格式内容 读取文档页面时 首次默认调用  获取菜单超链接   使用 -s 跳过菜单 只显示正文

## 使用方法

```bash
python web_extract.py <URL> [选项]
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 目标网页URL | 必填 |
| `-l, --length` | 最大字符数 | 20000 |
| `-o, --output` | 输出文件路径 | 控制台输出 |
| `-w, --wait` | 浏览器等待时间(秒) | 10 |
| `-s, --skip-menu` | 跳过菜单/侧边栏(更节约token) | 关闭 |
| `-g, --github-issues` | GitHub Issues模式，提取issue/pr标题和链接 | 关闭 |
| `-c, --selector` | GitHub Issues模式的CSS选择器 | `#_r_4_-list-view-container > ul` |

### 示例

```bash
# 基础使用（包含导航菜单）
python web_extract.py https://www.codebuddy.cn/docs/ide/Account/credits
# 跳过菜单，只提取正文（更节约token）
python web_extract.py https://example.com -s
# 增加字符限制 默认20000
python web_extract.py https://example.com -l 50000
# 增加等待时间（适合慢加载页面）
python web_extract.py https://example.com -w 20

# GitHub Issues模式 - 提取issue/pr列表
python web_extract.py https://github.com/user/repo/issues -g
# GitHub Issues模式 - 自定义选择器
python web_extract.py https://github.com/user/repo/issues -g -c "#my-selector > ul"
```

## GitHub Issues 模式

专门用于提取 GitHub Issues/Pull Requests 列表，只返回标题和链接，输出 YAML 格式：

```yaml
---
url: https://github.com/user/repo/issues
selector: #_r_4_-list-view-container > ul
count: 25
issues:
  - title: "feat: add new feature"
    url: https://github.com/user/repo/pull/123
  - title: "fix: bug fix"
    url: https://github.com/user/repo/issues/122
---
```
