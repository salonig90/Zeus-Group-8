import React, { useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { useAuth, PortfolioItem } from '../contexts/AuthContext';
import { predictPrice, calculateDiscount, formatPrediction } from '../services/predictionService';
import PERatioTrendGraph from '../components/PERatioTrendGraph';
import KMeansVisualization from '../components/KMeansVisualization';
import PricePredictionGraph from '../components/PricePredictionGraph';

const PortfolioSectorContainer = styled.div`
  max-width: 1600px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 80vh;
`;

const PageHeader = styled(motion.div)`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
`;

const SectorTitle = styled(motion.h1)`
  font-size: 3rem;
  background: ${props => props.theme.colors.accentPrimary};
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  font-weight: 800;
  letter-spacing: -1.5px;
  text-transform: capitalize;
`;

const BackButton = styled(motion.button)`
  background: transparent;
  border: 1px solid ${props => props.theme.colors.border};
  color: ${props => props.theme.colors.textPrimary};
  padding: 0.8rem 1.5rem;
  border-radius: ${props => props.theme.borderRadius.medium};
  cursor: pointer;
  font-weight: 600;
  transition: ${props => props.theme.transitions.default};
  
  &:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.3);
  }
`;

const SearchAndAddSection = styled(motion.div)`
  background: ${props => props.theme.colors.cardBackground};
  backdrop-filter: blur(12px);
  border-radius: ${props => props.theme.borderRadius.large};
  padding: 2rem;
  margin-bottom: 3rem;
  border: 1px solid ${props => props.theme.colors.border};
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
`;

const SearchInput = styled.input`
  flex: 1;
  min-width: 250px;
  padding: 1.2rem;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.medium};
  background: ${props => props.theme.colors.background};
  color: ${props => props.theme.colors.textPrimary};
  font-size: 1rem;
  transition: ${props => props.theme.transitions.default};
  
  &:focus {
    outline: none;
    border-color: #4facfe;
    box-shadow: ${props => props.theme.shadows.glow};
  }
`;

const AddButton = styled.button`
  background: ${props => props.theme.colors.accentPrimary};
  border: none;
  color: #000;
  padding: 1rem 2rem;
  border-radius: ${props => props.theme.borderRadius.medium};
  cursor: pointer;
  font-weight: 700;
  transition: ${props => props.theme.transitions.default};
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: ${props => props.theme.shadows.glow};
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const RefreshButton = styled.button`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  padding: 1rem 2rem;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const AnalyticsButtonGroup = styled(motion.div)`
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
`;

const AnalyticsButton = styled.button<{ active?: boolean }>`
  background: ${props => props.active 
    ? 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)' 
    : 'rgba(255, 255, 255, 0.1)'};
  border: 1px solid ${props => props.active ? 'rgba(78, 205, 196, 0.6)' : 'rgba(255, 255, 255, 0.1)'};
  color: white;
  padding: 0.8rem 1.5rem;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  
  &:hover {
    background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  }
`;

const TableContainer = styled(motion.div)`
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  border-radius: 15px;
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
`;

const StockTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  color: white;
  
  th, td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 0.9rem;
  }
  
  th {
    font-weight: 600;
    color: #4ecdc4;
    background: rgba(255, 255, 255, 0.05);
    position: sticky;
    top: 0;
    white-space: nowrap;
  }
  
  tr:hover {
    background: rgba(255, 255, 255, 0.03);
  }
`;

const PriceCell = styled.td`
  color: #00b894;
  font-weight: 600;
`;

const RemoveButton = styled.button`
  background: rgba(255, 107, 107, 0.2);
  border: 1px solid rgba(255, 107, 107, 0.5);
  color: #ff6b6b;
  padding: 0.4rem 0.8rem;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  font-size: 0.85rem;

  &:hover {
    background: rgba(255, 107, 107, 0.4);
    transform: scale(1.05);
  }
