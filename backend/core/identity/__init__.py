from backend.core.configs import settings
from backend.core.identity.base import IdentityProvider
from backend.core.identity.firebase import FirebaseIdentityProvider

PROVIDERS: dict[str, type[IdentityProvider]] = {
    "firebase": FirebaseIdentityProvider,
}

provider: IdentityProvider = PROVIDERS[settings.AUTH_PROVIDER]()
