# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 1. 选择策略
# ============================================================
STRATEGY_CONFIG = {
    # ############# CN #############
    # 策略配置: ["mfa", "sqz", "low"],
    "CN_RUN_STRATEGIES": ["mfa", "sqz"],
    # 上一日满足的条件标的: lhb, fit
    "CN_LAST_DAY_CONDITION_CODES": 'fit',
    # True: 开启实时快照数据
    "CN_USE_REAL_TIME_DATA": True,
    # A股扫描周期配置 "daily" | "weekly" | "monthly"
    "CN_INTERVAL": "daily",
    # 历史时段: "2026-02-04 ~ 2026-02-04"
    "CN_HISTORY_DAYS": "2026-05-01 ~ 2026-05-10",
    # 测试标的
    "CN_TEST_CODE": [],

    # ############# CO 调度配置 #############
    # OKX, Binance
    "CO_EXCHANGE": "B",
    # 周期 5m, 1h, 4h, 1d, 1w
    "CO_INTERVAL": "1d",
    # 结束时间
    "CO_END_DAY": "2026-06-19",
    # 从池子里随机取 N 只，None = 不限制
    "CO_TOP_N": None,
    # 排序规则：volume (成交额) 或 change (涨跌幅绝对值)
    "CO_RANK_BY": "volume",
    # k线数量
    "CO_KLINE_LIMIT": 300,
    # 多进程并发控制
    "CO_MAX_WORKERS": 5,
    # 测试标的
    "CO_MANUAL_LIST": [],

    # ############# US/HK 核心调度配置 #############
    # 可选值: stocks (美股), rwa (实物资产), contract (合约), hk (港股)
    "UH_CACHE_PATH": "hk",
    "UH_END_DAY": "2026-05-31",
    # K线周期: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
    "UH_INTERVAL": "1d",

    # ── 矩阵式多维度流控清洗字典 ──────────────────────────────────────────
    "MARKET_POOL_FILTERS": {

        "stocks": {
            "valid_mics": ["XNYS", "XNAS", "XASE"],
            "valid_types": ["Common Stock 普通股"],
            "exclude_keywords": ["ETF", "WARRANT"],
            "check_mic_and_type": True,
        },

        "rwa": {
            "exclude_keywords": [],
            "check_mic_and_type": False,
        },

        "contract": {
            "exclude_keywords": [],
            "check_mic_and_type": False,
        },

        "hk": {
            "valid_sub_types": [
                "Equity Securities (Main Board) 主板股票",
                "Exchange Traded Funds 交易所买卖基金",
                "Real Estate Investment Trusts 房地产信托REITs"
            ],
            "exclude_keywords": ["-R"],
            "check_mic_and_type": True,
        }
    }
}

# ============================================================
# 2. 系统性能与运行控制配
# ============================================================
SYSTEM_CONFIG = {
    # 数据源开关
    "ENABLE_RESULT_ENRICHMENT": True,       # True: 导出结果时注入映射信息（名称、市值等）版本V2
    "ENABLE_RESULT_FUTURE": True,           # True: 导出结果时当前日期未来累积涨幅
    "ENABLE_RESULT_MYSQL": True,            # True: 导出MYSQL
    "ENABLE_EXPORT": True,                  # True: 导出CSV
    "ENABLE_TELEGRAM": True,                # True: 导出Telegram
    "FUTURE_DAYS_LIST": list(range(1, 31)), # 需要的当前日期未来日期天数列表
    "ANCHOR_DATE": '2025-04-09',            # 加权平均anchor锚定日期：关税日
    "TRADABLE_MARKET_VALUE": 0,             # 过滤流动市值大小：亿

    # 分批逻辑控制
    "SAMPLE_SIZE": 0,                       # 抽样数量：0表示全量扫描；非0用于开发调试
    "BATCH_SIZE": 5000,                     # 每处理 5000 只股票
    "BATCH_INTERVAL_SEC": 0,                # 批次之间的强制休息时间

    # 通知开关 notify 模块
    "ENABLE_EMAIL": False,                  # 导出后是否发送邮件通知
    "EXPORT_ENCODING": "utf-8-sig",         # CSV导出编码。sig确保 Excel 打开中文不乱码

    # 多进程并发控制
    "MAX_WORKERS": 8,                       # 建议设为 0：自动识别 CPU 核心数
    "REQUEST_TIMEOUT": 30,                  # 网络/数据库请求超时时间(秒)

    # MySQL数据库连接池配置
    "DB_POOL_SIZE": 15,                     # 每个子进程会维持最多 15 个 "长连接"
    "DB_MAX_OVERFLOW": 25,                  # 当 15 个连接都被占满时，允许额外临时创建 25 个连接
    "DB_POOL_RECYCLE": 3600                 # 每小时强制重连
}

# ============================================================
# 3. 市场过滤与基础行为配置
# ============================================================
INDICATOR_CONFIG = {
    "DAYS": 500,                            # 扫描回溯天数。计算MA200或长周期指标必须有足够数据
    "ADJUST": "qfq",                        # 复权方式: qfq(前复权), hfq(后复权), None(不复权)。A股必选qfq

    # 市场排除开关
    "EXCLUDE": {
        "EXCLUDE_GEM": False,               # 排除创业板（300、301开头）
        "EXCLUDE_KCB": True,                # 排除科创板（688、689开头）
        "EXCLUDE_BJ": True,                 # 排除北交所（8、4、92开头）
        "EXCLUDE_ST": True,                 # 是否排除 ST/退市风险警示股
    }
}

