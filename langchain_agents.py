"""
Backward compatibility wrapper.
The actual implementation is now in business/ai_agents/langchain_agents.py
"""

from business.ai_agents.langchain_agents import (  # noqa: F401
    TourismMultiAgent,
    TourismNLUTool,
    AccessibilityAnalysisTool,
    RoutePlanningTool,
    TourismInfoTool,
    test_individual_tools,
    test_orchestrator,
)

if __name__ == "__main__":
    import asyncio

    print("VoiceFlow STT + LangChain Multi-Agent System")
    print("=" * 60)
    asyncio.run(test_individual_tools())
    print("\n" + "=" * 60)
    asyncio.run(test_orchestrator())
    print("\nTemplate testing complete!")
