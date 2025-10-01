"""
Language-specific instruction generation for multilingual AI agent support.

Following Pydantic AI best practices for dynamic instructions that leverage
LLM native multilingual capabilities without prompt duplication.
"""


def get_language_instruction(language: str) -> str:
    """
    Generate language-specific instruction for the AI agent.

    This instruction is prepended to the base system prompt to guide the AI
    to respond in the user's preferred language. The instruction tells the
    model to use natural, idiomatic language with appropriate cultural context.

    Args:
        language: ISO 639-1 language code ("en" or "es")

    Returns:
        Language instruction string, or empty string for English (default)

    Note:
        Following industry best practice (per Claude/Anthropic docs), we use
        explicit language instructions rather than duplicating all prompts.
        This leverages the LLM's native multilingual capabilities while
        maintaining a single source of truth for prompt content.
    """
    if language == "es":
        return """IMPORTANTE: Responde completamente en Español. Usa español natural e idiomático como si fueras un consultor de negocios nativo hispanohablante. Mantén terminología de negocios apropiada en español con conciencia cultural y tono profesional. Todas tus respuestas al usuario deben ser en español - nunca uses inglés en tus respuestas."""

    # English is the default - no instruction needed
    return ""