# ============================================================
# 4. 文件系统与持久化路径
# ============================================================
PATH_CONFIG = {
    "CACHE_FILE": os.path.join(BASE_DIR, "data/cache", "cn_stocks_cache.json"),
    "OUTPUT_FOLDER_BASE": os.path.join(BASE_DIR, "data/symbols"),    # 存放生成的信号CSV
    "OUTPUT_LOG": os.path.join(BASE_DIR, "data/logs")               # 存放运行日志
}

# 初始化：确保必要的物理文件夹存在
for path in [PATH_CONFIG["OUTPUT_FOLDER_BASE"], PATH_CONFIG["OUTPUT_LOG"]]:
    if not os.path.exists(path):
        os.makedirs(path)

# ============================================================
# 5. 数据库连接配置 (MySQL)
# ============================================================
"""
    1. 服务的开启、关闭与重启
    启动	    brew services start mysql	    后台常驻运行，开机自启动
    停止	    brew services stop mysql	    正常关闭服务
    重启	    brew services restart mysql	    修改配置文件后必用
    查看状态	brew services list	            查看 MySQL 是否正在运行

    2. 数据库登录与退出
    本地登录	mysql -u root -p	            常用登录方式，回车后输入密码
    TCP登录	mysql -h 127.0.0.1 -u root -p	强制走网络协议（跳过 Socket 错误）

    3. 排查故障常用命令
    查看实时日志           tail -f /usr/local/var/mysql/beluga.err
    检查进程是否存在        ps -ef | grep mysqld
    查看端口占用           lsof -i :3306
    寻找配置文件位置        ls /usr/local/etc/my.cnf
    查看配置文件加载顺序     mysql --help | grep "my.cnf"

    4. 内部配置与密码管理
    修改密码(9.x 版本)     ALTER USER 'root'@'localhost' IDENTIFIED BY '你的新密码';
    查看当前密码策略        SHOW VARIABLES LIKE 'validate_password%';
    查看Binlog状态         SHOW VARIABLES LIKE 'log_bin';
    查看当前所有用户        SELECT user, host, plugin FROM mysql.user;

    5. 权限与文件管理
    修复权限               sudo chown -R $(whoami) /usr/local/var/mysql
    备份数据库             mysqldump -u root -p --all-databases > backup.sql
"""
DB_CONFIG = {
    "HOST": "localhost",                                # 数据库地址
    "PORT": 3306,                                       # 端口，默认3306
    "USER": "xxx",                                     # 用户名
    "PASS": "xxx",                                   # 密码
    "DB_NAME": "xxx",                                 # 数据库名称
    "CHARSET": "utf8mb4"                                # 使用 utf8mb4 兼容性更好
}

# 涉及的表名
TABLE_CONFIG = {
    "QUERY_DAILY_TABLE": "asian_quant_stock_daily",     # 查询股票日表
    "QUERY_WEEKLY_TABLE": "asian_quant_stock_weekly",   # 查询股票日表
    "INSERT_DAILY_TABLE": "asian_quant_stock_daily",    # 更新股票日表
    "QUERY_STOCK_INFO": "asian_quant_stock_info",       # 更新股票信息表
}

# ============================================================
# 6. 通知渠道配置（Email / Telegram）
# ============================================================
# Email 配置
EMAIL_CONFIG = {
    "SMTP_HOST": "xxx.xxx.com",                         # SMTP 服务器地址（例如：smtp.qq.com / smtp.163.com / smtp.gmail.com）
    "SMTP_PORT": 465,                                   # SSL 常用端口 465；若使用 STARTTLS 通常为 587
    "USE_SSL": True,                                    # True 走 SMTP SSL；False 走明文 + STARTTLS（根据服务商选择）
    "USERNAME": "xxx@qq.com",                    # 发件邮箱账号
    "PASSWORD": "xxx",                     # 发件邮箱授权码/密码（注意保密）
    "FROM": "xxx@qq.com",                        # 发件人（通常和 USERNAME 相同）
    "TO": ["xxx@qq.com"]                         # 收件人列表
}

# Telegram Bot 配置
TELEGRAM_CONFIG = {
    "TG_TOKEN": "xxx",    # 机器人 Token
    "TG_CHAT_ID": "xxx",                                  # 目标 chat_id（用户/群）
    "DISABLE_WEB_PAGE_PREVIEW": True
}

# 企业微信 Bot 配置
WECOM_CONFIG = {
    "WECOM_WEBHOOK": "xxx"
}

# TWELVEDATA 配置
TWELVE_DATA_CONFIG = {
    "TWELVE_DATA_URL": "xxx",
    "TWELVE_DATA_KEY": "xxx"
}

# 加密Key
ENCRYPTION_KEY = 'xxx'

# Git
GITHUB_CONFIG = {
    "TOKEN": "xxx"
}

# Finnhub
FINNHUB_CONFIG = {
    "TOKEN": "xxx"
}

# HKEX
HKEX_URL = "xxx"