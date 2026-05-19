"""
FlowState-Engine Configuration Module.

Loads and validates all environment variables used across the system.
Provides a singleton Settings object accessible via get_settings().
"""

import os
from functools import lru_cache
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class LLMSettings(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(default="openai", description="LLM provider: openai | anthropic")
    model: str = Field(default="gpt-4o", description="Model identifier")
    api_key: str = Field(default="", description="API key for the LLM provider")
    temperature_pm: float = Field(default=0.4, description="PM agent temperature")
    temperature_swe: float = Field(default=0.2, description="SWE agent temperature")
    temperature_qa: float = Field(default=0.1, description="QA agent temperature")


class SandboxSettings(BaseModel):
    """Docker sandbox configuration."""
    base_image_python: str = Field(default="python:3.11-alpine")
    base_image_node: str = Field(default="node:20-alpine")
    base_image_go: str = Field(default="golang:1.22-alpine")
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    memory_limit: str = Field(default="256m")
    cpu_limit: float = Field(default=0.5, ge=0.1, le=4.0)


class ServerSettings(BaseModel):
    """Backend server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1024, le=65535)
    max_iterations: int = Field(default=5, ge=1, le=20)


class Settings(BaseModel):
    """Root configuration container."""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)


@lru_cache()
def get_settings() -> Settings:
    """Load settings from environment variables. Cached after first call."""
    return Settings(
        llm=LLMSettings(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("LLM_API_KEY", ""),
            temperature_pm=float(os.getenv("LLM_TEMPERATURE_PM", "0.4")),
            temperature_swe=float(os.getenv("LLM_TEMPERATURE_SWE", "0.2")),
            temperature_qa=float(os.getenv("LLM_TEMPERATURE_QA", "0.1")),
        ),
        sandbox=SandboxSettings(
            base_image_python=os.getenv("SANDBOX_BASE_IMAGE_PYTHON", "python:3.11-alpine"),
            base_image_node=os.getenv("SANDBOX_BASE_IMAGE_NODE", "node:20-alpine"),
            base_image_go=os.getenv("SANDBOX_BASE_IMAGE_GO", "golang:1.22-alpine"),
            timeout_seconds=int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "30")),
            memory_limit=os.getenv("SANDBOX_MEMORY_LIMIT", "256m"),
            cpu_limit=float(os.getenv("SANDBOX_CPU_LIMIT", "0.5")),
        ),
        server=ServerSettings(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "5")),
        ),
    )
