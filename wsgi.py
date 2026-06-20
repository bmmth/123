"""
PythonAnywhere WSGI 配置文件
"""
import sys
import os

# 添加项目路径（替换成你的用户名）
project_home = '/home/你的用户名/nvidia-api-monitor'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 设置工作目录
os.chdir(project_home)

# 导入 Flask 应用
from app import app as application

# 初始化数据库
from database import init_db
init_db()
