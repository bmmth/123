# PythonAnywhere 部署指南

## 步骤 1：注册 PythonAnywhere 账号

1. 访问 https://www.pythonanywhere.com
2. 注册免费账号（Beginner 账号即可）

## 步骤 2：上传代码

### 方式 A：通过 Git（推荐）

```bash
# 在 PythonAnywhere 的 Bash Console 中
git clone https://github.com/你的用户名/nvidia-api-monitor.git
```

### 方式 B：手动上传

1. 在 PythonAnywhere Dashboard 点击 **Files**
2. 创建文件夹 `nvidia-api-monitor`
3. 上传以下文件：
   - `app.py`
   - `api_client.py`
   - `database.py`
   - `config.py`
   - `wsgi.py`
   - `requirements.txt`

## 步骤 3：创建虚拟环境

在 PythonAnywhere 的 Bash Console 中：

```bash
# 创建虚拟环境
mkvirtualenv nvidia-monitor --python=python3.10

# 安装依赖
pip install flask openai python-dateutil
```

## 步骤 4：配置 Web App

1. 回到 Dashboard，点击 **Web**
2. 点击 **Add a new web app**
3. 选择你的域名（免费版是 `你的用户名.pythonanywhere.com`）
4. 选择 **Manual configuration** → **Python 3.10**
5. 在 **Virtualenv** 设置中填入：`/home/你的用户名/.virtualenvs/nvidia-monitor`

## 步骤 5：配置 WSGI

在 Web 配置页面，点击 **WSGI configuration file**，修改为：

```python
import sys
import os

project_home = '/home/你的用户名/nvidia-api-monitor'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
from database import init_db
init_db()
```

## 步骤 6：配置 API Key

**重要：不要在代码中硬编码 API Key！**

### 方式 A：使用环境变量（推荐）

在 PythonAnywhere 的 Bash Console：

```bash
# 编辑 ~/.bashrc
echo 'export NVIDIA_API_KEY="nvapi-你的key"' >> ~/.bashrc
source ~/.bashrc
```

然后修改 `config.py`：

```python
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
```

### 方式 B：使用 PythonAnywhere Secrets

1. 在 Dashboard 点击 **Account** → **API Token**
2. 或者在 Web App 设置中添加环境变量

## 步骤 7：重启 Web App

在 Web 配置页面点击 **Reload** 按钮

## 步骤 8：访问你的 Dashboard

打开浏览器访问：`https://你的用户名.pythonanywhere.com`

---

## 免费版限制

| 限制项 | 说明 |
|--------|------|
| CPU 秒数 | 每天 100 秒 |
| 带宽 | 每月 3GB |
| 存储 | 512MB |
| 域名 | `用户名.pythonanywhere.com` |

如果超出限制，可以考虑升级到付费计划。

---

## 常见问题

### Q: 500 Internal Server Error

检查错误日志：
1. 在 Web 配置页面点击 **Log files**
2. 查看 **Error log**

### Q: 数据库文件在哪里？

SQLite 数据库会自动创建在 `data/api_stats.db`

### Q: 如何更新代码？

```bash
cd ~/nvidia-api-monitor
git pull  # 如果用 Git
```

然后在 Web 页面点击 **Reload**

---

## 安全建议

1. **不要**把 API Key 提交到公开仓库
2. 使用环境变量存储敏感信息
3. 定期检查调用日志，发现异常及时处理
