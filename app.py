import io
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Controle de Tempo Online", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1UO8OsNELTVsK6l4Gp7vow7ccPwn7uBHu-y_wYgwb8hE/edit?gid=0#gid=0"
SCOPES = [
"https://www.googleapis.com/auth/spreadsheets",
"https://www.googleapis.com/auth/drive",
]

COLABORADORES = ["Rodrigo", "Eliz", "Gustavo", "Nathálie", "Enrico", "Yara", "Vivian", "Dhayane", "Jennifer"]
ADMIN_USUARIOS = ["Administrador"]
SENHA_PADRAO = "fisco121*"
MOTIVOS_BASE = [
"81 - Apuração de crédito para Estimativa – Não Previdenciária",
"88 - Apuração de Crédito - Não Previdenciária",
"144 - Retificação de arquivos - Não Previdenciária",
"227 - Associação - Não Previdenciária",
"348 - Revisão dos SPEDs retificados",
"400 - Conferência de crédito para Estimativa – Não Previdenciária",
"402 - Conferência de Crédito - Não Previdenciária",
"497 - Diversos",
"619 - Ajuste na Apuração de crédito - Não Previdenciária",
"620 - Conferência de arquivos retificados - Não Previdenciária",
"621 - Ajuste nos arquivos retificados - Não Previdenciária",
"629 - Retificação DCTF - Não Previdenciária",
"634 - Retirar CND e verificar Situação Fiscal – Não Previdenciária",
"771 - Conferências extras",
"773 - Apuração de Crédito - PERSE",
"774 - Conferência de Crédito - PERSE",
"827 - Reunião Apuração Não Previdenciária",
"903 - Validação do carregamento do crédito",
"973 - Transmissão de arquivos",
"Suporte",
"Outros",
]
TIPOS_SUPORTE = [
"80 - Reclassificação",
"81 - Apuração de crédito para Estimativa – Não Previdenciária",
"88 - Apuração de Crédito - Não Previdenciária",
"144 - Retificação de arquivos - Não Previdenciária",
"227 - Associação - Não Previdenciária",
"348 - Revisão dos SPEDs retificados",
"400 - Conferência de crédito para Estimativa – Não Previdenciária",
"402 - Conferência de Crédito - Não Previdenciária",
"497 - Diversos",
"619 - Ajuste na Apuração de crédito - Não Previdenciária",
"620 - Conferência de arquivos retificados - Não Previdenciária",
"621 - Ajuste nos arquivos retificados - Não Previdenciária",
"629 - Retificação DCTF - Não Previdenciária",
"634 - Retirar CND e verificar Situação Fiscal – Não Previdenciária",
"771 - Conferências extras",
"773 - Apuração de Crédito - PERSE",
"774 - Conferência de Crédito - PERSE",
"827 - Reunião Apuração Não Previdenciária",
"903 - Validação do carregamento do crédito",
"973 - Transmissão de arquivos",
"Outros",
]

COLUNAS_PLANILHA = ["Colaborador", "Data", "Motivo", "Empresa", "Início", "Fim", "Total", "Observação"]



import re

def carregar_empresas():
try:
with open("empresas.txt", "r", encoding="utf-8") as f:
linhas = f.readlines()

empresas = []

for linha in linhas:
linha = linha.strip()
if not linha:
continue

# remove múltiplos espaços
linha = re.sub(r"\s+", " ", linha)

# separa código
partes = linha.split(" ", 1)

if len(partes) > 1:
codigo = partes[0]
resto = partes[1]

# remove traços duplicados
resto = re.sub(r"-+", "-", resto)

# separa CNPJ
match = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", resto)

if match:
cnpj = match.group()
nome = resto.replace(cnpj, "").strip()

# remove traços extras no nome
nome = nome.strip(" -")

empresas.append(f"{codigo} - {nome} - {cnpj}")
else:
nome = resto.strip(" -")
empresas.append(f"{codigo} - {nome}")
else:
empresas.append(linha)

return sorted(set(empresas)) # remove duplicados

except FileNotFoundError:
return []



