import yfinance as yf


def get_stock_data(ticker: str):
    """
    获取股票的实时数据。
    ticker: 股票代码，例如 'AAPL' (苹果), 'TSLA' (特斯拉), '600519.SS' (贵州茅台), '00700.HK' (腾讯)
    """
    try:
        # 创建股票对象
        stock = yf.Ticker(ticker)

        # 获取基本信息 (info 字典可能很大，我们只取关键的)
        info = stock.info

        # 容错处理：有时候 info 为空
        if not info:
            return f"未找到代码为 {ticker} 的股票信息，请检查代码格式（如A股需加后缀.SS或.SZ）。"

        current_price = info.get('currentPrice', info.get('regularMarketPrice', '未知'))
        market_cap = info.get('marketCap', '未知')
        pe_ratio = info.get('trailingPE', '未知')
        currency = info.get('currency', 'USD')
        name = info.get('longName', ticker)

        # 简单换算一下市值单位
        if isinstance(market_cap, (int, float)):
            market_cap = f"{market_cap / 100000000:.2f}亿"

        return (f"【股票名称】：{name}\n"
                f"【当前价格】：{current_price} {currency}\n"
                f"【市值】：{market_cap}\n"
                f"【市盈率(PE)】：{pe_ratio}\n"
                f"【52周最高/最低】：{info.get('fiftyTwoWeekHigh')} / {info.get('fiftyTwoWeekLow')}")

    except Exception as e:
        return f"获取股票数据失败: {str(e)}"


# 单元测试
if __name__ == "__main__":
    print(get_stock_data("AAPL"))  # 美股
    print(get_stock_data("600519.SS"))  # A股