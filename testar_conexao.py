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
        # Configuração da exchange para contornar restrições geográficas de servidor
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True
            }
        })

        # Redireciona chamadas públicas e de dados
        exchange.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'

        # Teste de Autenticação Real: Busca do Saldo na Conta Spot
        balance = exchange.fetch_balance()
        
        # Filtrar apenas ativos com saldo maior que zero para conferência
        saldos_positivos = {k: v['free'] for k, v in balance['total'].items() if v['free'] > 0}
        saldo_usdt = balance['total'].get('USDT', 0.0)
        
        print("\n🎉 CONEXÃO E AUTENTICAÇÃO BEM-SUCEDIDAS!")
        print(f"💵 Saldo disponível em USDT: ${saldo_usdt:.2f}")
        
        if saldos_positivos:
            print(f"📦 Outros ativos encontrados no saldo: {saldos_positivos}")
            
        print("=" * 60)

    except ccxt.AuthenticationError:
        print("\n❌ ERRO DE AUTENTICAÇÃO: As chaves cadastradas no GitHub Secrets são inválidas ou foram digitadas incorretamente.")
    except ccxt.PermissionDenied:
        print("\n❌ ERRO DE PERMISSÃO: A sua API Key da Binance não tem permissão de leitura ou trading Spot ativada nas configurações da corretora.")
    except Exception as e:
        print(f"\n❌ ERRO AO CONECTAR: {e}")