EMPRESAS = carregar_empresas()


@st.cache_resource
def conectar_planilha():
info = dict(st.secrets["gcp_service_account"])
creds = Credentials.from_service_account_info(info, scopes=SCOPES)
client = gspread.authorize(creds)
return client.open_by_url(SHEET_URL).sheet1


def agora():
from zoneinfo import ZoneInfo
return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def data_str(dt):
return dt.strftime("%d/%m/%Y")


def hora_str(dt):
return dt.strftime("%H:%M:%S")


def login_ok(nome, senha):
return nome in (COLABORADORES + ADMIN_USUARIOS) and senha == SENHA_PADRAO


def usuario_eh_admin(nome):
return nome in ADMIN_USUARIOS


def calcular_total(inicio_texto, fim_texto):
try:
inicio = datetime.strptime(inicio_texto, "%H:%M:%S")
fim = datetime.strptime(fim_texto, "%H:%M:%S")
delta = fim - inicio
if delta.total_seconds() < 0:
return ""
total_segundos = int(delta.total_seconds())
horas = total_segundos // 3600
minutos = (total_segundos % 3600) // 60
segundos = total_segundos % 60
return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
except Exception:
return ""


def tempo_para_segundos(valor):
try:
texto = str(valor).strip()
if not texto:
return 0
partes = texto.split(":")
if len(partes) != 3:
return 0
horas, minutos, segundos = [int(p) for p in partes]
return horas * 3600 + minutos * 60 + segundos
except Exception:
return 0


def formatar_segundos(total_segundos):
total_segundos = int(total_segundos or 0)
horas = total_segundos // 3600
minutos = (total_segundos % 3600) // 60
segundos = total_segundos % 60
return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


@st.cache_data(ttl=20)
def obter_valores_planilha(_cache_buster=0):
sheet = conectar_planilha()
return sheet.get_all_values()


def invalidar_cache_e_rerun():
obter_valores_planilha.clear()
st.session_state.cache_buster = st.session_state.get("cache_buster", 0) + 1
st.rerun()


def dataframe_registros(sheet, cache_buster=0):
valores = obter_valores_planilha(cache_buster)
if not valores:
return pd.DataFrame(columns=["__linha"] + COLUNAS_PLANILHA)

mapa_colunas = {
"Motivo/tarefa em execução": "Motivo",
"Motivo/Tarefa em execução": "Motivo",
"Motivo/tarefa": "Motivo",
"Início": "Início",
"Inicio": "Início",
}
header = [mapa_colunas.get(col.strip(), col.strip()) for col in valores[0]]

linhas = []
for idx, row in enumerate(valores[1:], start=2):
row_preenchida = row + [""] * (len(header) - len(row))
registro = {col: row_preenchida[i] if i < len(row_preenchida) else "" for i, col in enumerate(header)}
for col in COLUNAS_PLANILHA:
registro.setdefault(col, "")
registro["__linha"] = idx
linhas.append(registro)

df = pd.DataFrame(linhas)
cols = ["__linha"] + [c for c in COLUNAS_PLANILHA if c in df.columns]
return df[cols]


def preparar_df_com_totais(df):
trabalho = df.copy()
if "Total" not in trabalho.columns:
trabalho["Total"] = ""
trabalho["__total_segundos"] = trabalho["Total"].apply(tempo_para_segundos)
return trabalho


def resumo_por_empresa(df):
if df.empty:
return pd.DataFrame(columns=["Empresa", "Total gasto", "Registros"])
trabalho = preparar_df_com_totais(df)
agrupado = (
trabalho.groupby("Empresa", dropna=False, as_index=False)
.agg(total_segundos=("__total_segundos", "sum"), registros=("Empresa", "size"))
)
agrupado["Empresa"] = agrupado["Empresa"].fillna("").astype(str)
agrupado["Total gasto"] = agrupado["total_segundos"].apply(formatar_segundos)
agrupado["Registros"] = agrupado["registros"].astype(int)
return agrupado.sort_values(by=["total_segundos", "Empresa"], ascending=[False, True])[
["Empresa", "Total gasto", "Registros"]
]


