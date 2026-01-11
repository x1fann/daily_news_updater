import json
import os
import yaml
from openai import OpenAI

def load_config(config_path='config.yaml'):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"配置加载失败: {e}")
        return None

def load_history():
    """读取新闻数据"""
    history_file = os.path.join('data', 'history.json')
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取新闻文件失败: {e}")
        return []

def summarize_news():
    config = load_config()

    llm_config = config['llm']
    api_key = os.environ.get("LLM_API_KEY") or llm_config.get('api_key')

    client = OpenAI(
        api_key=api_key,
        base_url=llm_config.get('base_url', 'https://api.deepseek.com')
    )

    history = load_history()
    if not history:
        print("没有可总结的新闻内容。")
        return

    print(f"读取到 {len(history)} 条新闻，正在生成摘要...")

    summaries = []
    
    # 1. Map 阶段：逐条总结
    for i, item in enumerate(history):
        print(f"正在处理第 {i+1}/{len(history)} 条: {item.get('title')}...")
        
        # 截取前 5000 个字符以避免过长
        content_snippet = item.get('content', '')[:5000]
        
        single_prompt = f"""请简要总结这篇新闻的内容，注意保留核心事件和观点。标题: {item.get('title')}来源: {item.get('source')}正文:{content_snippet}"""
        try:
            response = client.chat.completions.create(
                model=llm_config.get('model', 'deepseek-chat'),
                messages=[
                    {"role": "system", "content": "你是一个经验丰富的新闻编辑，擅长总结新闻内容。"},
                    {"role": "user", "content": single_prompt},
                ],
                stream=False
            )
            summaries.append(f"【新闻 {i+1}】{item.get('title')}\n{response.choices[0].message.content}")
        except Exception as e:
            print(f"  -> 处理失败 (可能是内容敏感): {e}")
            summaries.append(f"【新闻 {i+1}】{item.get('title')}\n(内容无法处理: {e})")

    if not summaries:
        print("没有成功生成摘要。")
        return

    # 2. Reduce 阶段：汇总总结
    print("\n正在生成最终汇总报告...")
    combined_summaries = "\n\n".join(summaries)
    
    final_system_prompt = "你是一个专业的政治经济学分析专家。请根据来自于不同新闻机构提供的多条新闻摘要，进行深度的综合总结和分析。请将它们按主题分类（如：美国政治、俄乌冲突、拉美局势等），提炼出关键动态和影响。"
    final_user_prompt = f"以下是各条新闻的简要摘要：\n\n{combined_summaries}\n\n请帮我生成一份综合简报。"

    try:
        response = client.chat.completions.create(
            model=llm_config.get('model', 'deepseek-chat'),
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": final_user_prompt},
            ],
            stream=False
        )
        
        summary = response.choices[0].message.content
        print("\n" + "="*20 + " 新闻总结 " + "="*20 + "\n")
        print(summary)
        print("\n" + "="*50)
        
        # 可选：保存总结结果
        save_summary(summary)

    except Exception as e:
        print(f"生成最终汇总失败: {e}")

def save_summary(content):
    """保存总结结果到文件"""
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'summary.txt')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n总结已保存至: {output_path}")
    except Exception as e:
        print(f"保存总结失败: {e}")

if __name__ == "__main__":
    summarize_news()
