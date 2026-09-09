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
        # Configuração da exchange
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot', 'adjustForTimeDifference': True}
        })

        # Redirecionamento da URL pública para evitar bloqueio 451
        exchange.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'

        # Teste 1: Testar resposta do servidor da Binance
        status = exchange.fetch_status()
        print(f"✅ Status do Servidor Binance: {status.get('status', 'OK').upper()}")

        # Teste 2: Tentar autenticar e buscar saldo de USDT
        balance = exchange.fetch_balance()
        saldo_usdt = balance['total'].get('USDT', 0.0)
        
        print("\n🎉 CONEXÃO BEM-SUCEDIDA!")
        print(f"💰 Saldo total em USDT na conta: ${saldo_usdt:.2f}")
        print("=" * 60)

    except ccxt.AuthenticationError:
        print("\n❌ ERRO DE AUTENTICAÇÃO: As chaves cadastradas no GitHub Secrets são inválidas ou foram digitadas incorretamente.")
    except ccxt.PermissionDenied:
        print("\n❌ ERRO DE PERMISSÃO: A sua API Key da Binance não tem permissão de leitura/trading Spot ativada.")
    except Exception as e:
        print(f"\n❌ ERRO AO CONECTAR: {e}")