def resumo_por_usuario(df):
if df.empty:
return pd.DataFrame(columns=["Usuário", "Total gasto", "Registros"])
trabalho = preparar_df_com_totais(df)
agrupado = (
trabalho.groupby("Colaborador", dropna=False, as_index=False)
.agg(total_segundos=("__total_segundos", "sum"), registros=("Colaborador", "size"))
)
agrupado["Usuário"] = agrupado["Colaborador"].fillna("").astype(str)
agrupado["Total gasto"] = agrupado["total_segundos"].apply(formatar_segundos)
agrupado["Registros"] = agrupado["registros"].astype(int)
return agrupado.sort_values(by=["total_segundos", "Usuário"], ascending=[False, True])[
["Usuário", "Total gasto", "Registros"]
]


def total_geral_formatado(df):
if df.empty:
return "00:00:00"
trabalho = preparar_df_com_totais(df)
return formatar_segundos(trabalho["__total_segundos"].sum())


def opcoes_empresas_do_df(df):
if df.empty or "Empresa" not in df.columns:
return []
return sorted({str(x).strip() for x in df["Empresa"].fillna("") if str(x).strip()})


def opcoes_usuarios_do_df(df):
if df.empty or "Colaborador" not in df.columns:
return []
return sorted({str(x).strip() for x in df["Colaborador"].fillna("") if str(x).strip()})


def procurar_tarefa_ativa(df, colaborador):
if df.empty:
return None
ativos = df[(df["Colaborador"].astype(str).str.strip() == colaborador) & (df["Fim"].astype(str).str.strip() == "")]
if ativos.empty:
return None
ultima = ativos.iloc[-1].to_dict()
return {
"linha": int(ultima["__linha"]),
"colaborador": ultima.get("Colaborador", ""),
"data": ultima.get("Data", ""),
"motivo": ultima.get("Motivo", ""),
"empresa": ultima.get("Empresa", ""),
"inicio": ultima.get("Início", ""),
"fim": ultima.get("Fim", ""),
"total": ultima.get("Total", ""),
"observacao": ultima.get("Observação", ""),
}


def finalizar_tarefa_ativa(sheet, df, colaborador, horario=None):
ativa = procurar_tarefa_ativa(df, colaborador)
if not ativa:
return None
fim = hora_str(horario or agora())
total = calcular_total(ativa["inicio"], fim)
atualizacoes = [
{"range": f"F{ativa['linha']}", "values": [[fim]]},
{"range": f"G{ativa['linha']}", "values": [[total]]},
]
sheet.batch_update(atualizacoes, value_input_option="USER_ENTERED")
ativa["fim"] = fim
ativa["total"] = total
return ativa


def iniciar_tarefa(sheet, df, colaborador, empresa, motivo, observacao="", horario=None):
momento = horario or agora()
finalizar_tarefa_ativa(sheet, df, colaborador, momento)
nova_linha = [
colaborador,
data_str(momento),
motivo,
empresa,
hora_str(momento),
"",
"",
observacao,
]
sheet.append_row(nova_linha, value_input_option="USER_ENTERED")


def voltar_ultima_tarefa(sheet, df, colaborador):
if df.empty:
return False
registros = df[df["Colaborador"].astype(str).str.strip() == colaborador]
registros = registros[(registros["Motivo"].astype(str).str.strip() != "") & (registros["Empresa"].astype(str).str.strip() != "")]
if registros.empty:
return False
ultima = registros.iloc[-1]
iniciar_tarefa(
sheet,
df,
colaborador,
str(ultima.get("Empresa", "")),
str(ultima.get("Motivo", "")),
str(ultima.get("Observação", "")),
)
return True


def calcular_tempo_decorrido(inicio_texto):
try:
inicio_dt = datetime.strptime(inicio_texto, "%H:%M:%S")
atual = agora()
inicio_hoje = atual.replace(hour=inicio_dt.hour, minute=inicio_dt.minute, second=inicio_dt.second, microsecond=0)
delta = atual - inicio_hoje
if delta.total_seconds() < 0:
return "00:00:00"
total_segundos = int(delta.total_seconds())
return formatar_segundos(total_segundos)
except Exception:
return "--:--:--"


