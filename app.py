import re
from datetime import datetime
from zoneinfo import ZoneInfo

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

COLABORADORES = ["Rodrigo dos Santos Soares", "Eliz Brugiolo", "Gustavo Silva", "Nathálie Carvalho", "Enrico Hilário", "Yara Neto", "Vivian Guimarães", "Dhayane Gomes", "Jennifer Benvindo"]
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

COLUNAS_PLANILHA = ["Colaborador", "Data", "Motivo", "Empresa", "Início", "Fim", "Total", "Observação", "Protocolo"]


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

        return sorted(set(empresas))  # remove duplicados

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
def obter_valores_planilha(cache_buster=0):
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
        "Protocolo": "Protocolo",
        "Protocólo": "Protocolo",
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
        "protocolo": ultima.get("Protocolo", ""),
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


def iniciar_tarefa(sheet, df, colaborador, empresa, motivo, observacao="", protocolo="", horario=None):
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
        protocolo,
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
        str(ultima.get("Protocolo", "")),
    )
    return True


def ultimo_protocolo_colaborador(df, colaborador, empresa=None, motivo=None):
    if df.empty or "Protocolo" not in df.columns:
        return ""

    registros = df[df["Colaborador"].astype(str).str.strip() == colaborador]
    registros = registros[registros["Protocolo"].astype(str).str.strip() != ""]

    # Filtra pela mesma empresa + motivo, mesmo que existam outras tarefas mais recentes
    if empresa is not None:
        registros = registros[registros["Empresa"].astype(str).str.strip() == str(empresa).strip()]
    if motivo is not None:
        registros = registros[registros["Motivo"].astype(str).str.strip() == str(motivo).strip()]

    if registros.empty:
        return ""

    registros = registros.sort_values(by="__linha")
    return str(registros.iloc[-1]["Protocolo"]).strip()


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
    exibicao = filtrados[
        ["Colaborador", "Data", "Motivo", "Empresa", "Início", "Fim", "Total", "Observação", "Protocolo"]
    ].copy()
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
if "protocolo_antes_intervalo" not in st.session_state:
    st.session_state.protocolo_antes_intervalo = None

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


@st.dialog("Número do protocolo")
def dialog_protocolo(empresa_sel, motivo_sel, obs_sel, protocolo_anterior="", eh_suporte=False):
    st.write(f"**Empresa:** {empresa_sel}")
    st.write(f"**Motivo:** {motivo_sel}")

    def _iniciar_com(prot):
        iniciar_tarefa(
            sheet,
            df_registros,
            colaborador,
            empresa_sel,
            motivo_sel,
            obs_sel,
            prot,
        )
        st.session_state.ultimo_inicio = hora_str(agora())
        st.session_state.em_intervalo = False
        st.session_state.empresa_antes_intervalo = None
        st.session_state.motivo_antes_intervalo = None
        st.session_state.obs_antes_intervalo = None
        st.session_state.protocolo_antes_intervalo = None
        st.toast("✅ Tarefa iniciada com sucesso!")
        invalidar_cache_e_rerun()

    if protocolo_anterior:
        st.success(f"📋 Seu último protocolo **para esta empresa e motivo** foi **{protocolo_anterior}**.")
        st.write("Quer continuar com o mesmo protocolo anterior?")
        if st.button(
            f"🔁 Sim, continuar com {protocolo_anterior}",
            use_container_width=True,
            type="primary",
        ):
            _iniciar_com(protocolo_anterior)
        st.caption("— ou informe um novo protocolo abaixo —")

    if eh_suporte:
        st.info("ℹ️ Para tarefas de **Suporte**, o protocolo é **opcional**. Você pode informar um protocolo ou iniciar sem ele.")

    protocolo = st.text_input(
        "Número do protocolo da tarefa" + (" (opcional)" if eh_suporte else ""),
        key="input_protocolo_dialog",
        placeholder="Ex: 123456",
    )

    if eh_suporte:
        col_ok, col_sem, col_cancelar = st.columns(3)
        with col_ok:
            tipo_botao = "secondary" if protocolo_anterior else "primary"
            if st.button("✅ OK e iniciar", use_container_width=True, type=tipo_botao):
                _iniciar_com(protocolo.strip())
        with col_sem:
            if st.button("▶ Iniciar sem protocolo", use_container_width=True):
                _iniciar_com("")
        with col_cancelar:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()
    else:
        col_ok, col_cancelar = st.columns(2)
        with col_ok:
            tipo_botao = "secondary" if protocolo_anterior else "primary"
            if st.button("✅ OK e iniciar", use_container_width=True, type=tipo_botao):
                if not protocolo.strip():
                    if protocolo_anterior:
                        st.warning("Digite um novo protocolo ou use o botão do protocolo anterior.")
                    else:
                        st.warning("Digite o número do protocolo antes de continuar.")
                else:
                    _iniciar_com(protocolo.strip())
        with col_cancelar:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()


