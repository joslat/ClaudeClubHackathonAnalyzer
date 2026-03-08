"""Analyzer: AI / LLM Integration Depth — detect and score AI usage sophistication.

Scans source files for AI/ML library imports, API usage patterns, and
architectural patterns like RAG, multi-agent orchestration, and tool calling.
"""

import re
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import AIIntegrationResult
from hackathon_analyzer.utils.file_utils import safe_read_text, walk_repo


# --- AI library detection ---
# Maps import names to their canonical library name
_AI_LIBRARIES: dict[str, str] = {
    # LLM providers
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "groq": "Groq",
    "mistralai": "Mistral",
    "cohere": "Cohere",
    "google.generativeai": "Google Gemini",
    "google.ai": "Google AI",
    "together": "Together AI",
    "replicate": "Replicate",
    "ollama": "Ollama",
    "litellm": "LiteLLM",
    # Frameworks
    "langchain": "LangChain",
    "langchain_core": "LangChain",
    "langchain_community": "LangChain",
    "langchain_openai": "LangChain",
    "langchain_anthropic": "LangChain",
    "llamaindex": "LlamaIndex",
    "llama_index": "LlamaIndex",
    "semantic_kernel": "Semantic Kernel",
    "autogen": "AutoGen",
    "crewai": "CrewAI",
    "phidata": "Phidata",
    "dspy": "DSPy",
    "instructor": "Instructor",
    "guidance": "Guidance",
    "outlines": "Outlines",
    "guardrails": "Guardrails",
    "marvin": "Marvin",
    # Vector DBs
    "chromadb": "ChromaDB",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "qdrant_client": "Qdrant",
    "milvus": "Milvus",
    "pgvector": "pgvector",
    "faiss": "FAISS",
    # ML/DL
    "transformers": "HuggingFace Transformers",
    "huggingface_hub": "HuggingFace Hub",
    "sentence_transformers": "Sentence Transformers",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "sklearn": "scikit-learn",
    "xgboost": "XGBoost",
    # Embeddings / tokenizers
    "tiktoken": "tiktoken",
    "tokenizers": "tokenizers",
}

# JavaScript/TypeScript AI package names (from package.json imports)
_JS_AI_PACKAGES: dict[str, str] = {
    "openai": "OpenAI",
    "@anthropic-ai/sdk": "Anthropic",
    "anthropic": "Anthropic",
    "langchain": "LangChain",
    "@langchain/core": "LangChain",
    "@langchain/openai": "LangChain",
    "@langchain/anthropic": "LangChain",
    "llamaindex": "LlamaIndex",
    "ai": "Vercel AI SDK",
    "@ai-sdk/openai": "Vercel AI SDK",
    "chromadb": "ChromaDB",
    "@pinecone-database/pinecone": "Pinecone",
    "cohere-ai": "Cohere",
    "@google/generative-ai": "Google Gemini",
    "replicate": "Replicate",
    "ollama": "Ollama",
}

# --- Pattern detection (from code content) ---
# Maps to (pattern_name, sophistication_tier)
# Tiers: basic=0.3, intermediate=0.5, advanced=0.7, expert=0.9
_CODE_PATTERNS: list[tuple[str, str, float]] = [
    # Basic: raw API calls (0.3)
    (r"ChatCompletion\.create|chat\.completions\.create", "raw_api_call", 0.3),
    (r"messages\.create|client\.messages", "raw_api_call", 0.3),
    (r"\.generate\(|\.complete\(", "raw_api_call", 0.3),

    # Intermediate: structured prompting (0.5)
    (r"system[_\s]*message|role.*system|SystemMessage", "system_message", 0.5),
    (r"prompt[_\s]*template|PromptTemplate|ChatPromptTemplate", "prompt_template", 0.5),
    (r"response_format|structured_output|json_mode", "structured_output", 0.5),
    (r"\.stream\(|stream=True|streaming", "streaming", 0.5),

    # Intermediate-high: function/tool calling (0.6)
    (r"tool_choice|function_call|tools\s*=|Tool\(", "tool_calling", 0.6),
    (r"tool_use|use_tool|bind_tools|with_structured_output", "tool_calling", 0.6),

    # Advanced: RAG patterns (0.7)
    (r"embed(?:ding)?s?\(|create_embedding|get_embedding", "embeddings", 0.7),
    (r"vector[_\s]*(?:store|db|search|index)|VectorStore", "vector_store", 0.7),
    (r"retriev(?:er|al)|similarity_search|semantic_search", "retrieval", 0.7),
    (r"RetrievalQA|RetrievalChain|RAG|rag_chain", "rag_pipeline", 0.7),
    (r"text_splitter|chunk|RecursiveCharacterTextSplitter", "text_chunking", 0.7),
    (r"document_loader|DirectoryLoader|WebBaseLoader", "document_loading", 0.7),

    # Advanced: agent patterns (0.8)
    (r"AgentExecutor|create_agent|initialize_agent", "agent", 0.8),
    (r"BaseTool|@tool|StructuredTool", "custom_tools", 0.8),
    (r"memory|ConversationBuffer|chat_history", "memory", 0.7),
    (r"chain\.invoke|RunnableSequence|LCEL", "chain_composition", 0.7),

    # Expert: multi-agent orchestration (0.9)
    (r"crew|CrewAI|Agent\(.*role|Task\(.*description", "multi_agent", 0.9),
    (r"autogen|AssistantAgent|UserProxyAgent|GroupChat", "multi_agent", 0.9),
    (r"swarm|orchestrat|supervisor|planner.*executor", "multi_agent", 0.9),

    # Expert: fine-tuning / training (1.0)
    (r"fine_tun|FineTun|training_args|TrainingArguments", "fine_tuning", 1.0),
    (r"Trainer\(|SFTTrainer|LoRA|peft|qlora", "fine_tuning", 1.0),
    (r"\.train\(\)|model\.fit|compile.*optimizer", "model_training", 1.0),
]

