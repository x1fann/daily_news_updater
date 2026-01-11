import yaml
import feedparser
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

HISTORY_FILE = os.path.join('data', 'history.json')
HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

def load_config(config_path='config.yaml'):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"配置加载失败: {e}")
        return None

def extract_main_text(soup):
    """正文提取逻辑"""
    # 1. 移除无关干扰标签
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
        tag.decompose()

    # 2. 依次尝试：<article> 标签 -> 有意义的 <p> 标签 -> <body> 兜底
    article = soup.find('article')
    if article and len(article.get_text()) > 100:
        return article.get_text(separator='\n', strip=True)

    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 10]
    full_text = '\n'.join(paragraphs)
    
    return full_text if len(full_text) > 50 else soup.body.get_text(separator='\n', strip=True)

def fetch_article_content(url, session):
    """获取单篇文章正文"""
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding # 自动识别编码
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        return extract_main_text(soup)
    except Exception as e:
        return f"爬取失败: {e}"

def save_to_history(data):
    """保存数据到历史文件"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    history = json.loads(content)
        except Exception as e:
            print(f"读取历史文件失败: {e}")

    # 查重更新
    updated = False
    for i, item in enumerate(history):
        if item.get('link') == data.get('link'):
            history[i] = data
            updated = True
            break

    if not updated:
        history.append(data)
        
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"写入历史文件失败: {e}")

def process_feed(source, session):
    """处理单个 RSS 源"""
    name, url = source.get('name', 'Unknown'), source.get('url')
    if not url: return

    print(f"\n>>> 正在获取: {name} ({url})")
    feed = feedparser.parse(url)
    for i, entry in enumerate(feed.entries[:10]):
        title = entry.get('title', '无标题')
        link = entry.get('link', '')
        print(f"  {i+1}. {title}\n     链接: {link}")

        if link:
            content = fetch_article_content(link, session)
            print(f"     共({len(content) if content else 0} 字)")
            
            # 保存到历史记录
            article_data = {
                'title': title,
                'link': link,
                'source': name,
                'content': content,
                'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            save_to_history(article_data)
        print("-" * 30)

def main():
    config = load_config()
    if not config or 'rss_sources' not in config:
        return

    with requests.Session() as session:
        for source in config['rss_sources']:
            try:
                process_feed(source, session)
            except Exception as e:
                print(f"处理源失败: {e}")

if __name__ == "__main__":
    main()