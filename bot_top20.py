import ccxt
import pandas as pd
import numpy as np
import xgboost as xgb
import warnings
import os
import csv
import requests
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

# Instância CCXT apenas para tickers de volume (rotas públicas spot)
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot', 'adjustForTimeDifference': True}
})
exchange.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'

TIMEFRAME = '1h'
LIMIAR_DECISAO = 0.70
VALOR_INVESTIMENTO_USDT = 20.0
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

CSV_HEADERS = [
    'id', 'timestamp_abertura', 'symbol', 'preco_entrada', 'probabilidade', 
    'stop_loss_preco', 'take_profit_preco', 'status', 
    'timestamp_fechamento', 'preco_saida', 'pnl_pct', 'pnl_usdt'
]

# ==========================================
# GESTÃO DE HISTÓRICO E POSIÇÕES (CSV)
# ==========================================
def inicializar_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

def auditar_posicoes_abertas():
    if not os.path.exists(CSV_PATH):
        return

    df_historico = pd.read_csv(CSV_PATH)
    if df_historico.empty or 'status' not in df_historico.columns:
        return

    posicoes_abertas = df_historico[df_historico['status'] == 'ABERTO']
    if posicoes_abertas.empty:
        return

    print("\n🔍 AUDITANDO POSIÇÕES EM ABERTO NO HISTÓRICO...")
    atualizou = False

    for idx, row in posicoes_abertas.iterrows():
        symbol = row['symbol']
        preco_entrada = float(row['preco_entrada'])
        stop_loss = float(row['stop_loss_preco'])
        take_profit = float(row['take_profit_preco'])

        try:
            # Requisição direta para cotação atual (evita erro 451)
            pair_slug = symbol.replace('/', '')
            r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={pair_slug}", timeout=10)
            preco_atual = float(r.json()['price'])
            
            status_novo = None
            preco_saida = None

            if preco_atual >= take_profit:
                status_novo = 'TAKE_PROFIT'
                preco_saida = take_profit
            elif preco_atual <= stop_loss:
                status_novo = 'STOP_LOSS'
                preco_saida = stop_loss

            if status_novo:
                data_fechamento = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                pnl_pct = ((preco_saida - preco_entrada) / preco_entrada) * 100
                pnl_usdt = (pnl_pct / 100) * VALOR_INVESTIMENTO_USDT

                df_historico.loc[idx, 'status'] = status_novo
                df_historico.loc[idx, 'timestamp_fechamento'] = data_fechamento
                df_historico.loc[idx, 'preco_saida'] = f"{preco_saida:.4f}"
                df_historico.loc[idx, 'pnl_pct'] = f"{pnl_pct:.2f}%"
                df_historico.loc[idx, 'pnl_usdt'] = f"{pnl_usdt:.2f}"
                atualizou = True

                emoji = "🎯" if status_novo == 'TAKE_PROFIT' else "🛑"
                print(f"{emoji} POSIÇÃO ENCERRADA: {symbol} | Resultado: {status_novo} ({pnl_pct:+.2f}%) | Preço de Saída: ${preco_saida:.4f}")

        except Exception as e:
            print(f"⚠️ Não foi possível verificar cotação atual para {symbol}: {e}")

    if atualizou:
        df_historico.to_csv(CSV_PATH, index=False)

def registrar_nova_posicao(data_hora, symbol, preco, prob):
    preco_stop = preco * (1 - STOP_LOSS_PCT)
    preco_alvo = preco * (1 + TAKE_PROFIT_PCT)
    posicao_id = f"{symbol.split('/')[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    nova_linha = [
        posicao_id, data_hora, symbol, f"{preco:.4f}", f"{prob:.4f}",
        f"{preco_stop:.4f}", f"{preco_alvo:.4f}", 'ABERTO',
        '', '', '', ''
    ]

    with open(CSV_PATH, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(nova_linha)

# ==========================================
# FILTROS DE MERCADO E DADOS
# ==========================================
def verificar_tendencia_btc():
    try:
        url = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=250"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not isinstance(data, list):
            return True

        df_btc = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteAssetVolume', 'NumberOfTrades', 'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore'])
        df_btc['Close'] = df_btc['Close'].astype(float)
        df_btc['MA200'] = df_btc['Close'].rolling(200).mean()
        
        ultimo_fechamento = float(df_btc.iloc[-2]['Close'])
        ma200 = float(df_btc.iloc[-2]['MA200'])

        em_alta = ultimo_fechamento > ma200
        status_txt = "TENDÊNCIA DE ALTA 🟢" if em_alta else "TENDÊNCIA DE BAIXA 🔴 (Entradas Bloqueadas)"
        print(f"📊 Filtro Macro BTC/USDT: Preço ${ultimo_fechamento:.2f} | MM200 ${ma200:.2f} -> {status_txt}")
        return em_alta
    except Exception as e:
        print(f"⚠️ Falha ao checar tendência do BTC: {e}. Prosseguindo por padrão...")
        return True

def obter_top20_moedas():
    STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'BUSD/USDT', 'TUSD/USDT', 'FDUSD/USDT', 'USDE/USDT', 'EUR/USDT']
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=10)
        tickers = r.json()
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
        print(f"⚠️ Erro ao buscar tickers: {e}")
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT']

# ==========================================
# EXECUÇÃO PRINCIPAL DO BOT
# ==========================================
def rodar_varredura():
    data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    print("=" * 65)
    print(f"  VARREDURA E EXECUÇÃO AUTOMÁTICA DA IA — {data_hora}")
    print("=" * 65)

    inicializar_csv()
    auditar_posicoes_abertas()

    btc_favoravel = verificar_tendencia_btc()

    try:
        booster = xgb.Booster()
        booster.load_model(MODEL_PATH)
        
        top20 = obter_top20_moedas()
        print(f"\n🔎 Analisando o Top {len(top20)} ativos do mercado...")
        sinais_encontrados = 0

        for symbol in top20:
            try:
                pair_slug = symbol.replace('/', '')
                url = f"https://data-api.binance.vision/api/v3/klines?symbol={pair_slug}&interval={TIMEFRAME}&limit=250"
                response = requests.get(url, timeout=10)
                ohlcv = response.json()

                if not isinstance(ohlcv, list) or len(ohlcv) < 200:
                    continue

                df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteAssetVolume', 'NumberOfTrades', 'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore'])
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
                    if btc_favoravel:
                        print(f"🚨 [SINAL DE COMPRA] -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Prob: {prob:.2%}")
                        registrar_nova_posicao(data_hora, symbol, preco_atual, prob)
                    else:
                        print(f"⚠️ [IGNORADO/FILTRO BTC] -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Prob: {prob:.2%}")
                else:
                    print(f"🟡 [NEUTRO]           -> {symbol:<10} | Preço: ${preco_atual:<10.4f} | Prob: {prob:.2%}")

            except Exception as e:
                print(f"⚠️ Erro ao processar {symbol}: {e}")
                continue

        if sinais_encontrados == 0:
            print("\n🏁 Varredura concluída: Nenhum ativo atingiu o limiar de alta necessário nesta rodada.")

    except Exception as e:
        print(f"❌ Erro na execução principal: {e}")

if __name__ == '__main__':
    rodar_varredura()
