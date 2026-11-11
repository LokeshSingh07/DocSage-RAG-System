import logging
from worker.celery_app import celery_app
from app.rag.ingestion import ingest
from app.core.observability import trace


logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="ingest_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)



@trace('ingest_task')
def ingest_task(self, key, tenant, doc_id, owner, groups):
    logger.info("Ingest %s (doc_id=%s, attempt=%s)", key, doc_id, self.request.retries + 1)
    
    return ingest(key, tenant, doc_id, owner, groups)