# Source file extensions to scan
_SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".cs", ".kt", ".scala", ".swift",
}


def analyze_ai_integration(repo_path: Path) -> AIIntegrationResult:
    """Detect and score AI/LLM integration depth in the codebase."""
    result = AIIntegrationResult()

    libraries_found: set[str] = set()
    patterns_found: dict[str, float] = {}  # pattern_name → max tier score
    evidence: list[str] = []

    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            fpath = dirpath / fname
            if fpath.suffix.lower() not in _SOURCE_EXTS:
                continue

            content = safe_read_text(fpath, max_bytes=100_000)
            if not content:
                continue

            rel = str(fpath.relative_to(repo_path))

            # Detect AI library imports
            _detect_library_imports(content, rel, libraries_found, evidence)

            # Detect code patterns
            _detect_code_patterns(content, rel, patterns_found, evidence)

    # Also scan package.json for JS AI packages
    _detect_js_packages(repo_path, libraries_found, evidence)

    result.ai_libraries_detected = sorted(libraries_found)
    result.ai_patterns_detected = sorted(patterns_found.keys())
    result.evidence = evidence[:20]  # Limit evidence entries

    # Compute depth score
    if not libraries_found and not patterns_found:
        result.integration_depth = "none"
        result.depth_score = 0.0
        return result

    # Highest pattern tier detected
    max_tier = max(patterns_found.values()) if patterns_found else 0.3
    # Bonus for library diversity
    lib_bonus = min(0.1, len(libraries_found) * 0.03)

    raw_score = min(1.0, max_tier + lib_bonus)
    result.depth_score = round(raw_score, 3)
    result.integration_depth = _tier_label(raw_score)

    return result


def _detect_library_imports(
    content: str,
    rel_path: str,
    libraries_found: set[str],
    evidence: list[str],
) -> None:
    """Scan file content for AI library import statements."""
    for import_name, lib_name in _AI_LIBRARIES.items():
        # Python: import X, from X import, from X.Y import
        pattern = rf"(?:^|\n)\s*(?:import|from)\s+{re.escape(import_name)}"
        if re.search(pattern, content):
            if lib_name not in libraries_found:
                libraries_found.add(lib_name)
                evidence.append(f"{rel_path}: imports {lib_name}")


def _detect_code_patterns(
    content: str,
    rel_path: str,
    patterns_found: dict[str, float],
    evidence: list[str],
) -> None:
    """Scan file content for AI usage patterns."""
    for pattern_re, pattern_name, tier_score in _CODE_PATTERNS:
        if re.search(pattern_re, content, re.IGNORECASE):
            existing = patterns_found.get(pattern_name, 0.0)
            if tier_score > existing:
                patterns_found[pattern_name] = tier_score
                if pattern_name not in {p.split(":")[0] for p in evidence if ":" in p}:
                    evidence.append(f"{rel_path}: {pattern_name}")


def _detect_js_packages(
    repo_path: Path,
    libraries_found: set[str],
    evidence: list[str],
) -> None:
    """Check package.json for AI-related JS/TS packages."""
    import json
    pkg_json = repo_path / "package.json"
    if not pkg_json.exists():
        return
    text = safe_read_text(pkg_json, max_bytes=50_000) or ""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return

    for section in ["dependencies", "devDependencies"]:
        for pkg in data.get(section, {}):
            if pkg in _JS_AI_PACKAGES:
                lib_name = _JS_AI_PACKAGES[pkg]
                if lib_name not in libraries_found:
                    libraries_found.add(lib_name)
                    evidence.append(f"package.json: {lib_name} ({pkg})")


def _tier_label(score: float) -> str:
    """Map numeric score to depth label."""
    if score >= 0.85:
        return "expert"
    if score >= 0.65:
        return "advanced"
    if score >= 0.45:
        return "intermediate"
    if score > 0.0:
        return "basic"
    return "none"
