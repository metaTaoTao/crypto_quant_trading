# coding=utf-8
"""
    内置数据源示例实现模块：

    所有数据接口仅供学习使用，以及最基本使用测试，如需进一步使用，请购买数据
"""
import os

import random
import math
import sqlite3 as sqlite

import pandas as pd

from core.env import EMarketTargetType, EMarketSubType
from core import env
from market import network
from market.data_base import StockBaseMarket, SupportMixin, FuturesBaseMarket, TCBaseMarket
from market.data_parser import BDParser, TXParser, NTParser, SNUSParser, YahooParser
from market.data_parser import SNFuturesParser, SNFuturesGBParser, HBTCParser
from utils import str_util, date_util, md5
from utils.dt_util import catch_error

"""网络请求（连接10秒，接收60秒）超时时间"""
K_TIME_OUT = (10, 60)


def random_from_list(array):
    """从参数array中随机取一个元素"""
    # 在array长度短的情况下，测试比np.random.choice效率要高
    return array[random.randrange(0, len(array))]


@catch_error(return_val=None, log=False)
def query_symbol_from_pinyin(pinyin):
    """通过拼音对symbol进行模糊查询"""
    path = TXApi.K_SYMBOLS_DB
    conn = sqlite.connect(path)
    cur = conn.cursor()
    pinyin = pinyin.lower()
    query = "select stockCode from {} where pinyin=\'{}\'".format(TXApi.K_DB_TABLE_NAME, pinyin)
    cur.execute(query)
    results = cur.fetchall()
    conn.close()
    if len(results) > 0:
        code = results[0][0]
        # 查询到的stcok code eg：sh111111，usabcd.n
        start = 2
        end = len(code)
        if '.' in code:
            # 如果是美股要截取.
            end = code.find('.')
        return code[start:end]

class YahooApi(StockBaseMarket, SupportMixin):
    """Yahoo Data Sources"""
    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(YahooApi, self).__init__(symbol)
        self._action_id = int(date_util.time_seconds())
        self._version2_log_cnt = 0
        self.data_parser_cls = YahooParser

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        import yfinance as yf
        df = yf.download(self._symbol.symbol_code, start=start, end=end, interval='1d')
        kl_df = self.data_parser_cls.parse(df)
        return StockBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)

    def minute(self, n_folds=5, *args, **kwargs):
        self._version2_log_cnt += 1
        cuid = str_util.create_random_with_num_low(40)
        log_id = self._action_id + self._version2_log_cnt * 66
        device = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        url = BDApi.MINUTE_NET_5D % (cuid, device, str(log_id), str(self._action_id), self._symbol.value)

        return network.get(url=url, timeout=K_TIME_OUT).json()
