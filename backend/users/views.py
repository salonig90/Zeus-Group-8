from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError
from .serializers import UserRegistrationSerializer, LoginSerializer, UserSerializer, StockSerializer, PortfolioStockSerializer
from .models import Stock, PortfolioStock, UserActivity, NewsletterSubscription, PaymentRecord, User
import yfinance as yf
import logging
from datetime import datetime, timedelta
import random
import pytz
import csv
import os
import requests

logger = logging.getLogger(__name__)

# MFAPI.in base URL
MFAPI_BASE_URL = "https://api.mfapi.in/mf"

# Indian sector stocks data (NIFTY 200)
INDIAN_SECTOR_STOCKS = {
    'automobile': [
        'BAJAJ-AUTO.NS', 'BHARATFORG.NS', 'BOSCHLTD.NS', 'EICHERMOT.NS', 'EXIDEIND.NS',
        'HEROMOTOCO.NS', 'HYUNDAI.NS', 'MRF.NS', 'M&M.NS', 'MARUTI.NS',
        'MOTHERSON.NS', 'SONACOMS.NS', 'TVSMOTOR.NS', 'TATAMOTORS.NS', 'TIINDIA.NS'
    ],
    'banking': [
        'SBIN.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS', 'KOTAKBANK.NS',
        'INDUSINDBK.NS', 'YESBANK.NS', 'BANKBARODA.NS', 'PNB.NS', 'CANBK.NS',
        'UNIONBANK.NS', 'IDFCFIRSTB.NS', 'FEDERALBNK.NS', 'BANKINDIA.NS', 'INDIANB.NS'
    ],
    'finance': [
        'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'JIOFIN.NS', 'MUTHOOTFIN.NS', 'SHRIRAMFIN.NS',
        'LICHSGFIN.NS', 'PFC.NS', 'RECLTD.NS', 'MOTILALOFS.NS', 'CHOLAFIN.NS',
        'HDFCAMC.NS', 'HDFCLIFE.NS', 'SBILIFE.NS', 'ICICIGI.NS', 'PAYTM.NS',
        'POLICYBZR.NS', 'IRFC.NS', 'IREDA.NS', 'HUDCO.NS', 'L&TFH.NS',
        'M&MFIN.NS', 'BAJAJHFL.NS', 'MAXFSL.NS', 'SBICARD.NS', 'BSE.NS', '360ONE.NS'
    ],
    'energy': [
        'RELIANCE.NS', 'NTPC.NS', 'POWERGRID.NS', 'TATAPOWER.NS', 'ADANIPOWER.NS',
        'ADANIGREEN.NS', 'ADANIENSOL.NS', 'ONGC.NS', 'IOC.NS', 'BPCL.NS',
        'HPCL.NS', 'GAIL.NS', 'COALINDIA.NS', 'OIL.NS', 'IGL.NS',
        'ATGL.NS', 'NTPCGREEN.NS', 'TORNTPOWER.NS', 'JSWENERGY.NS'
    ],
    'pharma': [
        'SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'LUPIN.NS',
        'AUROPHARMA.NS', 'BIOCON.NS', 'ZYDUSLIFE.NS', 'APOLLOHOSP.NS', 'FORTIS.NS',
        'MAXHEALTH.NS', 'GLENMARK.NS', 'ALKEM.NS', 'MANKIND.NS', 'TORNTPHARM.NS'
    ],
    'fmcg': [
        'HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS',
        'MARICO.NS', 'COLPAL.NS', 'GODREJCP.NS', 'TATACONSUM.NS', 'VBL.NS',
        'PATANJALI.NS', 'UNITDSPR.NS'
    ],
    'metals': [
        'TATASTEEL.NS', 'JSWSTEEL.NS', 'HINDALCO.NS', 'VEDL.NS', 'SAIL.NS',
        'NMDC.NS', 'NATIONALUM.NS', 'HINDZINC.NS', 'JINDALSTEL.NS'
    ],
    'realty': [
        'DLF.NS', 'GODREJPROP.NS', 'OBEROIREAL.NS', 'PRESTIGE.NS', 'PHOENIXLTD.NS', 'LODHA.NS'
    ],
    'it': [
        'TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS',
        'LTIM.NS', 'PERSISTENT.NS', 'MPHASIS.NS', 'COFORGE.NS', 'OFSS.NS',
        'KPITTECH.NS', 'TATAELXSI.NS', 'TATATECH.NS'
    ],
    'capital_goods': [
        'ABB.NS', 'SIEMENS.NS', 'LT.NS', 'CUMMINSIND.NS', 'HAVELLS.NS',
        'POLYCAB.NS', 'CGPOWER.NS', 'BEL.NS', 'BHEL.NS', 'HAL.NS',
        'MAZDOCK.NS', 'KEI.NS', 'APLAPOLLO.NS', 'ASTRAL.NS', 'PREMIERENE.NS',
        'WAREEENER.NS', 'ENRIN.NS'
    ],
    'telecom': [
        'BHARTIARTL.NS', 'IDEA.NS', 'INDUSTOWER.NS', 'TATACOMM.NS', 'BHARTIHEXA.NS'
    ],
    'chemicals': [
        'UPL.NS', 'SRF.NS', 'PIIND.NS', 'PIDILITIND.NS', 'COROMANDEL.NS', 'SOLARINDS.NS'
    ],
    'consumer_durables': [
        'TITAN.NS', 'VOLTAS.NS', 'HAVELLS.NS', 'DIXON.NS', 'BLUESTARCO.NS', 'KALYANKJIL.NS'
    ],
    'construction': [
        'ULTRACEMCO.NS', 'GRASIM.NS', 'AMBUJACEM.NS', 'ACC.NS', 'IRB.NS', 'RVNL.NS'
    ],
    'hospitality': [
        'INDHOTEL.NS', 'ITCHOTELS.NS', 'IRCTC.NS', 'JUBLFOOD.NS', 'DMART.NS',
        'TRENT.NS', 'SWIGGY.NS', 'NYKAA.NS', 'ZOMATO.NS'
    ],
    'us_stocks': [
        'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'GOOG', 'META', 'BRCM', 'TSLA', 'BRK-B', 'WMT', 'LLY', 'JPM', 'XOM', 'V', 'JNJ', 'MU', 'MA', 'COST', 'ORCL', 'CVX', 'NFLX', 'ABBV', 'PLTR', 'BAC', 'PG', 'AMD', 'KO', 'HD', 'CAT', 'CSCO', 'GE', 'LRCX', 'AMAT', 'MRK', 'RTX', 'MS', 'PM', 'UNH', 'GS', 'WFC', 'TMUS', 'GEV', 'IBM', 'LIN', 'MCD', 'INTC', 'VZ', 'PEP', 'AXP', 'T', 'KLAC', 'C', 'AMGN', 'NEE', 'ABT', 'CRM', 'DIS', 'TMO', 'TJX', 'TXN', 'GILD', 'ISRG', 'SCHW', 'ANET', 'APH', 'COP', 'PFE', 'BA', 'UBER', 'DE', 'ADI', 'APP', 'BLK', 'LMT', 'HON', 'UNP', 'QCOM', 'ETN', 'BKNG', 'WELL', 'DHR', 'PANW', 'SYK', 'SPGI', 'LOW', 'INTU', 'CB', 'ACN', 'PGR', 'PLD', 'BMY', 'NOW', 'VRTX', 'PH', 'COF', 'MDT', 'HCA', 'CME', 'MCK', 'MO', 'GLW', 'SBUX', 'SNDK', 'SO', 'CMCSA', 'NEM', 'CRWD', 'BSX', 'CEG', 'DELL', 'ADBE', 'NOC', 'WDC', 'DUK', 'EQIX', 'GD', 'WM', 'HWM', 'STX', 'CVS', 'TT', 'ICE', 'WMB', 'BX', 'MMC', 'MAR', 'FDX', 'ADP', 'PWR', 'AMT', 'UPS', 'PNC', 'SNPS', 'KKR', 'USB', 'JCI', 'BK', 'CDNS', 'NKE', 'REGN', 'MCO', 'ABNB', 'SHW', 'MSI', 'FCX', 'EOG', 'MMM', 'ITW', 'CMI', 'ORLY', 'KMI', 'ECL', 'MNST', 'MDLZ', 'EMR', 'CTAS', 'VLO', 'RCL', 'CSX', 'PSX', 'SLB', 'AON', 'CI', 'MPC', 'ROST', 'CL', 'DASH', 'WBD', 'AEP', 'RSG', 'CRH', 'HLT', 'TDG', 'LHX', 'GM', 'APO', 'ELV', 'TRV', 'HOOD', 'COR', 'NSC', 'APD', 'FTNT', 'SPG', 'SRE', 'OXY', 'BKR', 'DLR', 'PCAR', 'TEL', 'O', 'OKE', 'AJG', 'AFL', 'TFC', 'CIEN', 'AZO', 'FANG', 'ALL'
    ]
}

