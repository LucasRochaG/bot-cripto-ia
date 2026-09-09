import ccxt
import os

API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')

print("=" * 60)
print("🔍 TESTANDO CONEXÃO E AUTENTICAÇÃO COM A BINANCE")
print("=" * 60)

if not API_KEY or not SECRET_KEY:
    print("❌ ERRO: As chaves BINANCE_API_KEY e/ou BINANCE_SECRET_KEY não foram encontradas no GitHub Secrets.")
else:
    print("✅ Chaves de API encontradas nas variáveis de ambiente.")
    
    try:
        # Configuração da exchange com redirecionamento de endpoints
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True
            }
        })

        # Redireciona chamadas públicas e privadas para evitar restrições de IP nos EUA
        exchange.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'
        
        # Teste de conexão usando dados de mercado públicos (verificação sem bloqueio 451)
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Conexão com a Binance estabelecida! BTC/USDT Preço Atual: ${ticker['last']:.2f}")

        # Tentativa de consulta de saldo autenticada
        try:
            balance = exchange.private_get_account()
            saldos = {item['asset']: float(item['free']) for item in balance['balances'] if float(item['free']) > 0}
            saldo_usdt = saldos.get('USDT', 0.0)
            
            print("\n🎉 AUTENTICAÇÃO E SALDO BEM-SUCEDIDOS!")
            print(f"💵 Saldo disponível em USDT: ${saldo_usdt:.2f}")
            if saldos:
                print(f"📦 Outros ativos encontrados: {saldos}")
        except Exception as auth_err:
            print("\n⚠️ Dados públicos ok, mas o envio de ordens privadas no GitHub Actions sofre bloqueio de IP dos EUA.")
            print(f"Detalhe: {auth_err}")

        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERRO AO CONECTAR: {e}")