def validar_data_br(texto):
try:
if not str(texto).strip():
return True
datetime.strptime(str(texto).strip(), "%d/%m/%Y")
return True
except Exception:
return False


def validar_hora(texto):
try:
if not str(texto).strip():
return True
datetime.strptime(str(texto).strip(), "%H:%M:%S")
return True
except Exception:
return False


def aplicar_filtro_periodo(df, data_inicio, data_fim):
if df.empty:
return df
trabalho = df.copy()
trabalho["__data_dt"] = pd.to_datetime(trabalho["Data"], format="%d/%m/%Y", errors="coerce")
if data_inicio:
trabalho = trabalho[trabalho["__data_dt"] >= pd.Timestamp(data_inicio)]
if data_fim:
trabalho = trabalho[trabalho["__data_dt"] <= pd.Timestamp(data_fim)]
return trabalho.drop(columns=["__data_dt"], errors="ignore")


def gerar_csv_download(df):
export_df = df.drop(columns=["__linha"], errors="ignore").copy()
return export_df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")


def montar_motivo_suporte(tipo_suporte):
return (tipo_suporte or "").strip() if tipo_suporte else "Suporte"


def montar_observacao_suporte(suporte_para):
destino = (suporte_para or "").strip()
if destino:
return f"Suporte {destino}"
return "Suporte"


def montar_motivo_final(motivo_base, suporte_para=None, tipo_suporte=None):
if motivo_base == "Suporte":
return montar_motivo_suporte(tipo_suporte)
return (motivo_base or "").strip()


def render_tela_admin(df_registros):
st.subheader("Painel do Administrador")
st.caption("Acesso somente para leitura, filtros e relatórios.")

f1, f2, f3, f4 = st.columns([1, 1, 1.4, 1.2])
with f1:
data_inicio = st.date_input("Data inicial", value=None, format="DD/MM/YYYY", key="admin_data_inicio")
with f2:
data_fim = st.date_input("Data final", value=None, format="DD/MM/YYYY", key="admin_data_fim")
with f3:
empresas = ["Todas"] + opcoes_empresas_do_df(df_registros)
empresa_filtro = st.selectbox("Empresa", empresas, key="admin_empresa")
with f4:
usuarios = ["Todos"] + opcoes_usuarios_do_df(df_registros)
usuario_filtro = st.selectbox("Usuário", usuarios, key="admin_usuario")

filtrados = aplicar_filtro_periodo(df_registros, data_inicio, data_fim)
if empresa_filtro != "Todas":
filtrados = filtrados[filtrados["Empresa"].astype(str).str.strip() == empresa_filtro]
if usuario_filtro != "Todos":
filtrados = filtrados[filtrados["Colaborador"].astype(str).str.strip() == usuario_filtro]

k1, k2, k3 = st.columns(3)
k1.metric("Total de horas filtradas", total_geral_formatado(filtrados))
k2.metric("Empresas no filtro", len(opcoes_empresas_do_df(filtrados)))
k3.metric("Usuários no filtro", len(opcoes_usuarios_do_df(filtrados)))

r1, r2 = st.columns(2)
with r1:
st.markdown("#### Total por empresa")
resumo_empresa = resumo_por_empresa(filtrados)
st.dataframe(resumo_empresa, hide_index=True, use_container_width=True)
st.download_button(
"📥 Baixar relatório por empresa",
data=gerar_csv_download(resumo_empresa),
file_name="relatorio_por_empresa.csv",
mime="text/csv",
use_container_width=True,
)
with r2:
st.markdown("#### Total por usuário")
resumo_usuario = resumo_por_usuario(filtrados)
st.dataframe(resumo_usuario, hide_index=True, use_container_width=True)
st.download_button(
"📥 Baixar relatório por usuário",
data=gerar_csv_download(resumo_usuario),
file_name="relatorio_por_usuario.csv",
mime="text/csv",
use_container_width=True,
)

