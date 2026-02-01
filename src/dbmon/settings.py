from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    elastic_url: str = "http://localhost:9200"
    elastic_user: Optional[str] = None
    elastic_password: Optional[str] = None
    elastic_api_key: Optional[str] = None
    elastic_verify_certs: bool = False
    elastic_index_metrics: str = "dbmon-metrics"
    elastic_index_alerts: str = "dbmon-alerts"

    sql_connection_string: Optional[str] = None
    sql_instance: str = "unknown"
    host_name: str = "localhost"

    collector_mode: str = "mock"  # mock | live
    sample_input_path: str = "sample_inputs/sample_metrics.jsonl"
    alert_rules_path: str = "alerting/rules.yaml"

    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000

    # Ollama AI configuration
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    use_ai_analysis: bool = True


settings = Settings()
