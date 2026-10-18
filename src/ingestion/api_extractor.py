# ============================================================================
# DESCRIÇÃO: Extrator de APIs REST com paginação (Banco Mundial & Câmbio CZK)
# ============================================================================
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import requests
from typing import List, Dict, Any
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("APIExtractor")

class MacroEconomicAPIExtractor:
    """
    Extrai indicadores macroeconômicos da República Tcheca (World Bank REST API)
    com suporte a paginação automática para enriquecer a análise do Banco Berka.
    """
    BASE_URL = "https://api.worldbank.org/v2/country/CZE/indicator"

    def fetch_paginated_indicator(self, indicator_code: str = "FP.CPI.TOTL.ZG", date_range: str = "1993:1998") -> pd.DataFrame:
        """
        Extrai série histórica paginada filtrando pelo período histórico do Banco Berka (1993-1998).
        """
        page = 1
        total_pages = 1
        records: List[Dict[str, Any]] = []

        while page <= total_pages:
            url = f"{self.BASE_URL}/{indicator_code}?format=json&date={date_range}&per_page=50&page={page}"
            logger.info(f"Consumindo API REST (Página {page}/{total_pages}): {url}")
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list) or len(data) < 2 or not data[1]:
                break

            metadata = data[0]
            total_pages = int(metadata.get("pages", 1))

            for item in data[1]:
                records.append({
                    "country_iso": item.get("countryiso3code"),
                    "indicator_id": item.get("indicator", {}).get("id"),
                    "indicator_name": item.get("indicator", {}).get("value"),
                    "reference_year": int(item.get("date", 0)),
                    "value": item.get("value")
                })
            page += 1

        df = pd.DataFrame(records)
        logger.info(f"Extração via API concluída: {len(df)} registros coletados para o período {date_range}.")
        return df

if __name__ == "__main__":
    extractor = MacroEconomicAPIExtractor()
    df_macro = extractor.fetch_paginated_indicator()
    print(df_macro.head())