DROP PROCEDURE IF EXISTS `filter_stocks`;

CREATE DEFINER=`root`@`localhost` PROCEDURE `filter_stocks`(
    IN p_date VARCHAR(10),
    IN p_pct_chg_min DECIMAL(10,2),
    IN p_pct_chg_max DECIMAL(10,2),
    IN p_ffmc_min BIGINT,
    IN p_ffmc_max BIGINT,

    -- 成交量 > 前N日均值×M倍（N=0 不过滤）
    IN p_volume_gt_days INT,
    IN p_volume_gt_mult DECIMAL(10,2),

    -- 成交量 < 前N日均值×M倍（N=0 不过滤）
    IN p_volume_lt_days INT,
    IN p_volume_lt_mult DECIMAL(10,2),

    IN p_industry_include TEXT,
    IN p_industry_exclude TEXT,
    IN p_level1_include TEXT,
    IN p_level1_exclude TEXT,
    IN p_level2_include TEXT,
    IN p_level2_exclude TEXT,
    IN p_level3_include TEXT,
    IN p_level3_exclude TEXT
)
BEGIN
    SELECT
        sd.`code`,
        si.industry
    FROM
        asian_quant_stock_daily sd
    INNER JOIN asian_quant_stock_info si
        ON si.`code` = sd.`code`
    INNER JOIN sw_stock_industry ind
        ON ind.stock_code = sd.`code`
    WHERE
        sd.`date` = p_date
        AND sd.adjust = 'qfq'
        AND sd.pct_chg BETWEEN p_pct_chg_min AND p_pct_chg_max
        AND si.ffmc BETWEEN p_ffmc_min AND p_ffmc_max

        -- 成交量 > 前N日均值 × M倍（N=0 跳过）
        AND (
            p_volume_gt_days = 0
            OR sd.volume > p_volume_gt_mult * (
                SELECT AVG(d.volume)
                FROM (
                    SELECT volume
                    FROM asian_quant_stock_daily d2
                    WHERE d2.code = sd.code
                      AND d2.adjust = 'qfq'
                      AND d2.date < p_date
                    ORDER BY d2.date DESC
                    LIMIT p_volume_gt_days
                ) d
            )
        )

        -- 成交量 < 前N日均值 × M倍（N=0 跳过）
        AND (
            p_volume_lt_days = 0
            OR sd.volume < p_volume_lt_mult * (
                SELECT AVG(d.volume)
                FROM (
                    SELECT volume
                    FROM asian_quant_stock_daily d2
                    WHERE d2.code = sd.code
                      AND d2.adjust = 'qfq'
                      AND d2.date < p_date
                    ORDER BY d2.date DESC
                    LIMIT p_volume_lt_days
                ) d
            )
        )

        -- 行业筛选
        AND (p_industry_include = '' OR FIND_IN_SET(si.industry COLLATE utf8mb4_unicode_ci, p_industry_include COLLATE utf8mb4_unicode_ci))
        AND (p_industry_exclude = '' OR NOT FIND_IN_SET(si.industry COLLATE utf8mb4_unicode_ci, p_industry_exclude COLLATE utf8mb4_unicode_ci))

        AND (p_level1_include = '' OR FIND_IN_SET(ind.level1_name COLLATE utf8mb4_unicode_ci, p_level1_include COLLATE utf8mb4_unicode_ci))
        AND (p_level1_exclude = '' OR NOT FIND_IN_SET(ind.level1_name COLLATE utf8mb4_unicode_ci, p_level1_exclude COLLATE utf8mb4_unicode_ci))

        AND (p_level2_include = '' OR FIND_IN_SET(ind.level2_name COLLATE utf8mb4_unicode_ci, p_level2_include COLLATE utf8mb4_unicode_ci))
        AND (p_level2_exclude = '' OR NOT FIND_IN_SET(ind.level2_name COLLATE utf8mb4_unicode_ci, p_level2_exclude COLLATE utf8mb4_unicode_ci))

        AND (p_level3_include = '' OR FIND_IN_SET(ind.level3_name COLLATE utf8mb4_unicode_ci, p_level3_include COLLATE utf8mb4_unicode_ci))
        AND (p_level3_exclude = '' OR NOT FIND_IN_SET(ind.level3_name COLLATE utf8mb4_unicode_ci, p_level3_exclude COLLATE utf8mb4_unicode_ci));
END