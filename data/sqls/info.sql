

DROP TABLE IF EXISTS `asian_quant_stock_info`;
CREATE TABLE `asian_quant_stock_info` (
  `code` varchar(10) NOT NULL COMMENT '股票代码',
  `name` varchar(50) DEFAULT NULL COMMENT '股票简称',
  `industry` varchar(50) DEFAULT NULL COMMENT '所属行业',
  `mcap` decimal(20,4) DEFAULT NULL COMMENT '总市值',
  `ffmc` decimal(20,4) DEFAULT NULL COMMENT '流通市值',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '数据更新时间',
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='A股股票基础信息表';


CREATE TABLE `sw_stock_industry` (
  `stock_code` varchar(10) NOT NULL COMMENT '股票代码',
  `stock_name` varchar(20) DEFAULT NULL COMMENT '股票简称',
  `level1_code` varchar(20) DEFAULT NULL COMMENT '一级行业代码',
  `level1_name` varchar(50) DEFAULT NULL COMMENT '一级行业名称',
  `level1_stock_count` int DEFAULT NULL COMMENT '一级成份个数',
  `level1_pe_static` decimal(10,2) DEFAULT NULL COMMENT '一级静态市盈率',
  `level1_pe_ttm` decimal(10,2) DEFAULT NULL COMMENT '一级TTM市盈率',
  `level1_pb` decimal(10,2) DEFAULT NULL COMMENT '一级市净率',
  `level1_div_yield` decimal(10,2) DEFAULT NULL COMMENT '一级静态股息率',
  `level2_code` varchar(20) DEFAULT NULL COMMENT '二级行业代码',
  `level2_name` varchar(50) DEFAULT NULL COMMENT '二级行业名称',
  `level2_parent_name` varchar(50) DEFAULT NULL COMMENT '二级上级行业名称',
  `level2_stock_count` int DEFAULT NULL COMMENT '二级成份个数',
  `level2_pe_static` decimal(10,2) DEFAULT NULL COMMENT '二级静态市盈率',
  `level2_pe_ttm` decimal(10,2) DEFAULT NULL COMMENT '二级TTM市盈率',
  `level2_pb` decimal(10,2) DEFAULT NULL COMMENT '二级市净率',
  `level2_div_yield` decimal(10,2) DEFAULT NULL COMMENT '二级静态股息率',
  `level3_code` varchar(20) DEFAULT NULL COMMENT '三级行业代码',
  `level3_name` varchar(50) DEFAULT NULL COMMENT '三级行业名称',
  `level3_parent_name` varchar(50) DEFAULT NULL COMMENT '三级上级行业名称',
  `level3_stock_count` int DEFAULT NULL COMMENT '三级成份个数',
  `level3_pe_static` decimal(10,2) DEFAULT NULL COMMENT '三级静态市盈率',
  `level3_pe_ttm` decimal(10,2) DEFAULT NULL COMMENT '三级TTM市盈率',
  `level3_pb` decimal(10,2) DEFAULT NULL COMMENT '三级市净率',
  `level3_div_yield` decimal(10,2) DEFAULT NULL COMMENT '三级静态股息率',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='申万行业三级宽表';


-- ============================================================
-- 龙虎榜详情表
-- 数据来源：akshare → stock_lhb_detail_em
-- 主键说明：同一只股票同一天可能因多个上榜原因出现多行，
--           故以 (code, list_date, list_reason) 三列联合主键去重
-- 单位说明：
--   金额类（净买/买入/卖出/成交）→ 万元，保留 2 位小数
--   市值类（流通市值）           → 亿元，保留 4 位小数
-- ============================================================

CREATE TABLE IF NOT EXISTS `lhb_detail` (
    `id`                    BIGINT        NOT NULL AUTO_INCREMENT   COMMENT '自增主键',
    `code`                  VARCHAR(10)   NOT NULL                  COMMENT '股票/债券代码',
    `name`                  VARCHAR(50)   NOT NULL                  COMMENT '股票名称',
    `list_date`             DATE          NOT NULL                  COMMENT '上榜日期',
    `interpretation`        VARCHAR(100)  DEFAULT NULL              COMMENT '解读（主力行为 + 成功率）',
    `close`                 DECIMAL(12,4) DEFAULT NULL              COMMENT '收盘价(元)',
    `pct_chg`               DECIMAL(10,4) DEFAULT NULL              COMMENT '涨跌幅(%)',

    -- 金额类：单位 万元
    `lhb_net_buy`           DECIMAL(16,2) DEFAULT NULL              COMMENT '龙虎榜净买额(万元)',
    `lhb_buy`               DECIMAL(16,2) DEFAULT NULL              COMMENT '龙虎榜买入额(万元)',
    `lhb_sell`              DECIMAL(16,2) DEFAULT NULL              COMMENT '龙虎榜卖出额(万元)',
    `lhb_amount`            DECIMAL(16,2) DEFAULT NULL              COMMENT '龙虎榜成交额(万元)',
    `market_amount`         DECIMAL(18,2) DEFAULT NULL              COMMENT '市场总成交额(万元)',

    `net_buy_ratio`         DECIMAL(10,6) DEFAULT NULL              COMMENT '净买额占总成交比(%)',
    `amount_ratio`          DECIMAL(10,6) DEFAULT NULL              COMMENT '成交额占总成交比(%)',
    `turnover_rate`         DECIMAL(10,4) DEFAULT NULL              COMMENT '换手率(%)',

    -- 市值类：单位 亿元
    `float_market_cap`      DECIMAL(18,4) DEFAULT NULL              COMMENT '流通市值(亿元)',

    `list_reason`           VARCHAR(200)  NOT NULL DEFAULT ''       COMMENT '上榜原因',
    `after_1d`              DECIMAL(10,4) DEFAULT NULL              COMMENT '上榜后1日涨跌幅(%)',
    `after_2d`              DECIMAL(10,4) DEFAULT NULL              COMMENT '上榜后2日涨跌幅(%)',
    `after_5d`              DECIMAL(10,4) DEFAULT NULL              COMMENT '上榜后5日涨跌幅(%)',
    `after_10d`             DECIMAL(10,4) DEFAULT NULL              COMMENT '上榜后10日涨跌幅(%)',
    `updated_at`            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                          ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_lhb_detail`  (`code`, `list_date`, `list_reason`(150)),
    INDEX `idx_list_date`        (`list_date`),
    INDEX `idx_code`             (`code`),
    INDEX `idx_code_date`        (`code`, `list_date`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='龙虎榜详情表 (akshare stock_lhb_detail_em) | 金额单位:万元 市值单位:亿元';