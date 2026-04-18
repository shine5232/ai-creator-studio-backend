# Import all models so Alembic can detect them
from app.models.user import User, UserQuota  # noqa: F401
from app.models.project import Project, WorkflowStep  # noqa: F401
from app.models.script import Script, Storyboard, Shot  # noqa: F401
from app.models.character import Character, CharacterPeriod  # noqa: F401
from app.models.asset import Asset  # noqa: F401
from app.models.ai_gateway import AIProvider, AIModel, APIKey  # noqa: F401
from app.models.publish import SocialAccount, PublishRecord  # noqa: F401
from app.models.knowledge import KBCase, KBElement, KBFramework, KBScriptTemplate  # noqa: F401
from app.models.analytics import ContentAnalytics, GenerationCost  # noqa: F401
