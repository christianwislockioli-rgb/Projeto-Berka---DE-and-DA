# ============================================================================
# DESCRIÇÃO: Conector NoSQL (MongoDB) para logs de eventos e JSONs brutos
# ============================================================================
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
from pymongo import MongoClient
from src.utils.logger import get_logger

logger = get_logger("MongoConnector")

class MongoConnector:
    def __init__(self, db_name: str = "berka_nosql_logs"):
        user = os.getenv("MONGO_INITDB_ROOT_USERNAME", "mongo_admin")
        password = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "changeme_mongo_password")
        host = os.getenv("MONGO_HOST", "localhost")
        port = os.getenv("MONGO_PORT", "27017")
        
        self.uri = f"mongodb://{user}:{password}@{host}:{port}/"
        self.db_name = db_name

    def insert_audit_event(self, collection_name: str, payload: Dict[str, Any]) -> None:
        """
        Insere um documento JSON semiestruturado (ex: log de ingestão ou evento de API).
        """
        try:
            with MongoClient(self.uri, serverSelectionTimeoutMS=3000) as client:
                db = client[self.db_name]
                payload[" ingested_at_utc"] = datetime.now(timezone.utc).isoformat()
                db[collection_name].insert_one(payload)
                logger.info(f"Documento JSON registrado na coleção NoSQL '{collection_name}'.")
        except Exception as e:
            logger.warning(f"MongoDB offline ou inacessível no ambiente atual: {e}")

    def insert_many_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> None:
        """Insere múltiplos documentos JSON de uma só vez."""
        if not documents:
            return
        try:
            with MongoClient(self.uri, serverSelectionTimeoutMS=3000) as client:
                db = client[self.db_name]
                db[collection_name].insert_many(documents)
                logger.info(f"{len(documents)} documentos inseridos em '{collection_name}'.")
        except Exception as e:
            logger.warning(f"Falha ao inserir lote no MongoDB: {e}")