st.markdown("#### Registros filtrados")
exibicao = filtrados[["Colaborador", "Data", "Motivo", "Empresa", "Início", "Fim", "Total", "Observação"]].copy()
exibicao = exibicao.sort_values(by=["Data", "Início"], ascending=[False, False], na_position="last")
if exibicao.empty:
st.info("Nenhum registro encontrado para os filtros selecionados.")
else:
st.dataframe(exibicao, hide_index=True, use_container_width=True)
st.download_button(
"📥 Baixar registros filtrados",
data=gerar_csv_download(exibicao),
file_name="registros_filtrados_admin.csv",
mime="text/csv",
use_container_width=True,
)


sheet = None
st.title("Controle de Tempo Online")

if "usuario_logado" not in st.session_state:
st.session_state.usuario_logado = None
if "ultimo_inicio" not in st.session_state:
st.session_state.ultimo_inicio = None
if "em_intervalo" not in st.session_state:
st.session_state.em_intervalo = False
if "empresa_antes_intervalo" not in st.session_state:
st.session_state.empresa_antes_intervalo = None
if "motivo_antes_intervalo" not in st.session_state:
st.session_state.motivo_antes_intervalo = None
if "obs_antes_intervalo" not in st.session_state:
st.session_state.obs_antes_intervalo = None

try:
sheet = conectar_planilha()
except Exception as e:
st.error(f"Erro ao conectar na planilha: {e}")
st.stop()

with st.sidebar:
st.subheader("Acesso")
if st.session_state.usuario_logado:
perfil = "Administrador" if usuario_eh_admin(st.session_state.usuario_logado) else "Colaborador"
st.success(f"Logado como {st.session_state.usuario_logado}")
st.caption(f"Perfil: {perfil}")
if st.button("Sair"):
st.session_state.usuario_logado = None
invalidar_cache_e_rerun()
else:
# Formulário de login (Enter funciona aqui)
with st.form("login_form"):
nome_login = st.selectbox("Nome", COLABORADORES + ADMIN_USUARIOS, key="login_nome")
senha_login = st.text_input("Senha", type="password", key="login_senha")
entrar = st.form_submit_button("Entrar")

if entrar:
if login_ok(nome_login, senha_login):
st.session_state.usuario_logado = nome_login
invalidar_cache_e_rerun()
else:
st.error("Nome ou senha inválidos.")

if not st.session_state.usuario_logado:
st.info("Faça login para usar o sistema.")
st.stop()

cache_buster = st.session_state.get("cache_buster", 0)
df_registros = dataframe_registros(sheet, cache_buster)
colaborador = st.session_state.usuario_logado
e_admin = usuario_eh_admin(colaborador)

if e_admin:
render_tela_admin(df_registros)
st.stop()

empresa = st.selectbox("Empresa", EMPRESAS)
motivo_escolhido = st.selectbox(
"Motivo",
MOTIVOS_BASE,
help="💡 Digite qualquer parte do nome ou o número para filtrar — ex: 'Apuração', '629', 'retif'",
)

observacao = ""
suporte_para = ""
tipo_suporte = ""

if motivo_escolhido == "Outros":
observacao = st.text_input("Descreva o motivo")
elif motivo_escolhido == "Suporte":
suporte_para_opcao = st.selectbox("Para quem é o suporte?", COLABORADORES + ["Outros"])
if suporte_para_opcao == "Outros":
suporte_para = st.text_input("Digite para quem é o suporte")
else:
suporte_para = suporte_para_opcao

tipo_suporte_opcao = st.selectbox("Qual é o motivo do suporte?", TIPOS_SUPORTE)
if tipo_suporte_opcao == "Outros":
tipo_suporte = st.text_input("Digite o motivo do suporte")
else:
tipo_suporte = tipo_suporte_opcao

motivo_final = montar_motivo_final(motivo_escolhido, suporte_para, tipo_suporte)
if motivo_escolhido == "Suporte":
observacao = montar_observacao_suport
