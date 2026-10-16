# 中文导读：
# Alembic 迁移环境：导入业务模型注册元数据，分别支持离线生成 SQL 和在线执行迁移
# 迁移前应确认目标数据库

from alembic import context

from app.db.session import Base, engine
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.faq import models as faq_models  # noqa: F401
from app.modules.feedback import models as feedback_models  # noqa: F401
from app.modules.knowledge.models import KnowledgeBase  # noqa: F401
from app.modules.oidc import models as oidc_models  # noqa: F401
from app.modules.tenant import models as tenant_models  # noqa: F401

target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=engine.url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
