#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 上一日：龙虎榜
lhb_condition = """
    SELECT 
        DISTINCT code
    FROM 
        lhb_detail
    WHERE 
        list_date = :last_date
    """

# 上一日：标的筛选
fit_condition = """
    CALL filter_stocks(
        -- 交易日期
        :last_date,

        -- 涨跌幅范围
        -20, 20,

        -- 自由流通市值范围（单位：元）
        50e8, 800e8,

        -- 成交量 > 前N日均值×M倍（N=0 不过滤）
        0, 0,

        -- 成交量 < 前N日均值×M倍（N=0 不过滤）
        0, 0,

        -- 股票信息行业白名单
        '',

        -- 股票信息行业黑名单
        '',

        -- 申万一级行业白名单
        '',

        -- 申万一级行业黑名单
        '',

        -- 申万二级行业白名单
        '',

        -- 申万二级行业黑名单
        '',

        -- 申万三级行业白名单
        '',

        -- 申万三级行业黑名单
        ''
    )
"""