`;

const UpDown = styled.span<{ direction: 'up' | 'down' }>`
  color: ${props => props.direction === 'up' ? '#00b894' : '#ff6b6b'};
  font-weight: 600;
`;

const AnalyticsPanel = styled(motion.div)`
  background: ${props => props.theme.colors.cardBackground};
  backdrop-filter: blur(12px);
  border-radius: ${props => props.theme.borderRadius.large};
  padding: 3rem;
  border: 1px solid ${props => props.theme.colors.border};
  margin-bottom: 3rem;
`;

const EmptyState = styled(motion.div)`
  text-align: center;
  padding: 4rem 2rem;
  color: #cccccc;
`;

const SectorStatsContainer = styled(motion.div)`
  background: ${props => props.theme.colors.cardBackground};
  backdrop-filter: blur(12px);
  border-radius: ${props => props.theme.borderRadius.large};
  padding: 2rem;
  margin-bottom: 3rem;
  border: 1px solid ${props => props.theme.colors.border};
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
`;

const StatBox = styled.div`
  text-align: center;
  padding: 1.5rem;
  border-radius: ${props => props.theme.borderRadius.medium};
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid ${props => props.theme.colors.border};
`;

const StatLabel = styled.div`
  font-size: 0.8rem;
  color: ${props => props.theme.colors.textSecondary};
  margin-bottom: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 700;
`;

const StatValue = styled.div`
  font-size: 2.2rem;
  font-weight: 800;
  color: ${props => props.theme.colors.textPrimary};
  letter-spacing: -1px;
