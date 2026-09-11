#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from strategies import (
    mfa_strategy,
    sqz_strategy,
    utb_strategy,
    low_strategy,
    suf_strategy,
)

STRATEGY_REGISTRY = {
    "mfa": mfa_strategy.run_strategy,
    "sqz": sqz_strategy.run_strategy,
    "utb": utb_strategy.run_strategy,
    "low": low_strategy.run_strategy,
    "suf": suf_strategy.run_strategy,
}

from core.query.conditions import (
    lhb_condition,
    fit_condition
)

CONDITION_REGISTRY = {
    "lhb": lhb_condition,
    "fit": fit_condition
}