class BDApi(StockBaseMarket, SupportMixin):
    """bd数据源，支持港股，美股，a股"""

    K_NET_CONNECT_START = '&start='
    K_NET_DAY = 'http://gp.baidu.com:80/stocks/stockkline?from=android&os_ver=21&format=json&vv=3.3.0' \
                '&uid=&BDUSS=&cuid=%s&channel=default_channel&device=%s&logid=%s&actionid=%s&device_net_type' \
                '=wifi&period=day&stock_code=%s&fq_type=front'

    MINUTE_NET_5D = 'http://gp.baidu.com:80/stocks/stocktimelinefive?from=android&os_ver=21&format=json' \
                    '&vv=3.3&uid=&BDUSS=&cuid=%s&channel=default_channel&device=%s&logid=%s&actionid=%s' \
                    '&device_net_type=wifi&stock_code=%s&step=10'

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(BDApi, self).__init__(symbol)
        self._action_id = int(date_util.time_seconds())
        self._version2_log_cnt = 0
        self.data_parser_cls = BDParser

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        self._version2_log_cnt += 1
        log_id = self._action_id + self._version2_log_cnt * 66
        cuid = str_util.create_random_with_num_low(40)
        device = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        url = BDApi.K_NET_DAY % (cuid, device, str(log_id), str(self._action_id), self._symbol.value)
        # logging.info(url)
        next_start = None
        kl_df = None
        if start:
            # 需重新计算n_fold
            days = date_util.diff(start, date_util.current_str_date(), check_order=False)
            # 每次返回300条数据
            n_folds = int(days / 300.0)

        for _ in range(0, n_folds):
            if next_start:
                url = url + BDApi.K_NET_CONNECT_START + str(next_start)
            # logging.info(url)
            data = network.get(url=url, timeout=K_TIME_OUT)
            temp_df = None
            if data is not None:
                temp_df = self.data_parser_cls(self._symbol, data.json()).df

            if temp_df is not None:
                next_start = int(temp_df.loc[temp_df.index[0], ['date']].values[0])
            kl_df = temp_df if kl_df is None else pd.concat([temp_df, kl_df])
            # 因为是从前向后请求，且与时间无关，所以可以直接在for里面中断
            if kl_df is None:
                return None

            """由于每次放回300条>1年的数据，所以超出总数就不再请求下一组"""
            if kl_df.shape[0] > env.g_market_trade_year * n_folds:
                break

        return StockBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)

    def minute(self, n_folds=5, *args, **kwargs):
        self._version2_log_cnt += 1
        cuid = str_util.create_random_with_num_low(40)
        log_id = self._action_id + self._version2_log_cnt * 66
        device = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        url = BDApi.MINUTE_NET_5D % (cuid, device, str(log_id), str(self._action_id), self._symbol.value)

        return network.get(url=url, timeout=K_TIME_OUT).json()