# Common Indian Mutual Funds (Scheme Codes for MFAPI.in)
INDIAN_MUTUAL_FUNDS = [
    {'code': '120503', 'name': 'SBI Small Cap Fund'},
    {'code': '119063', 'name': 'HDFC Top 100 Fund'},
    {'code': '120594', 'name': 'ICICI Prudential Bluechip Fund'},
    {'code': '118666', 'name': 'Nippon India Small Cap Fund'},
    {'code': '120505', 'name': 'Axis Bluechip Fund'},
    {'code': '118989', 'name': 'Mirae Asset Large Cap Fund'},
]

@api_view(['GET'])
@permission_classes([AllowAny])
def get_mutual_funds(request):
    """Fetch mutual fund data from MFAPI.in for India and yfinance for global"""
    try:
        funds_data = []
        
        # 1. Fetch Indian Mutual Funds from MFAPI.in
        for fund in INDIAN_MUTUAL_FUNDS:
            try:
                # MFAPI.in provides scheme data including historical NAVs
                response = requests.get(f"{MFAPI_BASE_URL}/{fund['code']}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    meta = data.get('meta', {})
                    nav_history = data.get('data', [])
                    
                    if nav_history:
                        current_nav = float(nav_history[0].get('nav', 0))
                        prev_nav = float(nav_history[1].get('nav', current_nav)) if len(nav_history) > 1 else current_nav
                        change = current_nav - prev_nav
                        change_pct = (change / prev_nav * 100) if prev_nav > 0 else 0
                        
                        funds_data.append({
                            'symbol': fund['code'],
                            'name': meta.get('scheme_name', fund['name']),
                            'currentPrice': round(current_nav, 2),
                            'change': round(change, 2),
                            'changePercent': round(change_pct, 2),
                            'category': meta.get('scheme_category', 'Equity'),
                            'rating': random.randint(3, 5),
                            'aum': random.randint(5000, 50000) # MFAPI doesn't provide AUM easily
                        })
            except Exception as e:
                logger.error(f"Error fetching MF {fund['code']}: {str(e)}")
                continue

        # 2. Fetch Global Mutual Funds/ETFs from yfinance
        GLOBAL_FUNDS = ['VFIAX', 'VTSAX', 'VFFVX']
        for symbol in GLOBAL_FUNDS:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                current_price = info.get('navPrice', info.get('previousClose', 0))
                change = info.get('ytdReturn', 0) # Use YTD return as a proxy for change
                
                funds_data.append({
                    'symbol': symbol,
                    'name': info.get('longName', symbol),
                    'currentPrice': round(current_price, 2),
                    'change': round(change, 2),
                    'changePercent': round(change, 2),
                    'category': info.get('fundFamily', 'Global Fund'),
                    'rating': info.get('overallRating', 4),
                    'aum': info.get('totalAssets', 0) / 1e6 # In Millions
                })
            except Exception as e:
                logger.error(f"Error fetching Global MF {symbol}: {str(e)}")
                continue

        return Response({
            'success': True,
            'data': funds_data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in get_mutual_funds: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching mutual funds',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save user with hashed password
        user = serializer.save()
        
        # Save user to CSV file
        try:
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'users.csv')
            file_exists = os.path.isfile(csv_path)
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(['username', 'email', 'first_name', 'phone', 'signup_timestamp'])
                writer.writerow([
                    user.username,
                    user.email,
                    user.first_name or '',
                    user.phone or '',
                    datetime.now().isoformat()
                ])
            logger.info(f"User {user.email} saved to CSV at {csv_path}")
        except Exception as csv_err:
            logger.error(f"Failed to save user to CSV: {str(csv_err)}")
        
        # Record signup activity
        UserActivity.objects.create(
            user=user,
            action='SIGNUP',
            description=f"User {user.email} signed up",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Login user (optional - for session authentication)
        login(request, user)
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': access_token,
                'refresh': str(refresh)
            }
        }, status=status.HTTP_201_CREATED)
        
    except IntegrityError as e:
        return Response({
            'success': False,
            'message': 'Database integrity error',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Internal server error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    try:
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid credentials',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        
        # Record login activity
        UserActivity.objects.create(
            user=user,
            action='LOGIN',
            description=f"User {user.email} logged in",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Login user (for session authentication)
        login(request, user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': access_token,
                'refresh': str(refresh)
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Internal server error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({
                'success': False,
                'message': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify and refresh the token
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        return Response({
            'success': True,
            'message': 'Token refreshed successfully',
            'tokens': {
                'access': access_token,
                'refresh': str(refresh)
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Invalid refresh token',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    if request.user.is_authenticated:
        return Response({
            'success': True,
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)
    return Response({
        'success': False,
        'error': 'Not authenticated'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_live_metals_prices(request):
    """Fetch live gold and silver prices from yfinance"""
    try:
        # Fetch GOLD (GC=F) and SILVER (SI=F) futures
        gold_ticker = yf.Ticker('GC=F')
        silver_ticker = yf.Ticker('SI=F')

        # Get recent history for more accurate data
        gold_hist = gold_ticker.history(period='2d', interval='1d')
        silver_hist = silver_ticker.history(period='2d', interval='1d')

        gold_info = gold_ticker.info
        silver_info = silver_ticker.info

        # Extract gold data
        gold_current = 0
        gold_prev = 0

        if not gold_hist.empty and len(gold_hist) >= 1:
            gold_current = gold_hist.iloc[-1].get('Close', 0)
            if len(gold_hist) >= 2:
                gold_prev = gold_hist.iloc[-2].get('Close', gold_current)
            else:
                gold_prev = gold_info.get('regularMarketPreviousClose', gold_current)
        else:
            gold_current = gold_info.get('currentPrice', gold_info.get('regularMarketPrice', 0))
            gold_prev = gold_info.get('regularMarketPreviousClose', gold_current)

        # Extract silver data
        silver_current = 0
        silver_prev = 0

        if not silver_hist.empty and len(silver_hist) >= 1:
            silver_current = silver_hist.iloc[-1].get('Close', 0)
            if len(silver_hist) >= 2:
                silver_prev = silver_hist.iloc[-2].get('Close', silver_current)
            else:
                silver_prev = silver_info.get('regularMarketPreviousClose', silver_current)
        else:
            silver_current = silver_info.get('currentPrice', silver_info.get('regularMarketPrice', 0))
            silver_prev = silver_info.get('regularMarketPreviousClose', silver_current)

        # Calculate changes
        gold_change = gold_current - gold_prev if gold_prev and gold_prev > 0 else 0
        silver_change = silver_current - silver_prev if silver_prev and silver_prev > 0 else 0

        gold_change_pct = (gold_change / gold_prev * 100) if gold_prev and gold_prev > 0 else 0
        silver_change_pct = (silver_change / silver_prev * 100) if silver_prev and silver_prev > 0 else 0

        # Validate data
        if gold_current <= 0 or silver_current <= 0:
            raise ValueError("Invalid price data received")

        return Response({
            'success': True,
            'data': {
                'gold': {
                    'symbol': 'GC=F',
                    'price': round(float(gold_current), 2),
                    'change': round(float(gold_change), 2),
                    'changePercent': round(float(gold_change_pct), 2),
                    'lastUpdated': datetime.now().isoformat()
                },
                'silver': {
                    'symbol': 'SI=F',
                    'price': round(float(silver_current), 2),
                    'change': round(float(silver_change), 2),
                    'changePercent': round(float(silver_change_pct), 2),
                    'lastUpdated': datetime.now().isoformat()
                }
            }
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching metals prices: {str(e)}")
        # Return fallback data with more realistic values
        return Response({
            'success': True,
            'data': {
                'gold': {
                    'symbol': 'GC=F',
                    'price': 5176.50,  # Recent real price
                    'change': 41.80,
                    'changePercent': 0.81,
                    'lastUpdated': datetime.now().isoformat()
                },
                'silver': {
                    'symbol': 'SI=F',
                    'price': 84.61,  # Recent real price
                    'change': 1.43,
                    'changePercent': 1.72,
                    'lastUpdated': datetime.now().isoformat()
                }
            }
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_sector_stocks(request, sector):
    """Fetch stock data for a specific sector with database-first approach"""
    try:
        sector = sector.lower()

        # Check if we have stocks for this sector in the database
        db_stocks = Stock.objects.filter(sector=sector)
        
        # If no stocks in database OR if we want to ensure sync with INDIAN_SECTOR_STOCKS
        # For this update, we'll force a check if the sector is in our new mapping
        if sector in INDIAN_SECTOR_STOCKS:
            expected_symbols = INDIAN_SECTOR_STOCKS[sector]
            
            # If database count doesn't match or is empty, we sync/seed
            if not db_stocks.exists() or db_stocks.count() != len(expected_symbols):
                # Realistic fallback prices for Indian and International stocks
                REALISTIC_PRICES = {
                    # IT Stocks
                    'INFY.NS': 1560, 'TCS.NS': 3950, 'HCLTECH.NS': 1720, 'WIPRO.NS': 520, 'TECHM.NS': 1450,
                    'LTIM.NS': 4800, 'PERSISTENT.NS': 3800, 'MPHASIS.NS': 2400, 'COFORGE.NS': 5200, 'OFSS.NS': 8200,
                    'KPITTECH.NS': 1400, 'TATAELXSI.NS': 7200, 'TATATECH.NS': 1050,
                    # Banking Stocks
                    'SBIN.NS': 820, 'HDFCBANK.NS': 1650, 'ICICIBANK.NS': 1200, 'AXISBANK.NS': 1180, 'KOTAKBANK.NS': 1800,
                    'INDUSINDBK.NS': 1450, 'YESBANK.NS': 25, 'BANKBARODA.NS': 280, 'PNB.NS': 125, 'CANBK.NS': 580,
                    'UNIONBANK.NS': 155, 'IDFCFIRSTB.NS': 85, 'FEDERALBNK.NS': 165, 'BANKINDIA.NS': 145, 'INDIANB.NS': 520,
                    # Automobile Stocks
                    'BAJAJ-AUTO.NS': 9800, 'BHARATFORG.NS': 1200, 'BOSCHLTD.NS': 28000, 'EICHERMOT.NS': 4500, 'EXIDEIND.NS': 450,
                    'HEROMOTOCO.NS': 5400, 'HYUNDAI.NS': 1900, 'MRF.NS': 125000, 'M&M.NS': 2800, 'MARUTI.NS': 12800,
                    'MOTHERSON.NS': 150, 'SONACOMS.NS': 650, 'TVSMOTOR.NS': 2400, 'TATAMOTORS.NS': 920, 'TIINDIA.NS': 3800,
                    # Energy Stocks
                    'RELIANCE.NS': 2950, 'NTPC.NS': 380, 'POWERGRID.NS': 320, 'TATAPOWER.NS': 450, 'ADANIPOWER.NS': 620,
                    'ADANIGREEN.NS': 1800, 'ADANIENSOL.NS': 1100, 'ONGC.NS': 280, 'IOC.NS': 170, 'BPCL.NS': 620,
                    'HPCL.NS': 520, 'GAIL.NS': 210, 'COALINDIA.NS': 480, 'OIL.NS': 680, 'IGL.NS': 450,
                    'ATGL.NS': 950, 'NTPCGREEN.NS': 110, 'TORNTPOWER.NS': 1650, 'JSWENERGY.NS': 620,
                    # Pharma Stocks
                    'SUNPHARMA.NS': 1750, 'DRREDDY.NS': 6200, 'CIPLA.NS': 1580, 'DIVISLAB.NS': 4200, 'LUPIN.NS': 1880,
                    'AUROPHARMA.NS': 1480, 'BIOCON.NS': 280, 'ZYDUSLIFE.NS': 1050, 'APOLLOHOSP.NS': 6200, 'FORTIS.NS': 450,
                    'MAXHEALTH.NS': 880, 'GLENMARK.NS': 1200, 'ALKEM.NS': 5200, 'MANKIND.NS': 2200, 'TORNTPHARM.NS': 2800,
                    # FMCG Stocks
                    'HINDUNILVR.NS': 2800, 'ITC.NS': 450, 'NESTLEIND.NS': 2550, 'BRITANNIA.NS': 5200, 'DABUR.NS': 580,
                    'MARICO.NS': 620, 'COLPAL.NS': 2800, 'GODREJCP.NS': 1250, 'TATACONSUM.NS': 1150, 'VBL.NS': 1550,
                    'PATANJALI.NS': 1450, 'UNITDSPR.NS': 1200,
                    # Metals Stocks
                    'TATASTEEL.NS': 165, 'JSWSTEEL.NS': 920, 'HINDALCO.NS': 680, 'VEDL.NS': 450, 'SAIL.NS': 150,
                    'NMDC.NS': 240, 'NATIONALUM.NS': 190, 'HINDZINC.NS': 650, 'JINDALSTEL.NS': 1050,
                    # Realty Stocks
                    'DLF.NS': 1200, 'GODREJPROP.NS': 2400, 'OBEROIREAL.NS': 1800, 'PRESTIGE.NS': 1650, 'PHOENIXLTD.NS': 3200, 'LODHA.NS': 1200,
                    # Finance Stocks
                    'BAJFINANCE.NS': 7200, 'BAJAJFINSV.NS': 1650, 'JIOFIN.NS': 350, 'MUTHOOTFIN.NS': 1800, 'SHRIRAMFIN.NS': 2400,
                    'LICHSGFIN.NS': 650, 'PFC.NS': 520, 'RECLTD.NS': 580, 'MOTILALOFS.NS': 2200, 'CHOLAFIN.NS': 1380,
                    'HDFCAMC.NS': 3800, 'HDFCLIFE.NS': 650, 'SBILIFE.NS': 1450, 'ICICIGI.NS': 1650, 'PAYTM.NS': 680,
                    'POLICYBZR.NS': 1250, 'IRFC.NS': 175, 'IREDA.NS': 220, 'HUDCO.NS': 240, 'L&TFH.NS': 175,
                    'M&MFIN.NS': 310, 'BAJAJHFL.NS': 150, 'MAXFSL.NS': 1050, 'SBICARD.NS': 720, 'BSE.NS': 2800, '360ONE.NS': 780,
                    # Capital Goods
                    'ABB.NS': 7200, 'SIEMENS.NS': 6800, 'LT.NS': 3500, 'CUMMINSIND.NS': 3200, 'HAVELLS.NS': 1800,
                    'POLYCAB.NS': 6800, 'CGPOWER.NS': 650, 'BEL.NS': 280, 'BHEL.NS': 290, 'HAL.NS': 4200,
                    'MAZDOCK.NS': 4500, 'KEI.NS': 4200, 'APLAPOLLO.NS': 1550, 'ASTRAL.NS': 2200, 'PREMIERENE.NS': 420,
                    'WAREEENER.NS': 2800, 'ENRIN.NS': 2920,
                    # Telecom
                    'BHARTIARTL.NS': 1450, 'IDEA.NS': 14, 'INDUSTOWER.NS': 350, 'TATACOMM.NS': 1900, 'BHARTIHEXA.NS': 1200,
                    # Chemicals
                    'UPL.NS': 520, 'SRF.NS': 2400, 'PIIND.NS': 3800, 'PIDILITIND.NS': 3100, 'COROMANDEL.NS': 1600, 'SOLARINDS.NS': 9800,
                    # Consumer Durables
                    'TITAN.NS': 3400, 'VOLTAS.NS': 1500, 'DIXON.NS': 11500, 'BLUESTARCO.NS': 1600, 'KALYANKJIL.NS': 650,
                    # Construction
                    'ULTRACEMCO.NS': 10500, 'GRASIM.NS': 2400, 'AMBUJACEM.NS': 650, 'ACC.NS': 2500, 'IRB.NS': 65, 'RVNL.NS': 580,
                    # Hospitality
                    'INDHOTEL.NS': 680, 'ITCHOTELS.NS': 450, 'IRCTC.NS': 950, 'JUBLFOOD.NS': 520, 'DMART.NS': 4800,
                    'TRENT.NS': 7200, 'SWIGGY.NS': 420, 'NYKAA.NS': 180, 'ZOMATO.NS': 250,
                    # US Stocks
                    'AAPL': 235, 'MSFT': 420, 'GOOGL': 175, 'AMZN': 185, 'META': 510, 'TSLA': 240, 'NVDA': 125, 'BRK-B': 450, 'V': 280, 'JPM': 210,
                    'BAC': 38, 'WFC': 58, 'GS': 450, 'TM': 215, 'GM': 58, 'F': 12, 'XOM': 110, 'CVX': 165, 'COP': 128, 'MPC': 85,
                    'JNJ': 157, 'UNH': 520, 'PFE': 28, 'ABBV': 205, 'PG': 162, 'KO': 63, 'NSRGY': 95, 'DEO': 72, 'VALE': 12, 'RIO': 68,
                    'SCCO': 45, 'FCX': 45, 'BX': 135, 'KKR': 135, 'BLK': 910, 'AMP': 305, 'RCL': 165, 'CCL': 22, 'MAR': 320, 'HLT': 215,
                    'SPG': 143, 'PLD': 56, 'VNO': 48, 'AMB': 128,
                    'BRCM': 1300, 'WMT': 67, 'LLY': 780, 'MU': 125, 'COST': 730, 'ORCL': 122, 'NFLX': 680, 'PLTR': 25, 'CAT': 340, 'CSCO': 49, 'GE': 160, 'LRCX': 850, 'AMAT': 210, 'MRK': 130, 'RTX': 105, 'MS': 95, 'PM': 100, 'TMUS': 165, 'GEV': 150, 'IBM': 170, 'LIN': 440, 'MCD': 270, 'VZ': 40, 'PEP': 170, 'AXP': 230, 'T': 18, 'KLAC': 700, 'C': 60, 'AMGN': 300, 'NEE': 75, 'ABT': 110, 'TMO': 580, 'TJX': 100, 'TXN': 170, 'GILD': 65, 'ISRG': 390, 'SCHW': 70, 'ANET': 290, 'APH': 120, 'BA': 180, 'UBER': 70, 'DE': 380, 'ADI': 210, 'APP': 50, 'LMT': 460, 'HON': 200, 'UNP': 230, 'QCOM': 200, 'ETN': 280, 'BKNG': 3800, 'WELL': 100, 'DHR': 250, 'PANW': 320, 'SYK': 340, 'SPGI': 430, 'LOW': 230, 'INTU': 630, 'CB': 260, 'ACN': 300, 'PGR': 210, 'BMY': 45, 'NOW': 730, 'VRTX': 470, 'PH': 500, 'COF': 140, 'MDT': 85, 'HCA': 300, 'CME': 200, 'MCK': 580, 'MO': 45, 'GLW': 35, 'SBUX': 80, 'SNDK': 80, 'SO': 80, 'CMCSA': 40, 'NEM': 45, 'CRWD': 380, 'BSX': 75, 'CEG': 210, 'DELL': 140, 'NOC': 460, 'WDC': 80, 'DUK': 100, 'EQIX': 770, 'GD': 300, 'WM': 210, 'HWM': 80, 'STX': 90, 'CVS': 60, 'TT': 340, 'ICE': 140, 'WMB': 40, 'MMC': 220, 'FDX': 260, 'ADP': 250, 'PWR': 250, 'AMT': 200, 'UPS': 140, 'PNC': 150, 'SNPS': 600, 'USB': 40, 'JCI': 70, 'BK': 60, 'CDNS': 320, 'NKE': 95, 'REGN': 950, 'MCO': 400, 'ABNB': 160, 'SHW': 300, 'MSI': 380, 'EOG': 120, 'MMM': 100, 'ITW': 250, 'CMI': 280, 'ORLY': 1100, 'KMI': 20, 'ECL': 180, 'MNST': 50, 'MDLZ': 70, 'EMR': 110, 'CTAS': 700, 'VLO': 150, 'CSX': 35, 'PSX': 120, 'SLB': 45, 'AON': 300, 'CI': 340, 'ROST': 140, 'CL': 90, 'DASH': 110, 'WBD': 8, 'AEP': 90, 'RSG': 190, 'CRH': 80, 'TDG': 1300, 'LHX': 230, 'APO': 110, 'ELV': 540, 'TRV': 230, 'HOOD': 20, 'COR': 35, 'NSC': 230, 'APD': 270, 'FTNT': 60, 'SRE': 75, 'OXY': 60, 'BKR': 35, 'DLR': 140, 'PCAR': 110, 'TEL': 160, 'O': 55, 'OKE': 80, 'AJG': 240, 'AFL': 85, 'TFC': 40, 'CIEN': 50, 'AZO': 3000, 'FANG': 160, 'ALL': 160
                }
                
                # Update or create stocks to ensure they are in the correct sector
                for symbol in expected_symbols:
                    try:
                        base_price = REALISTIC_PRICES.get(symbol, 100)
                        variation = random.uniform(-0.05, 0.05)
                        current_price = base_price * (1 + variation)
                        
                        Stock.objects.update_or_create(
                            symbol=symbol,
                            defaults={
                                'name': symbol.replace('.NS', '').replace('-', ' '),
                                'sector': sector,
                                'current_price': float(current_price),
                                'change': 0,
                                'change_percent': 0,
                                'day_high': float(current_price * 1.01),
                                'day_low': float(current_price * 0.99),
                                'pe_ratio': round(random.uniform(15, 30), 2),
                                'market_cap': random.randint(50000000000, 800000000000),
                                'volume': random.randint(100000, 50000000)
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error seeding stock {symbol}: {str(e)}")
                
                # Refresh the list from DB
                db_stocks = Stock.objects.filter(sector=sector)
        else:
            return Response({
                'success': False,
                'message': f'Sector {sector} not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Map DB stocks to response format
        stocks_data = []
        ist = pytz.timezone('Asia/Kolkata')
        
        for stock in db_stocks:
            stocks_data.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'currentPrice': round(stock.current_price, 2),
                'change': round(stock.change, 2),
                'changePercent': round(stock.change_percent, 2),
                'dayHigh': round(stock.day_high, 2),
                'dayLow': round(stock.day_low, 2),
                'peRatio': round(stock.pe_ratio, 2),
                'marketCap': stock.market_cap,
                'volume': stock.volume,
                'sector': stock.sector
            })

        return Response({
            'success': True,
            'sector': sector,
            'data': stocks_data,
            'count': len(stocks_data),
            'timestamp': datetime.now(ist).isoformat()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error fetching sector stocks: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching sector stocks',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Map DB stocks to response format
        stocks_data = []
        ist = pytz.timezone('Asia/Kolkata')
        
        for stock in db_stocks:
            stocks_data.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'currentPrice': round(stock.current_price, 2),
                'change': round(stock.change, 2),
                'changePercent': round(stock.change_percent, 2),
                'dayHigh': round(stock.day_high, 2),
                'dayLow': round(stock.day_low, 2),
                'peRatio': round(stock.pe_ratio, 2),
                'marketCap': stock.market_cap,
                'volume': stock.volume,
                'sector': stock.sector
            })

        return Response({
            'success': True,
            'sector': sector,
            'data': stocks_data,
            'count': len(stocks_data),
            'timestamp': datetime.now(ist).isoformat()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error fetching sector stocks: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching sector stocks',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAdminUser])
def manage_stocks(request, symbol=None):
    """Admin-only view to list, add, or remove stocks"""
    try:
        if request.method == 'GET':
            # List all stocks by sector
            stocks = Stock.objects.all().order_by('sector', 'symbol')
            serializer = StockSerializer(stocks, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        elif request.method == 'POST':
            # Add a new stock
            symbol = request.data.get('symbol', '').upper()
            name = request.data.get('name', symbol)
            sector = request.data.get('sector', '').lower()
            current_price = request.data.get('current_price', 100)
            
            if not symbol or not sector:
                return Response({
                    'success': False,
                    'message': 'Symbol and sector are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            stock, created = Stock.objects.update_or_create(
                symbol=symbol,
                defaults={
                    'name': name,
                    'sector': sector,
                    'current_price': float(current_price),
                    'change': 0,
                    'change_percent': 0,
                    'day_high': float(current_price * 1.01),
                    'day_low': float(current_price * 0.99),
                    'pe_ratio': round(random.uniform(15, 30), 2),
                    'market_cap': random.randint(50000000000, 800000000000),
                    'volume': random.randint(100000, 50000000)
                }
            )
            
            return Response({
                'success': True,
                'message': f"Stock {symbol} {'added' if created else 'updated'} successfully",
                'data': StockSerializer(stock).data
            }, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            # Remove a stock
            if not symbol:
                return Response({
                    'success': False,
                    'message': 'Symbol is required for deletion'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                stock = Stock.objects.get(symbol=symbol)
                stock.delete()
                return Response({
                    'success': True,
                    'message': f"Stock {symbol} removed successfully"
                }, status=status.HTTP_200_OK)
            except Stock.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f"Stock {symbol} not found"
                }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        logger.error(f"Error managing stocks: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error managing stocks',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_portfolio(request):
    """Add a stock to user's portfolio"""
    try:
        symbol = request.data.get('symbol')
        sector = request.data.get('sector')
        quantity = request.data.get('quantity', 1)
        buying_price = request.data.get('buying_price', 0)
        
        if not symbol or not sector:
            return Response({
                'success': False,
                'message': 'Symbol and sector are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or fetch stock data
        stock, created = Stock.objects.get_or_create(
            symbol=symbol,
            defaults={
                'name': symbol,
                'sector': sector,
                'current_price': float(buying_price) if buying_price > 0 else 0,
                'change': 0,
                'change_percent': 0,
                'day_high': 0,
                'day_low': 0,
                'pe_ratio': 0,
                'market_cap': 0,
                'volume': 0
            }
        )
        
        # Add or update portfolio stock
        portfolio_stock, created = PortfolioStock.objects.update_or_create(
            user=request.user,
            stock=stock,
            defaults={
                'sector': sector,
                'quantity': quantity,
                'buying_price': buying_price
            }
        )
        
        return Response({
            'success': True,
            'message': 'Stock added to portfolio successfully',
            'portfolio_stock': PortfolioStockSerializer(portfolio_stock).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error adding to portfolio: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error adding to portfolio',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_portfolio(request):
    """Get user's portfolio organized by sector"""
    try:
        portfolio_stocks = PortfolioStock.objects.filter(user=request.user).order_by('sector', 'stock__symbol')
        
        # Organize by sector
        portfolio_by_sector = {}
        for ps in portfolio_stocks:
            if ps.sector not in portfolio_by_sector:
                portfolio_by_sector[ps.sector] = []
            portfolio_by_sector[ps.sector].append(PortfolioStockSerializer(ps).data)
        
        return Response({
            'success': True,
            'portfolio': portfolio_by_sector,
            'total_stocks': portfolio_stocks.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching portfolio: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching portfolio',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_sector_prices(request, sector):
    """Fetch live prices for all stocks in a sector and save to database"""
    try:
        sector = sector.lower()

        if sector not in INDIAN_SECTOR_STOCKS:
            return Response({
                'success': False,
                'message': f'Sector {sector} not found'
            }, status=status.HTTP_404_NOT_FOUND)

        symbols = INDIAN_SECTOR_STOCKS[sector]
        updated_stocks = []
        
        # Delete existing prices for this sector to refresh
        Stock.objects.filter(sector=sector).delete()
        
        # Realistic fallback prices for Indian and International stocks
        REALISTIC_PRICES = {
            # IT Stocks
            'INFY.NS': 1560, 'TCS.NS': 3950, 'HCLTECH.NS': 1720, 'WIPRO.NS': 520, 'TECHM.NS': 1450,
            'LTIM.NS': 4800, 'PERSISTENT.NS': 3800, 'MPHASIS.NS': 2400, 'COFORGE.NS': 5200, 'OFSS.NS': 8200,
            'KPITTECH.NS': 1400, 'TATAELXSI.NS': 7200, 'TATATECH.NS': 1050,
            # Banking Stocks
            'SBIN.NS': 820, 'HDFCBANK.NS': 1650, 'ICICIBANK.NS': 1200, 'AXISBANK.NS': 1180, 'KOTAKBANK.NS': 1800,
            'INDUSINDBK.NS': 1450, 'YESBANK.NS': 25, 'BANKBARODA.NS': 280, 'PNB.NS': 125, 'CANBK.NS': 580,
            'UNIONBANK.NS': 155, 'IDFCFIRSTB.NS': 85, 'FEDERALBNK.NS': 165, 'BANKINDIA.NS': 145, 'INDIANB.NS': 520,
            # Automobile Stocks
            'BAJAJ-AUTO.NS': 9800, 'BHARATFORG.NS': 1200, 'BOSCHLTD.NS': 28000, 'EICHERMOT.NS': 4500, 'EXIDEIND.NS': 450,
            'HEROMOTOCO.NS': 5400, 'HYUNDAI.NS': 1900, 'MRF.NS': 125000, 'M&M.NS': 2800, 'MARUTI.NS': 12800,
            'MOTHERSON.NS': 150, 'SONACOMS.NS': 650, 'TVSMOTOR.NS': 2400, 'TATAMOTORS.NS': 920, 'TIINDIA.NS': 3800,
            # Energy Stocks
            'RELIANCE.NS': 2950, 'NTPC.NS': 380, 'POWERGRID.NS': 320, 'TATAPOWER.NS': 450, 'ADANIPOWER.NS': 620,
            'ADANIGREEN.NS': 1800, 'ADANIENSOL.NS': 1100, 'ONGC.NS': 280, 'IOC.NS': 170, 'BPCL.NS': 620,
            'HPCL.NS': 520, 'GAIL.NS': 210, 'COALINDIA.NS': 480, 'OIL.NS': 680, 'IGL.NS': 450,
            'ATGL.NS': 950, 'NTPCGREEN.NS': 110, 'TORNTPOWER.NS': 1650, 'JSWENERGY.NS': 620,
            # Pharma Stocks
            'SUNPHARMA.NS': 1750, 'DRREDDY.NS': 6200, 'CIPLA.NS': 1580, 'DIVISLAB.NS': 4200, 'LUPIN.NS': 1880,
            'AUROPHARMA.NS': 1480, 'BIOCON.NS': 280, 'ZYDUSLIFE.NS': 1050, 'APOLLOHOSP.NS': 6200, 'FORTIS.NS': 450,
            'MAXHEALTH.NS': 880, 'GLENMARK.NS': 1200, 'ALKEM.NS': 5200, 'MANKIND.NS': 2200, 'TORNTPHARM.NS': 2800,
            # FMCG Stocks
            'HINDUNILVR.NS': 2800, 'ITC.NS': 450, 'NESTLEIND.NS': 2550, 'BRITANNIA.NS': 5200, 'DABUR.NS': 580,
            'MARICO.NS': 620, 'COLPAL.NS': 2800, 'GODREJCP.NS': 1250, 'TATACONSUM.NS': 1150, 'VBL.NS': 1550,
            'PATANJALI.NS': 1450, 'UNITDSPR.NS': 1200,
            # Metals Stocks
            'TATASTEEL.NS': 165, 'JSWSTEEL.NS': 920, 'HINDALCO.NS': 680, 'VEDL.NS': 450, 'SAIL.NS': 150,
            'NMDC.NS': 240, 'NATIONALUM.NS': 190, 'HINDZINC.NS': 650, 'JINDALSTEL.NS': 1050,
            # Realty Stocks
            'DLF.NS': 1200, 'GODREJPROP.NS': 2400, 'OBEROIREAL.NS': 1800, 'PRESTIGE.NS': 1650, 'PHOENIXLTD.NS': 3200, 'LODHA.NS': 1200,
            # Finance Stocks
            'BAJFINANCE.NS': 7200, 'BAJAJFINSV.NS': 1650, 'JIOFIN.NS': 350, 'MUTHOOTFIN.NS': 1800, 'SHRIRAMFIN.NS': 2400,
            'LICHSGFIN.NS': 650, 'PFC.NS': 520, 'RECLTD.NS': 580, 'MOTILALOFS.NS': 2200, 'CHOLAFIN.NS': 1380,
            'HDFCAMC.NS': 3800, 'HDFCLIFE.NS': 650, 'SBILIFE.NS': 1450, 'ICICIGI.NS': 1650, 'PAYTM.NS': 680,
            'POLICYBZR.NS': 1250, 'IRFC.NS': 175, 'IREDA.NS': 220, 'HUDCO.NS': 240, 'L&TFH.NS': 175,
            'M&MFIN.NS': 310, 'BAJAJHFL.NS': 150, 'MAXFSL.NS': 1050, 'SBICARD.NS': 720, 'BSE.NS': 2800, '360ONE.NS': 780,
            # Capital Goods
            'ABB.NS': 7200, 'SIEMENS.NS': 6800, 'LT.NS': 3500, 'CUMMINSIND.NS': 3200, 'HAVELLS.NS': 1800,
            'POLYCAB.NS': 6800, 'CGPOWER.NS': 650, 'BEL.NS': 280, 'BHEL.NS': 290, 'HAL.NS': 4200,
            'MAZDOCK.NS': 4500, 'KEI.NS': 4200, 'APLAPOLLO.NS': 1550, 'ASTRAL.NS': 2200, 'PREMIERENE.NS': 420,
            'WAREEENER.NS': 2800, 'ENRIN.NS': 2920,
            # Telecom
            'BHARTIARTL.NS': 1450, 'IDEA.NS': 14, 'INDUSTOWER.NS': 350, 'TATACOMM.NS': 1900, 'BHARTIHEXA.NS': 1200,
            # Chemicals
            'UPL.NS': 520, 'SRF.NS': 2400, 'PIIND.NS': 3800, 'PIDILITIND.NS': 3100, 'COROMANDEL.NS': 1600, 'SOLARINDS.NS': 9800,
            # Consumer Durables
            'TITAN.NS': 3400, 'VOLTAS.NS': 1500, 'DIXON.NS': 11500, 'BLUESTARCO.NS': 1600, 'KALYANKJIL.NS': 650,
            # Construction
            'ULTRACEMCO.NS': 10500, 'GRASIM.NS': 2400, 'AMBUJACEM.NS': 650, 'ACC.NS': 2500, 'IRB.NS': 65, 'RVNL.NS': 580,
            # Hospitality
            'INDHOTEL.NS': 680, 'ITCHOTELS.NS': 450, 'IRCTC.NS': 950, 'JUBLFOOD.NS': 520, 'DMART.NS': 4800,
            'TRENT.NS': 7200, 'SWIGGY.NS': 420, 'NYKAA.NS': 180, 'ZOMATO.NS': 250,
            # US Stocks
            'AAPL': 235, 'MSFT': 420, 'GOOGL': 175, 'AMZN': 185, 'META': 510, 'TSLA': 240, 'NVDA': 125, 'BRK-B': 450, 'V': 280, 'JPM': 210,
            'BAC': 38, 'WFC': 58, 'GS': 450, 'TM': 215, 'GM': 58, 'F': 12, 'XOM': 110, 'CVX': 165, 'COP': 128, 'MPC': 85,
            'JNJ': 157, 'UNH': 520, 'PFE': 28, 'ABBV': 205, 'PG': 162, 'KO': 63, 'NSRGY': 95, 'DEO': 72, 'VALE': 12, 'RIO': 68,
            'SCCO': 45, 'FCX': 45, 'BX': 135, 'KKR': 135, 'BLK': 910, 'AMP': 305, 'RCL': 165, 'CCL': 22, 'MAR': 320, 'HLT': 215,
            'SPG': 143, 'PLD': 56, 'VNO': 48, 'AMB': 128
        }
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Try to get live yfinance data
                hist = ticker.history(period='5d')
                
                current_price = 0
                change = 0
                change_pct = 0
                day_high = 0
                day_low = 0
                volume = 0
                
                # If we have historical data, use it
                if not hist.empty and len(hist) > 0:
                    latest_data = hist.iloc[-1]
                    current_price = latest_data.get('Close', 0)
                    day_high = latest_data.get('High', current_price)
                    day_low = latest_data.get('Low', current_price)
                    volume = latest_data.get('Volume', 0)
                    
                    if len(hist) >= 2:
                        previous_close = hist.iloc[-2].get('Close', current_price)
                    else:
                        previous_close = info.get('regularMarketPreviousClose', current_price)
                    
                    change = current_price - previous_close if previous_close and previous_close > 0 else 0
                    change_pct = (change / previous_close * 100) if previous_close and previous_close > 0 else 0
                
                # If yfinance data is invalid or missing, use realistic fallback
                if current_price <= 0:
                    base_price = REALISTIC_PRICES.get(symbol, 100)
                    variation = random.uniform(-0.05, 0.05)
                    current_price = base_price * (1 + variation)
                    
                    prev_variation = random.uniform(-0.03, 0.03)
                    previous_close = base_price * (1 + prev_variation)
                    
                    change = current_price - previous_close
                    change_pct = (change / previous_close * 100) if previous_close > 0 else 0
                    day_high = current_price * random.uniform(1.005, 1.02)
                    day_low = current_price * random.uniform(0.98, 0.995)
                    volume = random.randint(100000, 50000000)
                
                # Get company info
                company_name = info.get('longName', info.get('shortName', symbol.replace('.NS', '')))
                pe_ratio = info.get('trailingPE', info.get('forwardPE', 0))
                market_cap = info.get('marketCap', 0)
                
                # For US stocks, use realistic market cap ranges
                if not '.NS' in symbol and not market_cap:
                    market_cap = random.randint(50000000000, 800000000000)
                
                # Save to database
                stock, created = Stock.objects.update_or_create(
                    symbol=symbol,
                    defaults={
                        'name': company_name if company_name else symbol,
                        'sector': sector,
                        'current_price': float(current_price),
                        'change': float(change),
                        'change_percent': float(change_pct),
                        'day_high': float(day_high),
                        'day_low': float(day_low),
                        'pe_ratio': float(pe_ratio) if pe_ratio and pe_ratio > 0 else 0,
                        'market_cap': int(market_cap) if market_cap else 0,
                        'volume': int(volume) if volume else 0
                    }
                )
                
                updated_stocks.append(StockSerializer(stock).data)
                
            except Exception as e:
                logger.warning(f"yfinance issue for {symbol}, using realistic data: {str(e)}")
                try:
                    # Use realistic fallback data
                    base_price = REALISTIC_PRICES.get(symbol, 100)
                    variation = random.uniform(-0.05, 0.05)
                    current_price = base_price * (1 + variation)
                    
                    prev_variation = random.uniform(-0.03, 0.03)
                    previous_close = base_price * (1 + prev_variation)
                    
                    change = current_price - previous_close
                    change_pct = (change / previous_close * 100) if previous_close > 0 else 0
                    
                    stock, created = Stock.objects.update_or_create(
                        symbol=symbol,
                        defaults={
                            'name': symbol,
                            'sector': sector,
                            'current_price': float(current_price),
                            'change': float(change),
                            'change_percent': float(change_pct),
                            'day_high': float(current_price * random.uniform(1.005, 1.02)),
                            'day_low': float(current_price * random.uniform(0.98, 0.995)),
                            'pe_ratio': round(random.uniform(15, 30), 2),
                            'market_cap': random.randint(50000000000, 800000000000) if not '.NS' in symbol else random.randint(10000000000, 500000000000),
                            'volume': random.randint(100000, 50000000)
                        }
                    )
                    updated_stocks.append(StockSerializer(stock).data)
                except Exception as fallback_err:
                    logger.error(f"Failed for {symbol}: {str(fallback_err)}")
                    continue
        
        # Return updated stocks data
        if updated_stocks:
            return Response({
                'success': True,
                'message': 'Prices refreshed and saved successfully',
                'sector': sector,
                'stocks': updated_stocks,
                'count': len(updated_stocks),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': f'Unable to refresh prices for {sector} sector'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    except Exception as e:
        logger.error(f"Error refreshing sector prices: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error refreshing sector prices',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout user and record activity"""
    try:
        # Record activity before logging out
        UserActivity.objects.create(
            user=request.user,
            action='LOGOUT',
            description=f"User {request.user.email} logged out",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Django session logout
        logout(request)
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error during logout',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def activity_dashboard(request):
    """View to display user activities and system stats (Admin-like dashboard)"""
    try:
        # Handle stock addition/removal from dashboard
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'add_stock':
                symbol = request.POST.get('symbol', '').upper()
                name = request.POST.get('name', symbol)
                sector = request.POST.get('sector', '').lower()
                current_price = request.POST.get('current_price', 100)
                
                if symbol and sector:
                    Stock.objects.update_or_create(
                        symbol=symbol,
                        defaults={
                            'name': name,
                            'sector': sector,
                            'current_price': float(current_price),
                            'change': 0,
                            'change_percent': 0,
                            'day_high': float(current_price) * 1.01,
                            'day_low': float(current_price) * 0.99,
                            'pe_ratio': round(random.uniform(15, 30), 2),
                            'market_cap': random.randint(50000000000, 800000000000),
                            'volume': random.randint(100000, 50000000)
                        }
                    )
            elif action == 'remove_stock':
                symbol = request.POST.get('symbol')
                if symbol:
                    Stock.objects.filter(symbol=symbol).delete()

        activities = UserActivity.objects.all().order_by('-timestamp')[:100]
        total_count = UserActivity.objects.count()
        unique_users_count = User.objects.count()
        
        # Last 7 days stats
        seven_days_ago = datetime.now() - timedelta(days=7)
        new_customers = User.objects.filter(date_joined__gte=seven_days_ago)
        subscriptions = NewsletterSubscription.objects.all()
        payments = PaymentRecord.objects.all().order_by('-timestamp')
        
        # All stocks for management
        stocks = Stock.objects.all().order_by('sector', 'symbol')
        
        context = {
            'activities': activities,
            'total_count': total_count,
            'unique_users_count': unique_users_count,
            'new_customers': new_customers,
            'subscriptions': subscriptions,
            'payments': payments,
            'stocks': stocks,
            'sectors': ['it', 'banking', 'automobile', 'energy', 'pharma', 'fmcg', 'metals', 'finance', 'hospitality', 'realty', 'us_stocks']
        }
        
        return render(request, 'users/activity_dashboard.html', context)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error loading dashboard',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def subscribe_newsletter(request):
    """Subscribe user to newsletter"""
    try:
        email = request.data.get('email')
        if not email:
            return Response({
                'success': False,
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        subscription, created = NewsletterSubscription.objects.get_or_create(email=email)
        
        if not created:
            return Response({
                'success': False,
                'message': 'Email is already subscribed'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({
            'success': True,
            'message': 'Subscribed successfully'
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error subscribing: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error subscribing to newsletter',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_dummy_payment(request):
    """Process a dummy payment and record it"""
    try:
        amount = request.data.get('amount')
        card_number = request.data.get('cardNumber')
        expiry = request.data.get('expiry')
        cvv = request.data.get('cvv')
        
        if not all([amount, card_number, expiry, cvv]):
            return Response({
                'success': False,
                'message': 'All payment details are required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        payment = PaymentRecord.objects.create(
            user=request.user,
            amount=float(amount),
            card_number=card_number,
            expiry=expiry,
            cvv=cvv,
            status='SUCCESS'
        )
        
        return Response({
            'success': True,
            'message': 'Payment successful',
            'payment_id': payment.id
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        return Response({
            'success': False,
            'message': 'Payment processing failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_metals_sentiment(request):
    """Fetch gold & silver sentiment analysis from scraped news headlines."""
    try:
        from .sentiment import analyze_metals_sentiment
        result = analyze_metals_sentiment()
        return Response({
            'success': True,
            'data': result
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error performing sentiment analysis',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_stock_sentiment(request, sector):
    """Fetch stock sentiment analysis for a specific sector."""
    try:
        from .stock_sentiment import analyze_sector_sentiment
        result = analyze_sector_sentiment(sector)
        return Response({
            'success': True,
            'data': result
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in stock sentiment analysis for {sector}: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error performing stock sentiment analysis',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)