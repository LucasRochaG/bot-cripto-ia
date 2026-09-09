import ccxt
import pandas as pd
import numpy as np
import xgboost as xgb
import warnings
import os
import csv
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURAÇÕES E PARÂMETROS DE TRADING
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_xgb_multi_1h.json')
CSV_PATH = os.path.join(BASE_DIR, 'historico_sinais.csv')
FEATURES = ['Retorno_1', 'Retorno_4', 'Volatilidade_24', 'Amplitude_Candle', 'MA50_Ratio', 'MA200_Ratio', 'RSI']

API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')

# Configuração da exchange otimizada para GitHub Actions
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',
        'adjustForTimeDifference': True
    }
})

# Redireciona chamadas públicas para evitar bloqueio 451
exchange.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'

TIMEFRAME = '1h'
LIMIAR_DECISAO = 0.70
VALOR_INVESTIMENTO_USDT = 20.0
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

def inicializar_csv():
    """Garante que o arquivo historico_sinais.csv existe com o cabeçalho."""
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'timestamp_utc', 'symbol', 'preco_entrada', 'probabilidade', 
                'tipo_sinal', 'stop_loss_pct', 'stop_loss_preco', 
                'take_profit_pct', 'take_profit_preco'
            ])

def salvar_sinal_csv(data_hora, symbol, preco, prob, tipo):
    """Registra uma entrada no histórico CSV."""
    preco_stop = preco * (1 - STOP_LOSS_PCT)
    preco_alvo = preco * (1 + TAKE_PROFIT_PCT)
    
    with open(CSV_PATH, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            data_hora, symbol, f"{preco:.4f}", f"{prob:.4f}", 
            tipo, f"-{STOP_LOSS_PCT:.1%}", f"{preco_stop:.4f}", 
            f"+{TAKE_PROFIT_PCT:.1%}", f"{preco_alvo:.4f}"
        ])

def obter_top20_moedas():
    """Filtra as 20 moedas USDT com maior volume via API pública da Binance V3."""
    STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'BUSD/USDT', 'TUSD/USDT', 'FDUSD/USDT', 'USDE/USDT', 'EUR/USDT']
    try:
        tickers = exchange.public_get_ticker_24hr()
        usdt_pairs = []
        
        for t in tickers:
            symbol_raw = t['symbol']
            if symbol_raw.endswith('USDT'):
                base = symbol_raw[:-4]
                symbol = f"{base}/USDT"
                if symbol not in STABLECOINS and float(t.get('quoteVolume', 0)) > 0:
                    usdt_pairs.append({
                        'symbol': symbol,
                        'volume': float(t['quoteVolume'])
                    })
                    
        sorted_pairs = sorted(usdt_pairs, key=lambda x: x['volume'], reverse=True)
        return [pair['symbol'] for pair in sorted_pairs[:20]]
        
    except Exception as e:
        print(f"⚠️ Erro ao buscar tickers públicos, usando lista padrão: {e}")
        return [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 
            'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT'
        ]

def executar_compra_automatica(symbol, preco_atual):
    """Simula/Executa ordem de compra a mercado e exibe alvos de proteção."""
    preco_stop = preco_atual * (1 - STOP_LOSS_PCT)
    preco_alvo = preco_atual * (1 + TAKE_PROFIT_PCT)

    print(f"🛒 Registrando Sinal de Compra: {symbol} | Preço: ${preco_atual:.4f}")
    print(f"🎯 Stop Loss configurado em: ${preco_stop:.4f} (-{STOP_LOSS_PCT:.1%})")
    print(f"🎯 Take Profit configurado em: ${preco_alvo:.4f} (+{TAKE_PROFIT_PCT:.1%})")

def rodar_varredura():
    data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    print("=" * 65)
    print(f"  VARREDURA E EXECUÇÃO AUTOMÁTICA DA IA — {data_hora}")
    print("=" * 65)

    inicializar_csv()

    try:
        booster = xgb.Booster()
        booster.load_model(MODEL_PATH)
        
        top20 = obter_top20_moedas()
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
                    print(f"\n🚨 [SINAL DE COMPRA] -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Prob: {prob:.2%}")
                    salvar_sinal_csv(data_hora, symbol, preco_atual, prob, 'COMPRA')
                    executar_compra_automatica(symbol, preco_atual)
                else:
                    print(f"🟡 [NEUTRO]           -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Prob: {prob:.2%}")

            except Exception as e:
                continue

        if sinais_encontrados == 0:
            print("\nNenhum sinal de compra identificado nesta hora.")

    except Exception as e:
        print(f"❌ Erro na execução principal: {e}")

if __name__ == '__main__':
    rodar_varredura()
