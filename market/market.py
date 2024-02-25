import os
import datetime

import numpy as np
import pandas as pd
from utils.lazy_util import LazyFunc
class MarketMixin(object):
    """
        市场信息混入类，被混入类需要设置self.symbol_name，
        通过code_to_symbol将symbol转换为Symbol对象, 通过Symbol对象
        查询market和sub_market
    """

    @LazyFunc
    def _symbol(self):
        """通过code_to_symbol将symbol转换为Symbol对象 LazyFunc"""
        if not hasattr(self, 'symbol_name'):
            # 被混入类需要设置self.symbol_name
            raise NameError('must name symbol_name!!')
        # 通过code_to_symbol将symbol转换为Symbol对象
        return self.symbol_name

    @LazyFunc
    def symbol_market(self):
        """查询self.symbol_name的市场类型 LazyFunc"""
        return self._symbol.market

    @LazyFunc
    def symbol_sub_market(self):
        """查询self.symbol_name的子市场类型，即交易所信息 LazyFunc"""
        return self._symbol.sub_market