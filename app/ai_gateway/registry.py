from app.ai_gateway.base import BaseAdapter, ServiceType


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseAdapter] = {}
        self._aliases: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter):
        self._providers[adapter.provider_name] = adapter
        # Register aliases if adapter defines them
        for alias in getattr(adapter, "aliases", []):
            self._aliases[alias] = adapter

    def get_provider(self, name: str) -> BaseAdapter | None:
        return self._providers.get(name) or self._aliases.get(name)

    def list_providers(self) -> list[BaseAdapter]:
        return list(self._providers.values())

    def get_providers_for_service(self, service_type: ServiceType) -> list[BaseAdapter]:
        return [p for p in self._providers.values() if p.supports(service_type)]


registry = ProviderRegistry()
