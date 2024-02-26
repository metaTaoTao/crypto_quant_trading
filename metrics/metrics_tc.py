# -*- encoding:utf-8 -*-
"""比特币度量模块"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from ..MetricsBu.MetricsFutures import MetricsFutures



class MetricsTC(MetricsFutures):
    """比特币，莱特币等币类型度量，自扩张使用，暂时继承MetricsFutures，即不涉及benchmark，user可继承扩展需求"""
