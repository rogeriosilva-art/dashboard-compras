import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title='Resumo Executivo de Compras',
    layout='wide',
    page_icon='📊',
    initial_sidebar_state='expanded',
)

# Estilização CSS Personalizada
st.markdown(
    """
    <style>
    .main { background-color: #0E1117; }
    .stMetric {
        background-color: #1E232A;
        padding: 25px 20px;
        border-radius: 14px;
        border: 1px solid #2D3748;
        box-shadow: 0 6px 12px rgba(0,0,0,0.4);
        text-align: center;
    }
    div[data-testid="stMetricValue"] {
        font-size: 36px !important;
        font-weight: bold;
        color: #00E676;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 15px !important;
        color: #A0AEC0;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .comprador-card {
        background-color: #1E232A;
        padding: 18px;
        border-radius: 12px;
        border-left: 5px solid #29B6F6;
        margin-bottom: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    .comprador-total {
        border-left: 5px solid #00E676 !important;
        background-color: #16222F !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Caminho da planilha
excel_path = 'ROGERIO (2).xlsx'


@st.cache_data(ttl=1)
def load_data(path):
  df = pd.read_excel(path)
  df.columns = [str(c).strip() for c in df.columns]

  # Mapeia a coluna Compradc (Coluna N)
  col_comp = None
  for col in df.columns:
    if 'comprad' in col.lower() or 'vendedor' in col.lower():
      col_comp = col
      break

  if col_comp:
    raw_comp = df[col_comp].astype(str).str.strip()
    df['Comprador_Clean'] = raw_comp.str.upper()
  else:
    df['Comprador_Clean'] = ''

  # ID de Pedidos / Solicitações
  col_ped = 'NumPedid' if 'NumPedid' in df.columns else df.columns[0]
  df['Pedido_ID'] = df[col_ped].astype(str).str.strip()

  col_solic = 'NumSolic' if 'NumSolic' in df.columns else df.columns[0]
  df['Solic_ID'] = df[col_solic].astype(str).str.strip()

  # Datas
  for date_col in ['DtSolic', 'DtPedido', 'DtNF']:
    if date_col in df.columns:
      df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

  if 'DtPedido' in df.columns and df['DtPedido'].notna().any():
    df['AnoMes'] = df['DtPedido'].dt.to_period('M').astype(str)
  elif 'DtSolic' in df.columns and df['DtSolic'].notna().any():
    df['AnoMes'] = df['DtSolic'].dt.to_period('M').astype(str)
  else:
    df['AnoMes'] = 'Sem Data'

  df['AnoMes'] = df['AnoMes'].fillna('Sem Data').astype(str)
  return df


df_raw = load_data(excel_path)

# --- CABEÇALHO ---
st.title('📊 Resumo Executivo de Suprimentos')
st.markdown('***')

# --- FILTRO LATERAL ---
st.sidebar.title('Filtros do Painel')

todos_meses = [str(m) for m in df_raw['AnoMes'].unique()]
meses_disponiveis = sorted(
    [m for m in todos_meses if m not in ['NaT', 'Sem Data', 'nan']]
)
opcoes_mes = ['Todos os Meses'] + meses_disponiveis

mes_selecionado = st.sidebar.selectbox('📅 Período (Ano-Mês):', opcoes_mes)

if mes_selecionado != 'Todos os Meses':
  df = df_raw[df_raw['AnoMes'] == mes_selecionado].copy()
else:
  df = df_raw.copy()

# Lead Time (Dias)
if 'DtPedido' in df.columns and 'DtSolic' in df.columns:
  df['LeadTime_Solicitacao'] = (df['DtPedido'] - df['DtSolic']).dt.days
else:
  df['LeadTime_Solicitacao'] = None

if 'DtNF' in df.columns and 'DtPedido' in df.columns:
  df['LeadTime_Entrega'] = (df['DtNF'] - df['DtPedido']).dt.days
else:
  df['LeadTime_Entrega'] = None

# KPIs Principais do Topo
total_solicitacoes = df['Solic_ID'].nunique()

# Pedidos emitidos
df_pedidos_gerados = df[
    ~df['Pedido_ID'].str.lower().str.contains('aguardando|sem pedido|nan', na=False)
]
total_pedidos = df_pedidos_gerados['Pedido_ID'].nunique()

lt_solic_avg = (
    df['LeadTime_Solicitacao'].dropna().mean()
    if 'LeadTime_Solicitacao' in df
    and not df['LeadTime_Solicitacao'].dropna().empty
    else 0.0
)
lt_entrega_avg = (
    df['LeadTime_Entrega'].dropna().mean()
    if 'LeadTime_Entrega' in df and not df['LeadTime_Entrega'].dropna().empty
    else 0.0
)

# --- CARDS KPIS GERAIS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
  st.metric('Total Solicitações', f'{total_solicitacoes:,}'.replace(',', '.'))
with col2:
  st.metric('Total de Pedidos', f'{total_pedidos:,}'.replace(',', '.'))
with col3:
  st.metric('Lead Time Solicitação', f'{lt_solic_avg:.1f} dias')
with col4:
  st.metric('Lead Time Entrega', f'{lt_entrega_avg:.1f} dias')

st.markdown('<br><br>', unsafe_allow_html=True)

# --- ACOMPANHAMENTO DE COMPRADORES ---
st.subheader('👤 Acompanhamento de Pedidos por Comprador')

compradores_alvo = [
    'EVELYN',
    'ALAN',
    'CAMILA',
    'VIVIANE',
    'JHULIA',
    'MARIANA',
]

# Pedidos por Comprador Alvo
pedidos_por_comprador = {}
for comp in compradores_alvo:
  sub_df = df_pedidos_gerados[
      df_pedidos_gerados['Comprador_Clean'].str.contains(comp, na=False)
  ]
  qtd = sub_df['Pedido_ID'].nunique() if not sub_df.empty else 0
  pedidos_por_comprador[comp] = qtd

# Soma total de pedidos de todos os compradores da equipe
total_pedidos_compradores = sum(pedidos_por_comprador.values())

# Exibição dos Compradores em Cards
cols_comp = st.columns(len(compradores_alvo))

for i, comp in enumerate(compradores_alvo):
  with cols_comp[i]:
    qtd = pedidos_por_comprador[comp]
    st.markdown(
        f"""
        <div class="comprador-card">
            <span style="color: #A0AEC0; font-size: 13px; font-weight: bold;">{comp}</span><br>
            <span style="color: #29B6F6; font-size: 28px; font-weight: bold;">{qtd}</span>
            <span style="color: #718096; font-size: 12px;"> pedidos</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<br>', unsafe_allow_html=True)

# Card de Total Consolidado dos Compradores
col_total, _ = st.columns([1.8, 2.2])
with col_total:
  st.markdown(
      f"""
      <div class="comprador-card comprador-total">
          <span style="color: #00E676; font-size: 14px; font-weight: bold;">📦 TOTAL DE PEDIDOS - EQUIPE DE COMPRAS</span><br>
          <span style="color: #00E676; font-size: 34px; font-weight: bold;">{total_pedidos_compradores:,}</span>
          <span style="color: #A0AEC0; font-size: 14px;"> pedidos gerados pelos compradores</span>
      </div>
      """.replace(',', '.'),
      unsafe_allow_html=True,
  )