`;

const SECTOR_ICONS: { [key: string]: string } = {
  'it': '💻',
  'banking': '🏦',
  'automobile': '🚗',
  'energy': '⚡',
  'pharma': '💊',
  'fmcg': '🛒',
  'metals': '⛏️',
  'finance': '💰',
  'hospitality': '🏨',
  'realty': '🏢'
};

interface ExtendedStockData extends PortfolioItem {
  minPrice?: number;
  maxPrice?: number;
  peRatio?: number;
}

const PortfolioSector: React.FC = () => {
  const { sector } = useParams<{ sector: string }>();
  const navigate = useNavigate();
  const { portfolioBySector, removeFromPortfolio } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeAnalytics, setActiveAnalytics] = useState<'none' | 'pe' | 'kmeans' | 'prediction' | 'table'>('none');
  const [stocksData, setStocksData] = useState<Map<string, ExtendedStockData>>(new Map());

  const sectorName = sector?.toLowerCase() || '';
  const sectorStocks = useMemo(
    () => portfolioBySector[sectorName] || [],
    [portfolioBySector, sectorName]
  );
  
  const icon = SECTOR_ICONS[sectorName] || '📊';

  // Filter stocks based on search
  const filteredStocks = useMemo(
    () => sectorStocks.filter(stock =>
      stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stock.name.toLowerCase().includes(searchQuery.toLowerCase())
    ),
    [sectorStocks, searchQuery]
  );

  // Fetch detailed stock data for analytics
  const handleLoadAnalytics = useCallback(async (type: 'pe' | 'kmeans' | 'prediction') => {
    if (activeAnalytics === type) {
      setActiveAnalytics('none');
      return;
    }

    setActiveAnalytics(type);

    try {
      const newData = new Map(stocksData);

      for (const stock of sectorStocks) {
        if (!newData.has(stock.symbol)) {
          // Simulate fetching detailed data
          const minPrice = stock.price * (0.85 + Math.random() * 0.1);
          const maxPrice = stock.price * (1.1 + Math.random() * 0.1);
          const peRatio = 15 + Math.random() * 10;

          newData.set(stock.symbol, {
            ...stock,
            minPrice,
            maxPrice,
            peRatio
          });
        }
      }

      setStocksData(newData);
    } catch (err) {
      console.error('Error loading analytics:', err);
    }
  }, [activeAnalytics, sectorStocks, stocksData]);

  // Refresh live data from yfinance
  const handleRefreshData = useCallback(async () => {
    try {
      const newData = new Map(stocksData);

      for (const stock of sectorStocks) {
        try {
          const response = await fetch(`http://localhost:8000/api/auth/stocks/symbol/${stock.symbol}/`);
          if (response.ok) {
            const data = await response.json();
            const minPrice = data.currentPrice * (0.85 + Math.random() * 0.1);
            const maxPrice = data.currentPrice * (1.1 + Math.random() * 0.1);
            const peRatio = data.peRatio || 15 + Math.random() * 10;

            newData.set(stock.symbol, {
              ...stock,
              price: data.currentPrice || stock.price,
              change: data.change || stock.change,
              minPrice,
              maxPrice,
              peRatio
            });
          }
        } catch (err) {
          console.error(`Error fetching data for ${stock.symbol}:`, err);
        }
      }

      setStocksData(newData);
    } catch (err) {
      console.error('Error refreshing data:', err);
    }
  }, [sectorStocks, stocksData]);

  if (!sector) {
    return <div>Invalid sector</div>;
  }

  const totalValue = sectorStocks.reduce((total, item) => total + item.price, 0);
  const totalChange = sectorStocks.reduce((total, item) => total + item.change, 0);
  const avgChangePercent = sectorStocks.length > 0 ? totalChange / sectorStocks.length : 0;

  return (
    <PortfolioSectorContainer>
      <PageHeader
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div>
          <SectorTitle>
            {icon} {sectorName.toUpperCase()} PORTFOLIO
          </SectorTitle>
        </div>
        <BackButton
          onClick={() => navigate('/portfolio')}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          ← Back
        </BackButton>
      </PageHeader>

      {sectorStocks.length === 0 ? (
        <EmptyState
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
          <h2>No stocks in {sectorName} sector</h2>
          <p>Add stocks from the {sectorName} sector to view them here</p>
          <BackButton
            onClick={() => navigate('/stocks')}
            style={{ marginTop: '1rem', display: 'inline-block' }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Browse {sectorName.charAt(0).toUpperCase() + sectorName.slice(1)} Stocks
          </BackButton>
        </EmptyState>
      ) : (
        <>
          {/* Sector Statistics */}
          <SectorStatsContainer
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <StatBox>
              <StatLabel>Total Value</StatLabel>
              <StatValue>₹{totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</StatValue>
            </StatBox>
            <StatBox>
              <StatLabel>Stocks</StatLabel>
              <StatValue>{sectorStocks.length}</StatValue>
            </StatBox>
            <StatBox>
              <StatLabel>Avg Change</StatLabel>
              <StatValue style={{ color: avgChangePercent >= 0 ? '#00b894' : '#ff6b6b' }}>
                {avgChangePercent >= 0 ? '+' : ''}{avgChangePercent.toFixed(2)}%
              </StatValue>
            </StatBox>
          </SectorStatsContainer>

          {/* Search and Add Section */}
          <SearchAndAddSection
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            <SearchInput
              type="text"
              placeholder="Search stocks by symbol or company name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <AddButton onClick={() => navigate('/stocks')}>
              + Add Stock
            </AddButton>
            <RefreshButton onClick={handleRefreshData}>
              🔄 Refresh Data
            </RefreshButton>
          </SearchAndAddSection>

          {/* Analytics Controls */}
          <AnalyticsButtonGroup
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <AnalyticsButton
              active={activeAnalytics === 'pe'}
              onClick={() => handleLoadAnalytics('pe')}
            >
              📊 PE GRAPH
            </AnalyticsButton>
            <AnalyticsButton
              active={activeAnalytics === 'kmeans'}
              onClick={() => handleLoadAnalytics('kmeans')}
            >
              🎯 K-MEANS CLUSTERING
            </AnalyticsButton>
            <AnalyticsButton
              active={activeAnalytics === 'prediction'}
              onClick={() => handleLoadAnalytics('prediction')}
            >
              📈 PRICE PREDICTION
            </AnalyticsButton>
          </AnalyticsButtonGroup>

          {/* Analytics Panels */}
          {activeAnalytics === 'pe' && (
            <AnalyticsPanel
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <h3 style={{ color: '#4ecdc4', marginTop: 0, marginBottom: '1.5rem' }}>
                📊 P/E Ratio Trend (12 Months) - {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
              </h3>
              <PERatioTrendGraph stocks={sectorStocks} />
            </AnalyticsPanel>
          )}

          {activeAnalytics === 'kmeans' && (
            <AnalyticsPanel
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <h3 style={{ color: '#4ecdc4', marginTop: 0, marginBottom: '1.5rem' }}>
                🎯 K-Means Clustering Analysis - {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
              </h3>
              <KMeansVisualization stocks={sectorStocks} />
            </AnalyticsPanel>
          )}

          {activeAnalytics === 'prediction' && (
            <AnalyticsPanel
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <h3 style={{ color: '#4ecdc4', marginTop: 0, marginBottom: '1.5rem' }}>
                📈 Stock Price Prediction (Linear Regression) - Analyzed on {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
              </h3>
              <p style={{ color: '#cccccc', fontSize: '0.9rem', marginBottom: '1rem' }}>
                📌 Solid blue lines = Historical prices | 📌 Dashed lines = Predicted future prices (next 15 days)
              </p>
              <PricePredictionGraph stocks={sectorStocks} />
            </AnalyticsPanel>
          )}



          {/* Detailed Stock Table */}
          <TableContainer
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h3 style={{ color: '#4ecdc4', marginTop: 0, marginBottom: '1rem' }}>
              📋 {filteredStocks.length} Stock{filteredStocks.length !== 1 ? 's' : ''} in {sectorName}
            </h3>
            {filteredStocks.length > 0 ? (
              <StockTable>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Current Price</th>
                    <th>Min Price</th>
                    <th>Max Price</th>
                    <th>Discount %</th>
                    <th>P/E Ratio</th>
                    <th>Price Predict</th>
                    <th>Pred Change %</th>
                    <th>Direction</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStocks.map((stock) => {
                    const extended = (stocksData.get(stock.symbol) || stock) as ExtendedStockData;
                    const minPrice = extended.minPrice || stock.price * 0.9;
                    const maxPrice = extended.maxPrice || stock.price * 1.1;
                    const peRatio = extended.peRatio || 20;

                    const prediction = predictPrice(stock.price, stock.change);
                    const discount = calculateDiscount(stock.price, minPrice, maxPrice);
                    const formatted = formatPrediction(prediction);

                    return (
                      <tr key={stock.symbol}>
                        <td style={{ fontWeight: 600, color: '#4ecdc4' }}>{stock.symbol}</td>
                        <td>{stock.name}</td>
                        <PriceCell>₹{stock.price.toFixed(2)}</PriceCell>
                        <td>₹{minPrice.toFixed(2)}</td>
                        <td>₹{maxPrice.toFixed(2)}</td>
                        <td style={{ color: '#ff9800', fontWeight: 600 }}>{discount.toFixed(1)}%</td>
                        <td>{peRatio.toFixed(2)}</td>
                        <PriceCell>{formatted.price}</PriceCell>
                        <td style={{ color: prediction.predictedChange >= 0 ? '#00b894' : '#ff6b6b', fontWeight: 600 }}>
                          {formatted.change}
                        </td>
                        <td>
                          <UpDown direction={prediction.direction}>
                            {prediction.direction === 'up' ? '📈 UP' : '📉 DOWN'}
                          </UpDown>
                        </td>
                        <td>
                          <RemoveButton
                            onClick={() => removeFromPortfolio(stock.symbol)}
                          >
                            ✕ Remove
                          </RemoveButton>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </StockTable>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#cccccc' }}>
                🔍 No stocks match your search
              </div>
            )}
          </TableContainer>
        </>
      )}
    </PortfolioSectorContainer>
  );
};

export default PortfolioSector;
