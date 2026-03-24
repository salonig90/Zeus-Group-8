"""
Recommendation Agent — suggests stocks based on user portfolio and market data.
"""
import os
import logging
from ..tools import get_sector_top_performers, get_user_portfolio, calculate_portfolio_risk

logger = logging.getLogger(__name__)


def _llm_recommend(query: str, context: str, api_key: str) -> str:
    try:
        from langchain_groq import ChatGroq
        from langchain.prompts import ChatPromptTemplate

        llm = ChatGroq(model='llama-3.3-70b-versatile', api_key=api_key, temperature=0.7)
        prompt = ChatPromptTemplate.from_messages([
            ('system', (
                "You are Zeus, an expert Indian stock market advisor. "
                "Provide concise, actionable stock recommendations. "
                "Always mention sector diversification and risk. "
                "Keep response under 200 words. Use emojis for readability.\n\n"
                "Market Context:\n{context}"
            )),
            ('human', '{query}')
        ])
        chain = prompt | llm
        result = chain.invoke({'query': query, 'context': context})
        return result.content.strip()
    except Exception as e:
        logger.warning(f"Groq recommendation failed: {e}")
        return None


def run(query: str, user_id: int | None = None) -> dict:
    """
    Generate stock recommendations.
    Returns: { 'response': str, 'intent': 'recommendation' }
    """
    q = query.lower()
    portfolio = get_user_portfolio(user_id) if user_id else []
    risk = calculate_portfolio_risk(portfolio)

    # Determine sector focus from query
    sector = 'it'
    if any(k in q for k in ['bank', 'finance', 'financial']):
        sector = 'banking'
    elif any(k in q for k in ['pharma', 'health', 'medicine']):
        sector = 'pharma'
    elif any(k in q for k in ['energy', 'oil', 'power', 'reliance']):
        sector = 'energy'
    elif any(k in q for k in ['us', 'american', 'nasdaq', 's&p']):
        sector = 'us'

    top = get_sector_top_performers(sector)

    # Build context for LLM
    portfolio_summary = ""
    if portfolio:
        symbols = [p['symbol'] for p in portfolio[:5]]
        portfolio_summary = f"User holds: {', '.join(symbols)}. Risk: {risk['risk_level']}."

    top_summary = "\n".join(
        [f"  • {s['symbol']}: ₹{s['price']} ({s['change_pct']:+.1f}%)" for s in top]
    )
    context = f"{portfolio_summary}\nTop {sector.upper()} performers:\n{top_summary}"

    api_key = os.environ.get('GROQ_API_KEY')
    llm_response = _llm_recommend(query, context, api_key) if api_key else None

    if llm_response:
        return {'response': llm_response, 'intent': 'recommendation'}

    # — Fallback: structured response —
    is_risk_query = any(k in q for k in ['risk', 'diversif', 'level', 'safe'])

    if is_risk_query and portfolio:
        response = (
            f"📊 **Portfolio Risk Analysis**\n\n"
            f"Risk Level: **{risk['risk_level']}** (Score: {risk['score']}/100)\n"
            f"Diversification: {risk['diversification']} sector(s) — {', '.join(risk['sectors'])}\n\n"
            f"{risk['message']}\n\n"
            f"💡 *Tip: Aim for 5+ sectors to lower risk.*"
        )
    elif portfolio:
        held = [p['symbol'].replace('.NS', '') for p in portfolio[:3]]
        response = (
            f"🌟 **Top {sector.upper()} Picks for You**\n\n"
            + "\n".join([f"**{s['symbol'].replace('.NS','')}** — ₹{s['price']} ({s['change_pct']:+.1f}%)" for s in top])
            + f"\n\n📌 You already hold: {', '.join(held)}.\n"
            f"💡 Consider diversifying into **{sector.upper()}** to balance your portfolio."
        )
    else:
        response = (
            f"🌟 **Top {sector.upper()} Stocks Right Now**\n\n"
            + "\n".join([f"**{s['symbol'].replace('.NS','')}** — ₹{s['price']} ({s['change_pct']:+.1f}%)" for s in top])
            + "\n\n💡 *Log in to get personalized recommendations based on your portfolio.*"
        )

    return {'response': response, 'intent': 'recommendation'}
