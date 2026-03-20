// Stock Sentiment Analysis Service - Fetches per-stock sentiment for sector pages
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export interface StockSentimentScores {
  positive: number;
  negative: number;
  neutral: number;
}

export interface StockHeadlineData {
  headline: string;
  source: string;
  vader_score: number;
  rule_boost: number;
  combined_score: number;
  classification: 'positive' | 'negative' | 'neutral';
  scores: StockSentimentScores;
}

export interface StockSentimentItem {
  overall_score: number;
  classification: string;
  confidence: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_headlines: number;
  prediction: 'Bullish' | 'Bearish' | 'Neutral';
}

export interface SectorSentimentResponse {
  stocks: { [symbol: string]: StockSentimentItem };
  headlines: StockHeadlineData[];
  metadata: {
    sector: string;
    total_headlines_scraped: number;
    total_analyzed: number;
    stocks_analyzed: number;
    sources_used: string[];
    analysis_timestamp: string;
    method: string;
  };
}

// Per-sector cache
const sectorCache: { [sector: string]: { data: SectorSentimentResponse; timestamp: number } } = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export const fetchSectorStockSentiment = async (sector: string): Promise<SectorSentimentResponse> => {
  // Return cached data if still valid
  const cached = sectorCache[sector];
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.data;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/stocks/sector/${sector.toLowerCase()}/sentiment/`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    if (!result.success || !result.data) {
      throw new Error('Invalid response');
    }

    sectorCache[sector] = { data: result.data, timestamp: Date.now() };
    return result.data;
  } catch (error) {
    console.error(`Error fetching ${sector} stock sentiment:`, error);
    return getFallbackSentiment(sector);
  }
};

const getFallbackSentiment = (sector: string): SectorSentimentResponse => {
  // Generate basic fallback data
  const sectorStocks: { [key: string]: string[] } = {
    it: ['INFY.NS', 'TCS.NS', 'HCLTECH.NS', 'WIPRO.NS', 'TECHM.NS', 'MSFT', 'GOOG', 'AAPL', 'NVDA'],
    banking: ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'JPM', 'BAC', 'WFC', 'GS'],
    automobile: ['TATAMOTORS.NS', 'M&M.NS', 'MARUTI.NS', 'BAJAJ-AUTO.NS', 'HEROMOTOCO.NS', 'TSLA', 'TM', 'GM', 'F'],
    energy: ['RELIANCE.NS', 'NTPC.NS', 'POWERGRID.NS', 'TORNTPOWER.NS', 'OIL.NS', 'XOM', 'CVX', 'COP', 'MPC'],
    pharma: ['SUNPHARMA.NS', 'CIPLA.NS', 'DRHP.NS', 'AUROPHARMA.NS', 'LUPIN.NS', 'JNJ', 'UNH', 'PFE', 'ABBV'],
    fmcg: ['NESTLEIND.NS', 'BRITANNIA.NS', 'MARICO.NS', 'HINDUNILVR.NS', 'GODREJCP.NS', 'PG', 'KO', 'NSRGY', 'DEO'],
    metals: ['TATASTEEL.NS', 'HINDALCO.NS', 'JSWSTEEL.NS', 'NATIONALUM.NS', 'JINDALSTEL.NS', 'VALE', 'RIO', 'SCCO', 'FCX'],
    finance: ['BAJFINANCE.NS', 'HDFC.NS', 'MUTHOOTFIN.NS', 'CHOLAFIN.NS', 'PFC.NS', 'BX', 'KKR', 'BLK', 'AMP'],
    hospitality: ['INDHOTEL.NS', 'EIHOTEL.NS', 'TAJGVK.NS', 'CHALET.NS', 'LUXIND.NS', 'RCL', 'CCL', 'MAR', 'HLT'],
    realty: ['DLF.NS', 'OBEROI.NS', 'GPIL.NS', 'SUNTECK.NS', 'LODHA.NS', 'SPG', 'PLD', 'VNO', 'AMB'],
    us_stocks: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK-B', 'V', 'JPM'],
  };

  const symbols = sectorStocks[sector] || sectorStocks['us_stocks'];
  const stocks: { [symbol: string]: StockSentimentItem } = {};

  const predictions: Array<'Bullish' | 'Bearish' | 'Neutral'> = ['Bullish', 'Neutral', 'Bearish'];
  const classNames = ['Mildly Bullish', 'Neutral', 'Mildly Bearish'];

  symbols.forEach((symbol, i) => {
    const idx = i % 3;
    stocks[symbol] = {
      overall_score: idx === 0 ? 0.15 : idx === 1 ? 0.02 : -0.12,
      classification: classNames[idx],
      confidence: 55 + (i * 3) % 30,
      positive_count: 3 + (i % 4),
      negative_count: 1 + (i % 3),
      neutral_count: 2 + (i % 3),
      total_headlines: 6 + (i % 5),
      prediction: predictions[idx],
    };
  });

  return {
    stocks,
    headlines: [
      {
        headline: `${sector} sector shows mixed signals amid market volatility`,
        source: 'Market Analysis (Fallback)',
        vader_score: 0.05,
        rule_boost: 0.0,
        combined_score: 0.03,
        classification: 'neutral',
        scores: { positive: 0.1, negative: 0.05, neutral: 0.85 },
      },
    ],
    metadata: {
      sector,
      total_headlines_scraped: symbols.length,
      total_analyzed: symbols.length,
      stocks_analyzed: symbols.length,
      sources_used: ['Market Analysis (Fallback)'],
      analysis_timestamp: new Date().toISOString(),
      method: 'VADER + Rule-Based Domain Analysis (Fallback)',
    },
  };
};
