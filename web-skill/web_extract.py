#!/usr/bin/env python3
"""
网页关键内容提取工具 - 为AI优化，节约token
使用浏览器渲染模式，支持JavaScript动态页面
"""

import sys
import re
import argparse
import io
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class ContentExtractor(HTMLParser):
    """HTML内容提取器 - 保留链接"""
    
    def __init__(self, base_url=''):
        super().__init__()
        self.skip_depth = 0
        self.content_parts = []
        self.current_tag = ""
        self.base_url = base_url
        self.current_link = None  # 当前正在处理的链接
        
        # 跳过的标签 - 保留aside/nav用于提取侧边栏菜单
        self.skip_tags = {'script', 'style', 'footer', 'svg', 'canvas', 
                         'video', 'audio', 'iframe', 'noscript'}
        
        # 标签显示名称
        self.tag_names = {
            'h1': '【H1】', 'h2': '【H2】', 'h3': '【H3】',
            'h4': '【H4】', 'h5': '【H5】', 'h6': '【H6】',
            'p': '', 'li': '• ', 'td': '| ', 'th': '| ',
            'tr': '', 'table': '\n[表格]', 'a': '',
            'nav': '\n[导航]', 'aside': '\n[侧边栏]'
        }
        
        # 跳过包含这些class/id的元素 - 不跳过sidebar/nav以保留菜单
        self.skip_patterns = ['footer', 'ad', 'ads', 'comment', 'social', 'share', 
                             'related', 'recommend', 'cookie', 'popup', 'modal', 
                             'banner', 'widget', 'toolbar', 'advertisement']
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag in self.skip_tags:
            self.skip_depth += 1
            return
        
        # 检测class/id
        class_id = f" {attrs_dict.get('class', '')} {attrs_dict.get('id', '')} ".lower()
        if any(f' {p} ' in class_id for p in self.skip_patterns):
            self.skip_depth += 1
            return
        
        self.current_tag = tag
        
        # 处理链接 - A标签和其他可点击元素
        href = attrs_dict.get('href', '')
        if not href:
            # 尝试从data属性或onclick中提取链接
            href = attrs_dict.get('data-href', '')
        if not href:
            # 处理router-link的to属性
            href = attrs_dict.get('to', '')
        
        if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            # 转换为绝对URL
            if href.startswith('http'):
                self.current_link = href
            else:
                self.current_link = urljoin(self.base_url, href)
        
        # 添加标签前缀
        if tag in self.tag_names and self.tag_names[tag]:
            self.content_parts.append(self.tag_names[tag])
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip_depth -= 1
        
        # 链接结束，添加链接信息
        if tag == 'a' and self.current_link:
            self.content_parts.append(f"[{self.current_link}]")
            self.current_link = None
        
        # 添加换行
        if self.skip_depth <= 0 and tag in ['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr', 'table']:
            self.content_parts.append("\n")
    
    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        
        text = data.strip()
        if not text or len(text) < 1:
            return
        
        # 跳过无意义文本
        noise = ['shares', 'likes', 'comments', 'views', 'click here', 
                'read more', 'learn more', 'scroll to top', 'menu']
        if any(n in text.lower() for n in noise):
            return
        
        self.content_parts.append(text)
    
    def get_content(self):
        content = ''.join(self.content_parts)
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        return content.strip()


def extract_sidebar(html):
    """提取侧边栏导航"""
    patterns = [
        (r'<aside[^>]*>.*?</aside>', 'aside'),
        (r'<nav[^>]*>.*?</nav>', 'nav'),
        (r'<div[^>]*class=["\'][^"\']*sidebar[^"\']*["\'][^>]*>.*?</div>', 'sidebar'),
        (r'<div[^>]*class=["\'][^"\']*menu[^"\']*["\'][^>]*>.*?</div>', 'menu'),
        (r'<div[^>]*class=["\'][^"\']*VPSidebar[^"\']*["\'][^>]*>.*?</div>', 'VPSidebar'),
    ]
    
    for pattern, name in patterns:
        match = re.search(pattern, html, re.S | re.I)
        if match:
            content = match.group(0)
            inner = re.sub(r'^<[^>]+>', '', content)
            inner = re.sub(r'</[^>]+>$', '', inner)
            return inner
    return ""


