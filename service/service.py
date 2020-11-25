# coding=utf-8
import os
import json
import Kit
import pymysql
import logging
import requests
import sentry_sdk
from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
from requests import utils
from flask_cors import CORS
from Config import get_config
from dbutils.pooled_db import PooledDB
from concurrent.futures import ThreadPoolExecutor
from sentry_sdk.integrations.flask import FlaskIntegration

# 获取配置
app_config = get_config()
base_path = os.path.split(os.path.abspath(__file__))[0]

# Sentry
sentry_sdk.init(
    dsn=app_config['SERVICE']['dsn'],
    integrations=[FlaskIntegration()],
    environment=app_config["RUN_ENV"]
)

# 初始化应用
app = Flask(__name__)
app.config.from_mapping(app_config)

# 服务日志
file_logger = logging.getLogger('file_log')
file_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(filename='{}/log/run.log'.format(base_path), encoding="utf-8")
file_handler.setFormatter(logging.Formatter('%(asctime)s:<%(levelname)s> %(message)s'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# 初始化连接池
for key in app.config.get('POOL').keys():
    app.config.get('POOL')[key] = int(app.config.get('POOL')[key])
app.config.get('MYSQL')["port"] = int(app.config.get('MYSQL')["port"])
pool_config = app.config.get('POOL')
mysql_config = app.config.get('MYSQL')
app.mysql_pool = PooledDB(creator=pymysql, **mysql_config, **pool_config)

# 初始化异步线程与谅解
app.mysql_conn = app.mysql_pool.connection()
app.executor = ThreadPoolExecutor(max_workers=int(app_config["SERVICE"]["workers"]))

# 初始化路由
from User import user_blue
from Task import task_blue

app.register_blueprint(user_blue, url_prefix='/api/user')
app.register_blueprint(task_blue, url_prefix='/api/task')
CORS(app, supports_credentials=True,
     resources={r"/*": {"origins": app_config["BASE"]["web_host"]}})


@app.route('/')
@app.route('/api/')
def hello_world():
    app.logger.info('Trigger "Hello,world!"')
    return "Hello, world!"


@app.errorhandler(400)
def http_forbidden(msg):
    app.logger.warning("{}: <HTTP 400> {}".format(request.url, msg))
    return jsonify({
        "status": "error",
        "message": "请求数据异常，请检查",
    })


@app.errorhandler(500)
def http_forbidden(msg):
    app.logger.warning("{}: <HTTP 400> {}".format(request.url, msg))
    return jsonify({
        "status": "error",
        "message": "服务器状态异常，请联系开发者",
    })


if __name__ == '__main__':
    app.logger.setLevel(logging.DEBUG)
    app.run(host='127.0.0.1', port=12880, debug=True)
    exit()
