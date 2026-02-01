from __future__ import annotations

from elasticsearch import Elasticsearch

from dbmon.settings import settings


def create_client() -> Elasticsearch:
    if settings.elastic_api_key:
        return Elasticsearch(
            settings.elastic_url,
            api_key=settings.elastic_api_key,
            verify_certs=settings.elastic_verify_certs,
        )

    if settings.elastic_user and settings.elastic_password:
        return Elasticsearch(
            settings.elastic_url,
            basic_auth=(settings.elastic_user, settings.elastic_password),
            verify_certs=settings.elastic_verify_certs,
        )

    return Elasticsearch(settings.elastic_url, verify_certs=settings.elastic_verify_certs)


def index_events(client: Elasticsearch, index_name: str, events: list[dict]) -> None:
    if not events:
        return
    operations = []
    for event in events:
        operations.append({"index": {"_index": index_name}})
        operations.append(event)
    client.bulk(operations=operations, refresh=True)