def extract_article(html):
    """提取文章主体"""
    patterns = [
        (r'<article[^>]*>.*?</article>', 'article'),
        (r'<main[^>]*>.*?</main>', 'main'),
        (r'<div[^>]*class=["\'][^"\']*vp-doc[^"\']*["\'][^>]*>.*?</div>', 'vp-doc'),
        (r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>.*?</div>', 'content'),
        (r'<div[^>]*class=["\'][^"\']*markdown-body[^"\']*["\'][^>]*>.*?</div>', 'markdown'),
    ]
    
    for pattern, name in patterns:
        match = re.search(pattern, html, re.S | re.I)
        if match:
            content = match.group(0)
            inner = re.sub(r'^<[^>]+>', '', content)
            inner = re.sub(r'</[^>]+>$', '', inner)
            return inner
    
    body = re.search(r'<body[^>]*>(.*?)</body>', html, re.S | re.I)
    return body.group(1) if body else html


def smart_truncate(text, max_len=20000):
    """智能截断"""
    if len(text) <= max_len:
        return text
    
    truncated = text[:max_len]
    for char in ['。', '.', '！', '!', '？', '?', '\n\n']:
        pos = truncated.rfind(char)
        if pos > max_len * 0.7:
            return truncated[:pos + 1] + "\n\n[内容已截断...]"
    
    return truncated + "\n\n[内容已截断...]"


def fetch_with_browser(url, wait=5):
    """浏览器渲染获取"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        return None, "未安装selenium/webdriver-manager: pip install selenium webdriver-manager"
    
    chrome = Options()
    chrome.add_argument('--headless')
    chrome.add_argument('--no-sandbox')
    chrome.add_argument('--disable-dev-shm-usage')
    chrome.add_argument('--disable-gpu')
    chrome.add_argument('--window-size=1920,1080')
    chrome.add_argument('--disable-blink-features=AutomationControlled')
    chrome.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome)
        
        driver.get(url)
        
        WebDriverWait(driver, wait).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        import time
        time.sleep(2)
        
        html = driver.page_source
        current_url = driver.current_url
        
        driver.quit()
        return html, current_url
        
    except Exception as e:
        return None, str(e)


def extract_from_html(html, url, skip_menu=False):
    """从HTML提取内容 - 包括侧边栏和主内容
    
    Args:
        html: HTML内容
        url: 页面URL
        skip_menu: 是否跳过菜单/侧边栏（更节约token）
    """
    title = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    title = title.group(1).strip() if title else "无标题"
    
    desc = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    desc = desc.group(1).strip() if desc else ""
    
    full_content = ""
    
    if not skip_menu:
        # 提取侧边栏
        sidebar_html = extract_sidebar(html)
        sidebar_content = ""
        if sidebar_html:
            extractor_side = ContentExtractor(base_url=url)
            extractor_side.feed(sidebar_html)
            sidebar_content = extractor_side.get_content()
        
        if sidebar_content:
            full_content = f"[导航菜单]\n{sidebar_content}\n\n"
    
    # 提取主内容
    article = extract_article(html)
    extractor_main = ContentExtractor(base_url=url)
    extractor_main.feed(article)
    main_content = extractor_main.get_content()
    
    # 合并内容
    if skip_menu:
        full_content = main_content
    else:
        full_content += f"[正文内容]\n{main_content}"
    
    return {
        'url': url,
        'title': title,
        'description': desc,
        'content': full_content,
        'original_size': len(html)
    }


def fetch_and_extract(url, max_len=20000, wait=5, skip_menu=False):
    """主提取函数"""
    
    html, final_url = fetch_with_browser(url, wait)
    if html is None:
        return {'error': html}
    
    result = extract_from_html(html, final_url, skip_menu)
    
    extracted_len = len(result['content'])
    result['savings'] = round((1 - extracted_len / result['original_size']) * 100, 1) if result['original_size'] > 0 else 0
    
    result['content'] = smart_truncate(result['content'], max_len)
    result['final_size'] = len(result['content'])
    
    return result


def yaml_escape(text):
    """YAML字符串转义"""
    if not text:
        return '""'
    # 转义双引号和反斜杠
    text = text.replace('\\', '\\\\').replace('"', '\\"')
    # 如果包含特殊字符，用双引号包裹
    if any(c in text for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', "'", '\n']):
        return f'"{text}"'
    return text


def format_yaml(result):
    """YAML格式输出"""
    lines = [
        "---",
        f'title: {yaml_escape(result["title"])}',
        f'url: {result["url"]}',
    ]
    
    if result['description']:
        lines.append(f'description: {yaml_escape(result["description"])}')
    
    lines.extend([
        "stats:",
        f'  original_chars: {result["original_size"]}',
        f'  final_chars: {result["final_size"]}',
        f'  savings_percent: {result["savings"]}',
        "content: |",
    ])
    
    # 内容缩进
    for line in result['content'].split('\n'):
        lines.append(f"  {line}")
    
    lines.append("---")
    return '\n'.join(lines)


def fetch_github_issues(url, wait=5, selector="#_r_4_-list-view-container > ul"):
    """提取GitHub Issues列表页面的标题和链接
    
    Args:
        url: GitHub issues页面URL
        wait: 浏览器等待时间
        selector: CSS选择器，默认为 issues 列表容器
    """
    html, final_url = fetch_with_browser(url, wait)
    if html is None:
        return {'error': final_url}
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # 查找目标容器
    container = soup.select_one(selector)
    if not container:
        return {'error': f'未找到选择器: {selector}', 'html_preview': html[:2000]}
    
    issues = []
    for a in container.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        
        # 跳过空链接和无效链接
        if not text or not href:
            continue
        if href.startswith('#') or 'javascript:' in href:
            continue
        
        # 只保留 issue 和 pull request 链接
        if '/issues/' not in href and '/pull/' not in href:
            continue
        
        # 跳过搜索链接
        if 'issues?q=' in href:
            continue
        
        # 转换为绝对URL
        if not href.startswith('http'):
            href = urljoin('https://github.com', href)
        
        issues.append({
            'title': text,
            'url': href
        })
    
    return {
        'url': final_url,
        'selector': selector,
        'count': len(issues),
        'issues': issues
    }


def format_github_issues_yaml(result):
    """GitHub Issues YAML格式输出"""
    lines = [
        "---",
        f'url: {result["url"]}',
        f'selector: {result["selector"]}',
        f'count: {result["count"]}',
        "issues:",
    ]
    
    for issue in result['issues']:
        lines.append(f'  - title: {yaml_escape(issue["title"])}')
        lines.append(f'    url: {issue["url"]}')
    
    lines.append("---")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='网页关键内容提取工具 - YAML输出',
        epilog="""
示例:
  python web_extract.py https://example.com
  python web_extract.py https://example.com -l 50000 -w 10
  python web_extract.py https://example.com -s  # 跳过菜单，更节约token
  python web_extract.py https://example.com -o output.yaml
  python web_extract.py https://github.com/user/repo/issues -g  # GitHub Issues模式
  python web_extract.py https://github.com/user/repo/issues -g -c "#my-selector > ul"
        """
    )
    parser.add_argument('url', help='网页URL')
    parser.add_argument('-l', '--length', type=int, default=20000, help='最大长度(默认20000)')
    parser.add_argument('-o', '--output', help='输出文件')
    parser.add_argument('-w', '--wait', type=int, default=10, help='浏览器等待时间(秒)')
    parser.add_argument('-s', '--skip-menu', action='store_true', help='跳过菜单/侧边栏(更节约token)')
    parser.add_argument('-g', '--github-issues', action='store_true', help='GitHub Issues模式，提取标题和链接')
    parser.add_argument('-c', '--selector', default='#_r_4_-list-view-container > ul', help='GitHub Issues模式的CSS选择器')
    
    args = parser.parse_args()
    
    print(f"[提取] {args.url}")
    
    # GitHub Issues 模式
    if args.github_issues:
        print(f"[模式] GitHub Issues")
        print(f"[选择器] {args.selector}")
        print(f"[等待] 浏览器渲染中...\n")
        
        result = fetch_github_issues(args.url, args.wait, args.selector)
        
        if 'error' in result:
            print(f"[错误] {result['error']}")
            if 'html_preview' in result:
                print(f"\n[HTML预览]\n{result['html_preview']}")
            return
        
        output = format_github_issues_yaml(result)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"[保存] {args.output}")
        else:
            print(output)
        return
    
    # 普通模式
    if args.skip_menu:
        print(f"[模式] 跳过菜单/侧边栏")
    print(f"[等待] 浏览器渲染中...\n")
    
    result = fetch_and_extract(args.url, args.length, args.wait, args.skip_menu)
    
    if 'error' in result:
        print(f"[错误] {result['error']}")
        return
    
    output = format_yaml(result)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"[保存] {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
