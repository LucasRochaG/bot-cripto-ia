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
        # Configuração restrita apenas para API V3 Spot (sem rotas SAPI)
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'fetchBalance': {'type': 'spot'},  # Força o uso da API V3 Spot
                'adjustForTimeDifference': True
            }
        })

        # Redireciona chamadas públicas
        exchange.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'

        # Busca o saldo usando exclusivamente o endpoint v3/account
        balance = exchange.private_get_account()
        
        # Filtra e localiza os saldos de USDT e de outros ativos
        saldos = {item['asset']: float(item['free']) for item in balance['balances'] if float(item['free']) > 0}
        saldo_usdt = saldos.get('USDT', 0.0)
        
        print("\n🎉 CONEXÃO E AUTENTICAÇÃO BEM-SUCEDIDAS!")
        print(f"💵 Saldo disponível em USDT: ${saldo_usdt:.2f}")
        
        if saldos:
            print(f"📦 Outros ativos encontrados no saldo: {saldos}")
            
        print("=" * 60)

    except ccxt.AuthenticationError:
        print("\n❌ ERRO DE AUTENTICAÇÃO: As chaves cadastradas no GitHub Secrets são inválidas ou foram digitadas incorretamente.")
    except ccxt.PermissionDenied:
        print("\n❌ ERRO DE PERMISSÃO: A sua API Key da Binance não tem permissão de leitura ou trading Spot ativada.")
    except Exception as e:
        print(f"\n❌ ERRO AO CONECTAR: {e}")
