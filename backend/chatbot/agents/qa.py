"""
General Q&A Agent — answers finance questions.
Uses ChromaDB for memory + Gemini LLM with fallback to structured FAQ responses.
"""
import os
import logging
from ..tools import get_live_stock_price, get_market_news_summary, extract_stock_symbol

logger = logging.getLogger(__name__)

FINANCE_KNOWLEDGE = {
    'pe ratio': (
        "📊 **P/E Ratio (Price-to-Earnings)**\n\n"
        "Shows how much you pay for ₹1 of a company's earnings.\n"
        "• **High P/E (>30):** Investors expect high growth, or the stock may be overvalued.\n"
        "• **Low P/E (<15):** Could be undervalued or a mature, slow-growth company.\n"
        "• Rule of thumb: Compare P/E within the same sector.\n\n"
        "💡 *Tip: A P/E of 20-25 is considered fair for most Indian large-caps.*"
    ),
    'rsi': (
        "📉 **RSI — Relative Strength Index**\n\n"
        "A momentum indicator measuring speed of price movements (0–100 scale).\n"
        "• **RSI < 30:** Oversold — potential buying opportunity 🛒\n"
        "• **RSI > 70:** Overbought — possible correction coming ⚠️\n"
        "• **RSI 40–60:** Neutral zone\n\n"
        "💡 *Best used alongside price charts, not in isolation.*"
    ),
    'moving average': (
        "📈 **Moving Averages (MA)**\n\n"
        "Smooths price data to identify trend direction.\n"
        "• **MA20:** 20-day average — short-term trend\n"
        "• **MA50:** 50-day average — medium-term trend\n"
        "• Price above MA20 → **Bullish signal** 🚀\n"
        "• Price below MA20 → **Bearish signal** 📉\n\n"
        "💡 *A 'golden cross' (MA50 crosses above MA200) is a strong buy signal.*"
    ),
    'gold': (
        "🥇 **Gold Market**\n\n"
        "Gold is the ultimate safe-haven asset:\n"
        "• Rises during inflation, geopolitical uncertainty, or weak USD\n"
        "• Current spot: ~$3,000/oz (MCX: ~₹87,000/10g)\n"
        "• Ideal portfolio allocation: 5–10%\n"
        "• Track it on Zeus's **Metals** page with RSI & MA20 charts.\n\n"
        "💡 *Gold doesn't pay dividends but protects purchasing power.*"
    ),
    'silver': (
        "🥈 **Silver Market**\n\n"
        "Silver has dual demand — investment + industrial use.\n"
        "• ~70% of demand comes from industry (EVs, solar panels)\n"
        "• Current spot: ~$33/oz (MCX: ~₹95,000/kg)\n"
        "• More volatile than gold — higher risk, higher reward\n\n"
        "💡 *Silver often outperforms gold in bull markets.*"
    ),
    'mutual fund': (
        "📦 **Mutual Funds**\n\n"
        "Pooled investment vehicles managed by fund managers.\n"
        "• **Equity funds:** Higher return, higher risk (5+ year horizon)\n"
        "• **Debt funds:** Stable returns, lower risk\n"
        "• **Index funds:** Low-cost, market-matching returns\n"
        "• **SIP:** Invest small amounts monthly — rupee-cost averaging\n\n"
        "💡 *Index funds with expense ratio < 0.5% beat most active funds long-term.*"
    ),
    'nifty': (
        "📊 **Nifty 50**\n\n"
        "India's benchmark stock index — tracks 50 largest NSE-listed companies.\n"
        "• Represents ~13 sectors and ~65% of NSE's market cap\n"
        "• Used to gauge overall Indian market health\n"
        "• If Nifty is green → broad market is up; if red → market is down\n\n"
        "💡 *Investing in a Nifty 50 index fund gives instant diversification.*"
    ),
}


def _llm_answer(query: str, api_key: str, context: str = '') -> str | None:
    try:
        from langchain_groq import ChatGroq
        from langchain.prompts import ChatPromptTemplate

        llm = ChatGroq(model='llama-3.3-70b-versatile', api_key=api_key, temperature=0.5)
        prompt = ChatPromptTemplate.from_messages([
            ('system', (
                "You are Zeus, an expert financial assistant for Indian and global markets. "
                "Answer concisely in under 200 words. Use emojis for readability. "
                "Specialise in: stocks, mutual funds, gold/silver, market analysis. "
                "If out of scope, redirect to finance topics politely.\n\n"
                "Additional context:\n{context}"
            )),
            ('human', '{query}')
        ])
        chain = prompt | llm
        result = chain.invoke({'query': query, 'context': context})
        return result.content.strip()
    except Exception as e:
        logger.warning(f"Groq Q&A failed: {e}")
        return None


def run(query: str, user_id: int | None = None) -> dict:
    """Answer a general finance question."""
    q = query.lower()

    # Check for stock price query
    symbol = extract_stock_symbol(query)
    if symbol and any(k in q for k in ['price', 'how much', 'cost', 'worth', 'trading', 'what is']):
        data = get_live_stock_price(symbol)
        currency = '₹' if '.NS' in symbol else '$'
        response = (
            f"📈 **{symbol.replace('.NS', '')} Live Price**\n\n"
            f"Price: **{currency}{data['price']:,.2f}**\n"
            f"Change: {data['change_pct']:+.1f}% today\n"
            f"*Updated: {data.get('timestamp', 'just now')}*"
        )
        return {'response': response, 'intent': 'qa'}

    # Check for news query
    if any(k in q for k in ['news', 'today', 'latest', 'update', 'market today']):
        news = get_market_news_summary()
        response = f"📰 **Market News — {__import__('datetime').datetime.now().strftime('%d %b %Y')}**\n\n{news}"
        return {'response': response, 'intent': 'qa'}

    # Try knowledge base
    for topic, answer in FINANCE_KNOWLEDGE.items():
        if topic in q:
            return {'response': answer, 'intent': 'qa'}

    # Try LLM
    api_key = os.environ.get('GROQ_API_KEY')
    if api_key:
        llm_resp = _llm_answer(query, api_key)
        if llm_resp:
            return {'response': llm_resp, 'intent': 'qa'}

    # Final fallback
    out_of_scope_kw = ['recipe', 'movie', 'game', 'sport', 'football', 'cricket score', 'weather']
    if any(k in q for k in out_of_scope_kw):
        return {
            'response': (
                "🎯 **Out of Scope**\n\n"
                "I specialise in finance. Let me help you with:\n"
                "• Stock analysis & recommendations\n"
                "• Mutual funds & portfolio management\n"
                "• Gold, silver & precious metals\n"
                "• Market predictions & trends\n\n"
                "*Try: \"What is RSI?\" or \"Suggest stocks for me\"*"
            ),
            'intent': 'qa'
        }

    return {
        'response': (
            "🧠 **Zeus AI**\n\n"
            "I'm still processing that. Here's what I can help with:\n"
            "• Live stock prices (e.g., *\"What is TCS price?\"*)\n"
            "• Market concepts (RSI, P/E, Moving Averages)\n"
            "• Stock recommendations\n"
            "• Portfolio management\n"
            "• Market predictions"
        ),
        'intent': 'qa'
    }
