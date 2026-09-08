import ccxt
import pandas as pd
import numpy as np
import xgboost as xgb
import warnings
import os
from datetime import datetime

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_xgb_multi_1h.json')
FEATURES = ['Retorno_1', 'Retorno_4', 'Volatilidade_24', 'Amplitude_Candle', 'MA50_Ratio', 'MA200_Ratio', 'RSI']

# Usa a Binance sem nenhum tipo de bloqueio ou proxy no GitHub
exchange = ccxt.binance({'enableRateLimit': True})
TIMEFRAME = '1h'
LIMIAR_DECISAO = 0.70

def obter_top20_moedas():
    """Filtra as 20 moedas USDT com maior volume na Binance."""
    STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'BUSD/USDT', 'TUSD/USDT', 'FDUSD/USDT', 'USDE/USDT', 'EUR/USDT']
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = {
            k: v for k, v in tickers.items() 
            if k.endswith('/USDT') and k not in STABLECOINS and v.get('quoteVolume') is not None
        }
        sorted_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1]['quoteVolume'], reverse=True)
        return [pair[0] for pair in sorted_pairs[:20]]
    except Exception as e:
        print(f"⚠️ Erro ao buscar tickers: {e}")
        return [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 
            'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT', 
            'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT', 'APT/USDT', 'FIL/USDT', 
            'ETC/USDT', 'XMR/USDT', 'ALGO/USDT', 'KAS/USDT', 'UNI/USDT'
        ]

def rodar_varredura():
    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S UTC')
    print("=" * 65)
    print(f"  VARREDURA DO TOP 20 DA IA (GITHUB ACTIONS) — {data_hora}")
    print("=" * 65)
    
    try:
        booster = xgb.Booster()
        booster.load_model(MODEL_PATH)
        
        top20 = obter_top20_moedas()
        print(f"🔍 Moedas analisadas: {', '.join([s.split('/')[0] for s in top20])}\n")
        
        sinais_encontrados = 0

        for symbol in top20:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=250)
                if not ohlcv or len(ohlcv) < 200:
                    continue

                df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = df[col].astype(float)

                df['Retorno_1'] = df['Close'].pct_change(1)
                df['Retorno_4'] = df['Close'].pct_change(4)
                df['Volatilidade_24'] = df['Retorno_1'].rolling(24).std()
                df['Amplitude_Candle'] = (df['High'] - df['Low']) / df['Close']
                df['MA50_Ratio'] = df['Close'] / df['Close'].rolling(50).mean()
                df['MA200_Ratio'] = df['Close'] / df['Close'].rolling(200).mean()

                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / loss)))

                candle_fechado = df.iloc[-2]
                preco_atual = float(df.iloc[-1]['Close'])
                ma200 = float(candle_fechado['MA200_Ratio'])

                linha_fechada = candle_fechado[FEATURES].values.astype(np.float32)
                dmatrix_input = xgb.DMatrix(np.array([linha_fechada]), feature_names=FEATURES)

                prob = float(booster.predict(dmatrix_input)[0])

                if prob >= LIMIAR_DECISAO and ma200 > 1.0:
                    sinais_encontrados += 1
                    print(f"🚨 [COMPRA ENCONTRADA] -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Probabilidade: {prob:.2%}")
                else:
                    print(f"🟡 [NEUTRO]           -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Probabilidade: {prob:.2%}")

            except Exception as e:
                continue

        if sinais_encontrados == 0:
            print("\nNenhum sinal de compra identificado nesta hora.")

    except Exception as e:
        print(f"❌ Erro na execução principal: {e}")

if __name__ == '__main__':
    rodar_varredura()
