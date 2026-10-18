# ============================================================================
# DESCRIÇÃO: Coleta automatizada de páginas Web (Web Scraping com BeautifulSoup)
# ============================================================================
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import requests
from bs4 import BeautifulSoup
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("WebScraper")

class CzechBankWebScraper:
    """
    Realiza scraping de tabelas públicas com metadados regionais e bancários tchecos.
    """
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PortfolioDataEngineeringBot/1.0"
    }

    def scrape_html_table(self, url: str) -> pd.DataFrame:
        """
        Faz o download de uma página web e extrai a primeira tabela HTML estruturada.
        """
        logger.info(f"Iniciando Web Scraping na URL: {url}")
        response = requests.get(url, headers=self.HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")

        if not table:
            logger.warning("Nenhuma tag <table> encontrada na página alvo.")
            return pd.DataFrame()

        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)

        df = pd.DataFrame(rows, columns=headers if headers and len(headers) == len(rows[0]) else None)
        logger.info(f"Web Scraping finalizado: {len(df)} linhas extraídas.")
        return df

if __name__ == "__main__":
    print("=== TESTANDO O WEB SCRAPER ===")
    scraper = CzechBankWebScraper()
    
    # Exemplo utilizando uma página de testes ou site público
    url_teste = "https://pt.wikipedia.org/wiki/República_Tcheca"
    try:
        df_resultado = scraper.scrape_html_table(url_teste)
        if not df_resultado.empty:
            print("Tabela extraída com sucesso!")
            print(df_resultado.head())
        else:
            print("O scraper executou, mas nenhuma tabela foi encontrada na URL informada.")
    except Exception as e:
        print(f"Erro ao executar o scraping de teste: {e}")