if not EMPRESAS:
    st.warning(
        "Nenhuma empresa carregada. Verifique se o arquivo **empresas.txt** "
        "existe na mesma pasta do aplicativo e não está vazio."
    )

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
    observacao = montar_observacao_suporte(suporte_para)

st.divider()

ativa = procurar_tarefa_ativa(df_registros, colaborador)

if st.session_state.em_intervalo and not ativa:
    empresa_anterior = st.session_state.empresa_antes_intervalo or ""
    st.warning(
        f"☕ **Você está em intervalo!**\n\n"
        f"Última empresa trabalhada: **{empresa_anterior}**\n\n"
        f"Clique em **🔁 Voltei** quando retornar."
    )

if ativa:
    st.session_state.em_intervalo = False
    st.session_state.empresa_antes_intervalo = None
    st.session_state.motivo_antes_intervalo = None
    st.session_state.obs_antes_intervalo = None
    st.session_state.protocolo_antes_intervalo = None

    st.markdown("### 🔴 EM EXECUÇÃO")
    st.success(f"Empresa: {ativa['empresa']}")
    st.info(f"Motivo: {ativa['motivo']}")
    if ativa.get("protocolo"):
        st.info(f"Protocolo: {ativa['protocolo']}")
    if ativa["observacao"]:
        st.write(f"Observação: {ativa['observacao']}")
    st.markdown(f"## ⏱️ {calcular_tempo_decorrido(ativa['inicio'])}")
    st.caption(f"Iniciado às {ativa['inicio']}")
elif not st.session_state.em_intervalo:
    st.markdown("### ⚪ Nenhuma tarefa em execução")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶ Iniciar Trabalho", use_container_width=True):
        if not empresa or not str(empresa).strip():
            st.warning("Selecione a empresa antes de iniciar.")
        elif motivo_escolhido == "Outros" and not observacao.strip():
            st.warning("Descreva o motivo em Outros.")
        elif motivo_escolhido == "Suporte" and (not suporte_para.strip() or not tipo_suporte.strip()):
            st.warning("Preencha para quem é o suporte e o motivo do suporte.")
        else:
            # Abre a caixinha pedindo o protocolo. A tarefa só inicia após o OK.
            protocolo_anterior = ultimo_protocolo_colaborador(
                df_registros,
                colaborador,
                empresa=str(empresa).strip(),
                motivo=motivo_final,
            )
            dialog_protocolo(
                str(empresa).strip(),
                motivo_final,
                observacao.strip(),
                protocolo_anterior,
                eh_suporte=(motivo_escolhido == "Suporte"),
            )

with col2:
    if st.button("☕ Intervalo", use_container_width=True):
        tarefa_finalizada = finalizar_tarefa_ativa(sheet, df_registros, colaborador)
        if tarefa_finalizada:
            st.session_state.em_intervalo = True
            st.session_state.empresa_antes_intervalo = tarefa_finalizada.get("empresa", "")
            st.session_state.motivo_antes_intervalo = tarefa_finalizada.get("motivo", "")
            st.session_state.obs_antes_intervalo = tarefa_finalizada.get("observacao", "")
            st.session_state.protocolo_antes_intervalo = tarefa_finalizada.get("protocolo", "")
            st.toast("☕ Bom intervalo! Clique em Voltei quando retornar.")
        else:
            st.warning("Nenhuma tarefa ativa para finalizar.")
        invalidar_cache_e_rerun()

    if st.button("🔁 Voltei", use_container_width=True):
        if st.session_state.em_intervalo and st.session_state.empresa_antes_intervalo:
            empresa_retomar = st.session_state.empresa_antes_intervalo
            motivo_retomar = st.session_state.motivo_antes_intervalo or ""
            obs_retomar = st.session_state.obs_antes_intervalo or ""
            prot_retomar = st.session_state.protocolo_antes_intervalo or ""
            iniciar_tarefa(sheet, df_registros, colaborador, empresa_retomar, motivo_retomar, obs_retomar, prot_retomar)
            st.session_state.em_intervalo = False
            st.session_state.empresa_antes_intervalo = None
            st.session_state.motivo_antes_intervalo = None
            st.session_state.obs_antes_intervalo = None
            st.session_state.protocolo_antes_intervalo = None
            st.toast(f"✅ Retomando: {empresa_retomar}")
        else:
            if voltar_ultima_tarefa(sheet, df_registros, colaborador):
                st.toast("✅ Última tarefa retomada.")
            else:
                st.warning("Nenhuma tarefa anterior encontrada.")
        invalidar_cache_e_rerun()

with col3:
    if st.button("⛔ Finalizar", use_container_width=True):
        if finalizar_tarefa_ativa(sheet, df_registros, colaborador):
            st.session_state.em_intervalo = False
            st.session_state.empresa_antes_intervalo = None
            st.session_state.protocolo_antes_intervalo = None
            st.toast("✅ Tarefa finalizada.")
        else:
            st.warning("Nenhuma tarefa ativa para finalizar.")
        invalidar_cache_e_rerun()

st.divider()
st.subheader("Últimos registros")

registros_colab = df_registros[
    df_registros["Colaborador"].astype(str).str.strip() == colaborador
].copy()