class TXApi(StockBaseMarket, SupportMixin):
    """tx数据源，支持港股，美股，a股"""

    K_NET_BASE = "http://ifzq.gtimg.cn/appstock/app/%sfqkline/get?p=1&param=%s,day,,,%d," \
                 "qfq&_appName=android&_dev=%s&_devId=%s&_mid=%s&_md5mid=%s&_appver=4.2.2&_ifChId=303&_screenW=%d" \
                 "&_screenH=%d&_osVer=%s&_uin=10000&_wxuin=20000&__random_suffix=%d"

    K_NET_HK_MNY = 'http://proxy.finance.qq.com/ifzqgtimg/stock/corp/hkmoney/sumary?' \
                   'symbol=%s&type=sum&jianjie=1&_appName=android' \
                   '&_dev=%s&_devId=%s&_mid=%s&_md5mid=%s&_appver=5.5.0&_ifChId=277' \
                   '&_screenW=%d&_screenH=%d&_osVer=%s&_uin=10000&_wxuin=20000&_net=WIFI&__random_suffix=%d'

    K_DB_TABLE_NAME = "values_table"
    K_DB_TABLE_SN = "stockCode"
    p_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))
    K_SYMBOLS_DB = os.path.join(p_dir, 'RomDat/symbols_db.db')

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(TXApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = TXParser

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        cuid = str_util.create_random_with_num_low(40)
        cuid_md5 = md5.md5_from_binary(cuid)
        random_suffix = str_util.create_random_with_num(5)
        dev_mod = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        os_ver = random_from_list(StockBaseMarket.K_OS_VERSION_LIST)
        screen = random_from_list(StockBaseMarket.K_PHONE_SCREEN)

        days = env.g_market_trade_year * n_folds + 1
        # start 不为空时计算 获取天数，获取的数据肯定比预期的数据多，因为同一时间内，交易日的天数一定不比实际的天数多
        if start:
            temp_end = date_util.current_str_date()
            days = date_util.diff(start, temp_end, check_order=False)

        sub_market = None
        if self._symbol.market == EMarketTargetType.E_MARKET_TARGET_US:
            # sub_market = self.query_symbol_sub_market(self._symbol.value)
            market = self._symbol.market.value
            if '.' in self._symbol.value:
                # 如果已经有.了说明是大盘，大盘不需要子市场，eg：us.IXIC
                sub_market = ''
            else:
                # 这里tx的source不支持US_PINK, US_OTC, US_PREIPO
                sub_market_map = {EMarketSubType.US_N.value: 'n',

                                  EMarketSubType.US_PINK.value: 'n',
                                  EMarketSubType.US_OTC.value: 'n',
                                  EMarketSubType.US_PREIPO.value: 'n',
                                  EMarketSubType.US_AMEX.value: 'n',

                                  EMarketSubType.US_OQ.value: 'oq'}
                sub_market = '.{}'.format(sub_market_map[self._symbol.sub_market.value])
            url = TXApi.K_NET_BASE % (
                market, self._symbol.value + sub_market, days,
                dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver, int(random_suffix, 10))
        elif self._symbol.market == EMarketTargetType.E_MARKET_TARGET_HK:
            market = self._symbol.market.value
            url = TXApi.K_NET_BASE % (
                market, self._symbol.value, days,
                dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver, int(random_suffix, 10))
        else:
            market = ''
            url = TXApi.K_NET_BASE % (
                market, self._symbol.value, days,
                dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver, int(random_suffix, 10))

        data = network.get(url, timeout=K_TIME_OUT)
        if data is not None:
            kl_pd = self.data_parser_cls(self._symbol, sub_market, data.json()).df
        else:
            return None

        return StockBaseMarket._fix_kline_pd(kl_pd, n_folds, start, end)

    def hkmoney(self):
        """港股概要信息接口"""
        if self._symbol.market != EMarketTargetType.E_MARKET_TARGET_HK:
            raise TypeError('hkmoney only support hk!!')

        cuid = str_util.create_random_with_num_low(40)
        cuid_md5 = md5.md5_from_binary(cuid)
        random_suffix = str_util.create_random_with_num(5)
        dev_mod = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        os_ver = random_from_list(StockBaseMarket.K_OS_VERSION_LIST)
        screen = random_from_list(StockBaseMarket.K_PHONE_SCREEN)

        url = TXApi.K_NET_HK_MNY % (self._symbol.value, dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver,
                                    int(random_suffix, 10))
        return network.get(url, timeout=K_TIME_OUT)

    def minute(self, n_fold=5, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('TXApi minute NotImplementedError!')


class NTApi(StockBaseMarket, SupportMixin):
    """nt数据源，支持港股，美股，a股"""

    K_NET_BASE = "http://img1.money.126.net/data/%s/kline/day/history/%d/%s.json"

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(NTApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = NTParser

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        kl_df = None
        if start is None or end is None:
            end_year = int(date_util.current_str_date()[:4])
            start_year = end_year - n_folds + 1
        else:
            start_year = int(start[:4])
            end_year = int(end[:4])
        req_year = list(range(start_year, end_year + 1))

        if self._symbol.market == EMarketTargetType.E_MARKET_TARGET_US:
            market = self._symbol.market.value
            symbol = self._symbol.symbol_code.upper()
            if self._symbol.is_us_index():
                # ntes 需要做映射匹配大盘symbol
                index_dict = {'.DJI': 'DOWJONES', '.IXIC': 'NASDAQ', '.INX': 'SP500'}
                symbol = index_dict[symbol]
        elif self._symbol.market == EMarketTargetType.E_MARKET_TARGET_HK:
            market = self._symbol.market.value
            symbol = self._symbol.symbol_code.upper()
        elif self._symbol.market == EMarketTargetType.E_MARKET_TARGET_CN:
            market = self._symbol.market.value
            symbol = self._symbol.symbol_code
            if self._symbol.is_sz_stock():
                symbol = '1{}'.format(symbol)
            else:
                symbol = '0{}'.format(symbol)
        else:
            raise TypeError('NTApi dt support {}'.format(self._symbol.market))

        for year in req_year:
            url = NTApi.K_NET_BASE % (market, year, symbol)
            data = network.get(url=url, retry=1, timeout=K_TIME_OUT)
            temp_df = None
            if data is not None:
                temp_df = self.data_parser_cls(self._symbol, data.json()).df
            if temp_df is not None:
                kl_df = temp_df if kl_df is None else kl_df.append(temp_df)
        if kl_df is None:
            return None
        return StockBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)

    def minute(self, n_fold=5, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('NTApi minute NotImplementedError!')


class SNUSApi(StockBaseMarket, SupportMixin):
    """snus数据源，支持美股"""
    K_NET_BASE = "http://stock.finance.sina.com.cn/usstock/api/json_v2.php/US_MinKService.getDailyK?" \
                 "symbol=%s&___qn=3n"

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(SNUSApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = SNUSParser

    def _support_market(self):
        """声明数据源支持美股"""
        return [EMarketTargetType.E_MARKET_TARGET_US]

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        url = SNUSApi.K_NET_BASE % self._symbol.symbol_code
        data = network.get(url=url, timeout=K_TIME_OUT).json()
        kl_df = self.data_parser_cls(self._symbol, data).df
        if kl_df is None:
            return None
        return StockBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)

    def minute(self, n_fold=5, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('SNUSApi minute NotImplementedError!')


class SNFuturesApi(FuturesBaseMarket, SupportMixin):
    """sn futures数据源，支持国内期货"""

    K_NET_BASE = "http://stock.finance.sina.com.cn/futures/api/json_v2.php/" \
                 "IndexService.getInnerFuturesDailyKLine?symbol=%s"

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(SNFuturesApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = SNFuturesParser

    def _support_market(self):
        """声明数据源支持期货数据"""
        return [EMarketTargetType.E_MARKET_TARGET_FUTURES_CN]

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        url = SNFuturesApi.K_NET_BASE % self._symbol.symbol_code
        data = network.get(url=url, timeout=K_TIME_OUT).json()
        kl_df = self.data_parser_cls(self._symbol, data).df
        if kl_df is None:
            return None
        return FuturesBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)


class SNFuturesGBApi(FuturesBaseMarket, SupportMixin):
    """sn futures数据源，支持国际期货"""

    K_NET_BASE = "http://stock2.finance.sina.com.cn/futures/api/jsonp.php/" \
                 "var %s%s=/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=%s&_=%s"

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(SNFuturesGBApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = SNFuturesGBParser

    def _support_market(self):
        """声明数据源支持期货数据, 支持国际期货市场"""
        return [EMarketTargetType.E_MARKET_TARGET_FUTURES_GLOBAL]

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        today = date_util.current_str_date().replace('-', '_')
        url = SNFuturesGBApi.K_NET_BASE % (self._symbol.symbol_code, today, self._symbol.symbol_code, today)
        data = network.get(url=url, timeout=(10, 60))
        text = data.text
        # 返回的是Javascript字符串解析出dict
        js_dict = network.parse_js(text[text.find('=(') + 2:text.rfind(')')])
        kl_df = self.data_parser_cls(self._symbol, js_dict).df
        if kl_df is None:
            return None
        return FuturesBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)


class HBApi(TCBaseMarket, SupportMixin):
    """hb数据源，支持币类，比特币，莱特币"""

    K_NET_BASE = 'https://www.huobi.com/qt/staticmarket/%s_kline_100_json.js?length=%d'

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(HBApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = HBTCParser

    def _support_market(self):
        """只支持币类市场"""
        return [EMarketTargetType.E_MARKET_TARGET_TC]

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        req_cnt = n_folds * env.g_market_trade_year
        if start is not None and end is not None:
            # 向上取整数，下面使用_fix_kline_pd再次进行剪裁, 要使用current_str_date不能是end
            folds = math.ceil(date_util.diff(date_util.date_str_to_int(start),
                                               date_util.current_str_date()) / 365)
            req_cnt = folds * env.g_market_trade_year

        url = HBApi.K_NET_BASE % (self._symbol.symbol_code, req_cnt)
        data = network.get(url=url, timeout=K_TIME_OUT).json()
        kl_df = self.data_parser_cls(self._symbol, data).df
        if kl_df is None:
            return None
        return TCBaseMarket._fix_kline_pd(kl_df, n_folds, start, end)

    def minute(self, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('HBApi minute NotImplementedError!')
