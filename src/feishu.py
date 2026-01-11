import requests
import os
import yaml
from datetime import datetime

def load_config(config_path='config.yaml'):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"配置加载失败: {e}")
        return None

# 从配置文件读取
config = load_config() or {}
feishu_config = config.get('feishu', {})

APP_ID = os.environ.get("FEISHU_APP_ID") or feishu_config.get('app_id')
APP_SECRET = os.environ.get("FEISHU_APP_SECRET") or feishu_config.get('app_secret')
APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN") or feishu_config.get('app_token')
TABLE_ID = os.environ.get("FEISHU_TABLE_ID") or feishu_config.get('table_id')
SUMMARY_FILE = os.path.join('data', 'summary.txt')

# 获取access_token
def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("tenant_access_token")
    else:
        raise Exception(f"获取 tenant_access_token 失败: {response.text}")

def read_summary():
    try:
        with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取摘要文件失败: {e}")
        return None

# 新增数据到表格
def add_summary_record():

    content = read_summary()
    if not content:
        print("摘要内容为空，跳过上传。")
        return

    today = datetime.today().strftime("%Y-%m-%d")
    # 飞书日期字段通常支持 Unix 时间戳（毫秒）或 "yyyy-MM-dd" 格式字符串
    # 这里为了保险起见，使用 Unix 时间戳
    today_unix_timestamp = int(datetime.strptime(today, "%Y-%m-%d").timestamp() * 1000)

    # 多维表格字段设置："日期" (Date类型) 和 "内容" (Text类型)
    fields = {
        "日期": today_unix_timestamp,
        "内容": content
    }

    token = get_tenant_access_token()
    if not token:
        return

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"fields": fields}

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            resp_json = response.json()
            if resp_json.get("code") == 0:
                print(f"成功将摘要写入飞书表格: {resp_json['data']['record']['record_id']}")
            else:
                print(f"写入飞书表格失败 (API错误): {resp_json}")
        else:
            print(f"写入飞书表格失败 (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"请求飞书 API 发生异常: {e}")

if __name__ == "__main__":
    add_summary_record()