f1, f2, f3, f4 = st.columns([1, 1, 2, 2])

with f1:
    data_inicio = st.date_input(
        "Data inicial",
        value=None,
        format="DD/MM/YYYY"
    )

with f2:
    data_fim = st.date_input(
        "Data final",
        value=None,
        format="DD/MM/YYYY"
    )

with f3:
    empresas_registradas = ["Todas"] + opcoes_empresas_do_df(registros_colab)

    empresa_filtro = st.selectbox(
        "Filtrar empresa",
        empresas_registradas
    )

with f4:
    st.caption(
        "Os filtros abaixo afetam o total de horas e os registros exibidos."
    )

filtrados = aplicar_filtro_periodo(
    registros_colab,
    data_inicio,
    data_fim
)

if empresa_filtro != "Todas":
    filtrados = filtrados[
        filtrados["Empresa"].astype(str).str.strip() == empresa_filtro
    ]

filtrados = filtrados.sort_values(
    by=["Data", "Início", "__linha"],
    ascending=[False, False, False],
    na_position="last"
)

# MÉTRICAS
k1, k2 = st.columns(2)

k1.metric(
    "Tempo total filtrado",
    total_geral_formatado(filtrados)
)

k2.metric(
    "Empresas no filtro",
    len(opcoes_empresas_do_df(filtrados))
)

if filtrados.empty:
    st.info("Sem registros para este colaborador no período selecionado.")

else:
    exibicao = filtrados[
        [
            "__linha",
            "Data",
            "Motivo",
            "Empresa",
            "Início",
            "Fim",
            "Total",
            "Observação",
            "Protocolo",
        ]
    ].copy()

    edited = st.data_editor(
        exibicao,
        hide_index=True,
        use_container_width=True,
        disabled=["__linha", "Total"],
        column_config={
            "__linha": st.column_config.NumberColumn(
                "Linha",
                disabled=True
            ),

            "Data": st.column_config.TextColumn(
                "Data"
            ),

            "Motivo": st.column_config.TextColumn(
                "Motivo"
            ),

            "Empresa": st.column_config.TextColumn(
                "Empresa",
                width="large"
            ),

            "Início": st.column_config.TextColumn(
                "Início"
            ),

            "Fim": st.column_config.TextColumn(
                "Fim"
            ),

            "Total": st.column_config.TextColumn(
                "Total",
                disabled=True
            ),

            "Observação": st.column_config.TextColumn(
                "Observação"
            ),

            "Protocolo": st.column_config.TextColumn(
                "Protocolo"
            ),
        },
        key="editor_registros",
    )

    c1, c2 = st.columns([1, 1])

    with c1:
        csv_bytes = gerar_csv_download(
            edited.drop(columns=["__linha"], errors="ignore")
        )

        st.download_button(
            "📥 Baixar CSV",
            data=csv_bytes,
            file_name=f"registros_{colaborador.lower()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c2:
        if st.button(
            "💾 Salvar alterações na planilha",
            use_container_width=True
        ):

            erros = []
            atualizacoes = []

            for _, row in edited.iterrows():

                linha = int(row["__linha"])

                data_txt = str(row["Data"]).strip()
                inicio_txt = str(row["Início"]).strip()
                fim_txt = str(row["Fim"]).strip()
                motivo_txt = str(row["Motivo"]).strip()
                empresa_txt = str(row["Empresa"]).strip()

                observacao_txt = str(
                    row.get("Observação", "")
                ).strip()

                protocolo_txt = str(
                    row.get("Protocolo", "")
                ).strip()

                if not validar_data_br(data_txt):
                    erros.append(
                        f"Linha {linha}: data inválida. Use DD/MM/AAAA."
                    )

                if not validar_hora(inicio_txt):
                    erros.append(
                        f"Linha {linha}: início inválido. Use HH:MM:SS."
                    )

                if not validar_hora(fim_txt):
                    erros.append(
                        f"Linha {linha}: fim inválido. Use HH:MM:SS."
                    )

                total_txt = (
                    calcular_total(inicio_txt, fim_txt)
                    if inicio_txt and fim_txt
                    else ""
                )

                atualizacoes.extend([
                    {"range": f"B{linha}", "values": [[data_txt]]},
                    {"range": f"C{linha}", "values": [[motivo_txt]]},
                    {"range": f"D{linha}", "values": [[empresa_txt]]},
                    {"range": f"E{linha}", "values": [[inicio_txt]]},
                    {"range": f"F{linha}", "values": [[fim_txt]]},
                    {"range": f"G{linha}", "values": [[total_txt]]},
                    {"range": f"H{linha}", "values": [[observacao_txt]]},
                    {"range": f"I{linha}", "values": [[protocolo_txt]]},
                ])

            if erros:
                for erro in erros:
                    st.error(erro)

            else:
                sheet.batch_update(
                    atualizacoes,
                    value_input_option="USER_ENTERED"
                )

                st.toast(
                    "✅ Alterações salvas na planilha com sucesso."
                )

                invalidar_cache_e_rerun()
