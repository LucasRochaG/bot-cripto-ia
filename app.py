import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Dashboard IA Cripto Bot", page_icon="🤖", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'historico_sinais.csv')

st.title("🤖 Dashboard de Performance — Bot Crypto XGBoost")
st.markdown("---")

if not os.path.exists(CSV_PATH):
    st.info("ℹ️ Nenhum registro encontrado ainda. O histórico de sinais será exibido assim que o robô realizar a primeira varredura.")
    st.stop()

df = pd.read_csv(CSV_PATH)

if df.empty or 'status' not in df.columns:
    st.warning("⚠️ O arquivo de histórico está criado, mas ainda não possui registros de negociação.")
    st.stop()

# ==========================================
# CÁLCULO DE MÉTRICAS / KPIs
# ==========================================
tot_sinais = len(df)
operacoes_fechadas = df[df['status'].isin(['TAKE_PROFIT', 'STOP_LOSS'])]
operacoes_abertas = df[df['status'] == 'ABERTO']

vitorias = len(df[df['status'] == 'TAKE_PROFIT'])
derrotas = len(df[df['status'] == 'STOP_LOSS'])
tot_encerradas = len(operacoes_fechadas)

win_rate = (vitorias / tot_encerradas * 100) if tot_encerradas > 0 else 0.0

if not operacoes_fechadas.empty and 'pnl_usdt' in operacoes_fechadas.columns:
    operacoes_fechadas['pnl_usdt_num'] = operacoes_fechadas['pnl_usdt'].astype(str).str.replace('$', '').str.replace('%', '').astype(float)
    pnl_total_usdt = operacoes_fechadas['pnl_usdt_num'].sum()
else:
    pnl_total_usdt = 0.0

# ==========================================
# PAINEL DE METRICAS
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total de Sinais", tot_sinais)
col2.metric("Posições Abertas", len(operacoes_abertas))
col3.metric("Operações Fechadas", tot_encerradas)
col4.metric("Win Rate (%)", f"{win_rate:.1f}%")
col5.metric("PnL Total (USDT)", f"${pnl_total_usdt:+.2f}")

st.markdown("---")

# ==========================================
# GRÁFICOS E TABELAS
# ==========================================
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("📈 Curva de Patrimônio Accumulada (PnL)")
    if not operacoes_fechadas.empty and 'pnl_usdt_num' in operacoes_fechadas.columns:
        operacoes_fechadas['pnl_acumulado'] = operacoes_fechadas['pnl_usdt_num'].cumsum()
        fig = px.line(operacoes_fechadas, x='timestamp_fechamento', y='pnl_acumulado', 
                      title="Evolução do Lucro (USDT)", labels={'pnl_acumulado': 'USDT', 'timestamp_fechamento': 'Data'},
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Aguardando fechamento da primeira operação para gerar o gráfico.")

with c2:
    st.subheader("📊 Distribuição de Resultados")
    if tot_encerradas > 0:
        df_pie = pd.DataFrame({
            'Resultado': ['Take Profit', 'Stop Loss'],
            'Quantidade': [vitorias, derrotas]
        })
        fig_pie = px.pie(df_pie, values='Quantidade', names='Resultado', color='Resultado',
                         color_discrete_map={'Take Profit': '#00CC96', 'Stop Loss': '#EF553B'})
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.caption("Aguardando encerramento de posições.")

# ==========================================
# DETALHAMENTO DE OPERAÇÕES
# ==========================================
tab1, tab2 = st.columns(2)

with tab1:
    st.subheader("🔓 Posições em Aberto")
    st.dataframe(operacoes_abertas[['timestamp_abertura', 'symbol', 'preco_entrada', 'probabilidade', 'stop_loss_preco', 'take_profit_preco']], use_container_width=True)

with tab2:
    st.subheader("📜 Histórico de Fechamentos")
    st.dataframe(operacoes_fechadas[['timestamp_fechamento', 'symbol', 'preco_entrada', 'preco_saida', 'status', 'pnl_pct', 'pnl_usdt']], use_container_width=True)
