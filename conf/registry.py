#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from strategies import (
    mix_strategy,
    suf_strategy,
    mfa_strategy,
    utb_strategy,
    tma_strategy,
    sqz_strategy,
    low_strategy
)

STRATEGY_REGISTRY = {
    "mix": mix_strategy.run_strategy,
    "suf": suf_strategy.run_strategy,
    "mfa": mfa_strategy.run_strategy,
    "utb": utb_strategy.run_strategy,
    "tma": tma_strategy.run_strategy,
    "sqz": sqz_strategy.run_strategy,
    "low": low_strategy.run_strategy
}

from core.query.conditions import (
    lhb_condition,
    fit_condition
)

CONDITION_REGISTRY = {
    "lhb": lhb_condition,
    "fit": fit_condition
}