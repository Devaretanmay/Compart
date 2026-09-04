"""Provider-Neutral Contract Registry & Migration Specs Catalog."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RewriteRule:
    pattern: str
    replacement: str
    file_extensions: List[str]
    description: str
    is_regex: bool = True


@dataclass
class ProviderMigration:
    from_version: str
    to_version: str
    changelog_url: str
    description: str
    old_spec_path: Optional[str] = None
    new_spec_path: Optional[str] = None
    breaking_changes_count: int = 1
    rewrites: List[RewriteRule] = field(default_factory=list)


@dataclass
class ProviderSpec:
    name: str
    display_name: str
    package_name: str
    docs_url: str
    migrations: Dict[str, ProviderMigration] = field(default_factory=dict)
    openapi_spec_url: Optional[str] = None


class ProviderRegistry:
    """Central registry for API providers, contract specifications, and migrations."""

    def __init__(self):
        self._providers: Dict[str, ProviderSpec] = {}
        self._load_builtins()

    def register(self, provider: ProviderSpec):
        """Register a new provider specification."""
        self._providers[provider.name.lower()] = provider
        self._providers[provider.package_name.lower()] = provider

    def get(self, name_or_package: str) -> Optional[ProviderSpec]:
        """Lookup provider by name or package identifier."""
        return self._providers.get(name_or_package.lower())

    def list_providers(self) -> List[ProviderSpec]:
        """List all registered unique providers."""
        seen = set()
        unique = []
        for p in self._providers.values():
            if p.name not in seen:
                seen.add(p.name)
                unique.append(p)
        return unique

    def _load_builtins(self):
        stripe_spec = ProviderSpec(
            name="stripe",
            display_name="Stripe Node SDK",
            package_name="stripe",
            docs_url="https://docs.stripe.com/api",
        )
        stripe_spec.migrations["11.0.0->13.0.0"] = ProviderMigration(
            from_version="11.18.0",
            to_version="13.0.0",
            changelog_url="https://github.com/stripe/stripe-node/wiki/Migration-guide-for-v13",
            description="Stripe Node SDK v11 to v13 migration.",
            old_spec_path="trials/fixtures/calcom_stripe/specs/stripe_v11.json",
            new_spec_path="trials/fixtures/calcom_stripe/specs/stripe_v13.json",
            rewrites=[
                RewriteRule(
                    pattern=r'apiVersion:\s*"2022-11-15"',
                    replacement='apiVersion: "2024-06-20"',
                    file_extensions=[".ts", ".tsx", ".js", ".jsx"],
                    description="Update Stripe apiVersion to 2024-06-20 (required by v13+)",
                ),
                RewriteRule(
                    pattern=r',\s*typescript:\s*true',
                    replacement='',
                    file_extensions=[".ts", ".tsx", ".js", ".jsx"],
                    description="Remove deprecated typescript constructor flag (native in v13)",
                ),
                RewriteRule(
                    pattern=r'constructEvent\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(process\.env\.\w+)\s*\)',
                    replacement=r'constructEvent(\1, \2 as string, \3 as string)',
                    file_extensions=[".ts", ".tsx"],
                    description="Explicit string cast for constructEvent (v13 type tightening)",
                ),
                RewriteRule(
                    pattern=r'new Stripe\(process\.env\.(\w+),',
                    replacement=r'new Stripe(process.env.\1 as string,',
                    file_extensions=[".ts", ".tsx"],
                    description="Add as string cast to Stripe constructor key (v13 type safety)",
                ),
                RewriteRule(
                    pattern=r'"stripe":\s*"\^11\.\d+\.\d+"',
                    replacement='"stripe": "^13.0.0"',
                    file_extensions=[".json"],
                    description="Bump stripe package version to ^13.0.0",
                ),
            ],
        )
        stripe_spec.migrations["21.0.0->22.0.0"] = ProviderMigration(
            from_version="11.18.0",
            to_version="22.0.0",
            changelog_url="https://github.com/stripe/stripe-node/wiki/Migration-guide-for-v22",
            description="Stripe Node SDK v22 drift: amount field string requirement.",
            old_spec_path="trials/fixtures/taxonomy_stripe/specs/stripe_v21.json",
            new_spec_path="trials/fixtures/taxonomy_stripe/specs/stripe_v22.json",
        )
        self.register(stripe_spec)

        openai_spec = ProviderSpec(
            name="openai",
            display_name="OpenAI Node SDK",
            package_name="openai",
            docs_url="https://platform.openai.com/docs/api-reference",
        )
        openai_spec.migrations["3.0.0->4.0.0"] = ProviderMigration(
            from_version="3.3.0",
            to_version="4.0.0",
            changelog_url="https://github.com/openai/openai-node/discussions/217",
            description="OpenAI Node SDK v3 to v4 rewrite: createChatCompletion -> chat.completions.create.",
            old_spec_path="trials/fixtures/langchainjs_openai/specs/openai_v3.json",
            new_spec_path="trials/fixtures/langchainjs_openai/specs/openai_v4.json",
            rewrites=[
                RewriteRule(
                    pattern=r'createChatCompletion\(',
                    replacement='chat.completions.create(',
                    file_extensions=[".ts", ".tsx", ".js", ".jsx", ".py"],
                    description="Rename createChatCompletion to chat.completions.create (v4 API)",
                ),
                RewriteRule(
                    pattern=r'new Configuration\(\{',
                    replacement='new OpenAI({',
                    file_extensions=[".ts", ".tsx", ".js", ".jsx"],
                    description="Replace Configuration constructor with OpenAI client (v4)",
                ),
            ],
        )
        self.register(openai_spec)

        anthropic_spec = ProviderSpec(
            name="anthropic",
            display_name="Anthropic SDK",
            package_name="@anthropic-ai/sdk",
            docs_url="https://docs.anthropic.com/en/api/getting-started",
        )
        anthropic_spec.migrations["0.4.0->0.5.0"] = ProviderMigration(
            from_version="0.4.0",
            to_version="0.5.0",
            changelog_url="https://docs.anthropic.com/en/api/messages",
            description="Anthropic Messages API shift: completions.create -> messages.create.",
            rewrites=[
                RewriteRule(
                    pattern=r'completions\.create\(',
                    replacement='messages.create(',
                    file_extensions=[".ts", ".tsx", ".js", ".jsx", ".py"],
                    description="Rename completions.create to messages.create (Anthropic Messages API)",
                ),
            ],
        )
        self.register(anthropic_spec)

        twilio_spec = ProviderSpec(
            name="twilio",
            display_name="Twilio Node Helper",
            package_name="twilio",
            docs_url="https://www.twilio.com/docs/libraries/node",
        )
        self.register(twilio_spec)

        resend_spec = ProviderSpec(
            name="resend",
            display_name="Resend Email SDK",
            package_name="resend",
            docs_url="https://resend.com/docs/api-reference/introduction",
        )
        self.register(resend_spec)

        supabase_spec = ProviderSpec(
            name="supabase",
            display_name="Supabase JS Client",
            package_name="@supabase/supabase-js",
            docs_url="https://supabase.com/docs/reference/javascript/introduction",
        )
        self.register(supabase_spec)


_GLOBAL_REGISTRY: Optional[ProviderRegistry] = None


def get_default_registry() -> ProviderRegistry:
    """Get global default provider registry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ProviderRegistry()
    return _GLOBAL_REGISTRY
