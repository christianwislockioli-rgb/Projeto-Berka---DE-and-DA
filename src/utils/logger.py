# ============================================================================
# DESCRIÇÃO: Configuração centralizada de logs estruturados para o pipeline
# ============================================================================
import logging
import sys
from pathlib import Path

def get_logger(name: str, log_file: str = "pipeline_execution.log") -> logging.Logger:
    """
    Cria e retorna um logger padronizado que escreve no terminal e em arquivo.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s | [%(levelname)s] | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Handler para saída no console/terminal (Databricks & Local)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Handler para arquivo local (se o sistema de arquivos permitir escrita)
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_dir / log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            # Em clusters restritos do Databricks, mantém apenas o console_handler
            pass

    return logger