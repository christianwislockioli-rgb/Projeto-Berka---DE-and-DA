# ============================================================================
# SCRIPT GERADOR DOS RELATÓRIOS AUTOMÁTICOS (PASTA reports/)
# ============================================================================
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path para padronizar as importações
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("EDAReportGenerator")

def gerar_relatorios_html_eda(df_pandas: pd.DataFrame, pasta_destino: str = "reports") -> None:
    """
    Gera os diagnósticos automatizados do YData Profiling
    e do Sweetviz na pasta reports/.
    """
    output_dir = Path(pasta_destino)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Amostragem de segurança caso a tabela tenha mais de 50.000 linhas
    if len(df_pandas) > 50000:
        df_sample = df_pandas.sample(n=50000, random_state=42)
        logger.info("Amostragem de 50.000 linhas aplicada para otimizar a geração.")
    else:
        df_sample = df_pandas.copy()

    # 1. Relatório YData Profiling
    try:
        from ydata_profiling import ProfileReport
        caminho_ydata = output_dir / "ydata_profiling_report.html"
        logger.info("Gerando relatório YData Profiling...")
        profile = ProfileReport(
            df_sample,
            title="Raio-X Automatizado - Banco Berka (YData Profiling)",
            minimal=True,
            explorative=True
        )
        profile.to_file(caminho_ydata)
        logger.info(f"Sucesso: Relatório YData gerado em '{caminho_ydata}'")
    except Exception as e:
        logger.error(f"Aviso ao gerar YData Profiling: {e}")

    # 2. Relatório Sweetviz
    try:
        import sweetviz as sv
        caminho_sweetviz = output_dir / "sweetviz_report.html"
        logger.info("Gerando relatório Sweetviz...")
        relatorio_sv = sv.analyze([df_sample, "Base Banco Berka"])
        relatorio_sv.show_html(filepath=str(caminho_sweetviz), open_browser=False)
        logger.info(f"Sucesso: Relatório Sweetviz gerado em '{caminho_sweetviz}'")
    except Exception as e:
        logger.error(f"Aviso ao gerar Sweetviz: {e}")

if __name__ == "__main__":
    print("=== INICIANDO GERAÇÃO DE RELATÓRIOS HTML (EDA) ===")
    
    # Caminho de exemplo para ler um arquivo .asc/.csv local do dataset Berka
    caminho_arquivo = Path("data/raw/loan.asc") # Ajuste para o arquivo desejado (ex: account.asc)
    
    if caminho_arquivo.exists():
        df_alvo = pd.read_csv(caminho_arquivo, sep=";", low_memory=False)
        print(f"Arquivo carregado: {caminho_arquivo} | Linhas: {len(df_alvo)}")
        gerar_relatorios_html_eda(df_alvo, pasta_destino="reports")
    else:
        print(f"Arquivo não encontrado em '{caminho_arquivo}'. Verifique o caminho ou crie um DataFrame de teste.")