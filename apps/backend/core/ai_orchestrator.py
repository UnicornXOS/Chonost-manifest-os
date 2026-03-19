"""
AI Orchestrator Service

This service manages multiple AI providers, external integrations, and MCP tools.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
import os

# Import AI providers
try:
    # Unified client is the goal
    from utils.unified_ai_client import get_client
except ImportError:
    # Fallback for environments where utils is not in the path
    # This allows the app to still run, albeit with missing functionality.
    get_client = None

class AIOrchestrator:
    """AI Orchestrator for managing multiple AI providers and integrations"""

    def __init__(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("ENCRYPTION_KEY environment variable must be set for secure operation")
        try:
            self.encryption_key = key.encode() if isinstance(key, str) else key
            self.cipher_suite = Fernet(self.encryption_key)
        except Exception as e:  # pragma: no cover - defensive
            raise ValueError("Invalid ENCRYPTION_KEY: must be a 32 urlsafe base64-encoded key") from e

        if get_client:
            self.ai_client = get_client()
        else:
            self.ai_client = None
            print("Warning: UnifiedAIClient could not be imported. AI functionality will be limited.")

        self.providers = {}
        self.integrations = {}
        self.mcp_tools = {}
        self.usage_tracker = {}
        
    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage"""
        return self.cipher_suite.encrypt(api_key.encode()).decode()
    
    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        return self.cipher_suite.decrypt(encrypted_key.encode()).decode()
    
    def _get_user_providers(self, user_id: str) -> Dict[str, Any]:
        """Get user's configured providers from database"""
        # TODO: Implement database lookup
        return self.providers.get(user_id, {})
    
    def _save_user_providers(self, user_id: str, providers: Dict[str, Any]):
        """Save user's providers to database"""
        # TODO: Implement database save
        self.providers[user_id] = providers
    
    def configure_provider(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Configure an AI provider for a user"""
        try:
            # Encrypt API key
            encrypted_key = self._encrypt_api_key(api_key)
            
            # Get user's providers
            user_providers = self._get_user_providers(user_id)
            
            # Add/update provider
            user_providers[provider] = {
                "api_key": encrypted_key,
                "base_url": base_url,
                "model": model,
                "config": config or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Save to database
            self._save_user_providers(user_id, user_providers)
            
            return {
                "success": True,
                "message": f"Provider {provider} configured successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to configure provider: {str(e)}"
            }
    
    def list_providers(self, user_id: str) -> Dict[str, Any]:
        """List user's configured providers"""
        try:
            user_providers = self._get_user_providers(user_id)
            
            # Return provider names and config (without API keys)
            providers_list = []
            for provider_name, provider_config in user_providers.items():
                providers_list.append({
                    "name": provider_name,
                    "base_url": provider_config.get("base_url"),
                    "model": provider_config.get("model"),
                    "config": provider_config.get("config", {}),
                    "created_at": provider_config.get("created_at"),
                    "updated_at": provider_config.get("updated_at")
                })
            
            return {
                "success": True,
                "providers": providers_list
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list providers: {str(e)}"
            }
    
    def remove_provider(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Remove a provider for a user"""
        try:
            user_providers = self._get_user_providers(user_id)
            
            if provider in user_providers:
                del user_providers[provider]
                self._save_user_providers(user_id, user_providers)
                
                return {
                    "success": True,
                    "message": f"Provider {provider} removed successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Provider {provider} not found"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to remove provider: {str(e)}"
            }
    
    async def test_provider(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Test a provider connection using the UnifiedAIClient."""
        if not self.ai_client:
            return {"success": False, "message": "AI Client not initialized."}

        try:
            user_providers = self._get_user_providers(user_id)
            if provider not in user_providers:
                return {"success": False, "message": f"Provider {provider} not configured."}

            # Use a simple, low-cost prompt for testing
            test_messages = [{"role": "user", "content": "Hello"}]
            
            # The unified client is initialized with config, so we just call it.
            result = await self.ai_client.generate_response(provider, test_messages, max_tokens=10)

            if result and result.get('success'):
                return {"success": True, "details": {"status": "connected", "response": result.get('content')}}
            else:
                error_message = result.get('error', 'Unknown error during test.')
                return {"success": False, "message": f"Provider test failed: {error_message}"}

        except Exception as e:
            return {"success": False, "message": f"Failed to test provider: {str(e)}"}

    async def create_completion(
        self,
        user_id: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a completion using the UnifiedAIClient."""
        if not self.ai_client:
            return {"success": False, "message": "AI Client not initialized."}

        try:
            user_providers = self._get_user_providers(user_id)
            if not user_providers:
                return {"success": False, "message": "No AI providers configured."}

            # Convert prompt to messages format
            messages = [{"role": "user", "content": prompt}]
            
            # Prepare kwargs for the unified client
            kwargs = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
                **(config or {})
            }
            if model:
                kwargs["model"] = model

            # Try providers in their configured order
            for provider_name in user_providers.keys():
                try:
                    # The unified client handles the authentication and provider logic
                    result = await self.ai_client.generate_response(provider_name, messages, **kwargs)
                    
                    if result and result.get('success'):
                        # Track usage
                        self._track_usage(user_id, provider_name, result.get("metadata", {}).get("usage", {}))
                        
                        # Adapt the unified client's response to the expected format
                        return {
                            "success": True,
                            "provider": result.get('provider'),
                            "model": result.get('metadata', {}).get('model'),
                            "content": result.get('content'),
                            "usage": result.get("metadata", {}).get("usage", {})
                        }
                except Exception as e:
                    print(f"Provider {provider_name} failed: {str(e)}")
                    continue # Try the next provider
            
            return {"success": False, "message": "All configured providers failed to generate a response."}

        except Exception as e:
            return {"success": False, "message": f"Failed to create completion: {str(e)}"}
    
    async def analyze_content(
        self,
        user_id: str,
        content: str,
        analysis_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze content using AI"""
        try:
            # Create analysis prompt based on type
            if analysis_type == "character":
                prompt = f"Analyze the following character from a manuscript:\n\n{content}\n\nProvide analysis of: personality, motivations, development, relationships, and role in the story."
            elif analysis_type == "plot":
                prompt = f"Analyze the following plot element:\n\n{content}\n\nProvide analysis of: structure, pacing, conflict, resolution, and narrative arc."
            elif analysis_type == "writing":
                prompt = f"Analyze the following writing sample:\n\n{content}\n\nProvide analysis of: style, tone, clarity, engagement, and technical quality."
            else:
                return {
                    "success": False,
                    "message": f"Unknown analysis type: {analysis_type}"
                }
            
            # Use completion to analyze
            result = await self.create_completion(
                user_id=user_id,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3,
                config=config
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "analysis": {
                        "type": analysis_type,
                        "content": content,
                        "result": result["content"],
                        "provider": result["provider"],
                        "model": result["model"],
                        "usage": result.get("usage", {}),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            else:
                return result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to analyze content: {str(e)}"
            }
    
    def configure_integration(
        self,
        user_id: str,
        service: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure external integration"""
        try:
            # Get user's integrations
            user_integrations = self.integrations.get(user_id, {})
            
            # Add/update integration
            user_integrations[service] = {
                "config": config,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.integrations[user_id] = user_integrations
            
            return {
                "success": True,
                "message": f"Integration {service} configured successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to configure integration: {str(e)}"
            }
    
    def list_integrations(self, user_id: str) -> Dict[str, Any]:
        """List user's configured integrations"""
        try:
            user_integrations = self.integrations.get(user_id, {})
            
            integrations_list = []
            for service_name, service_config in user_integrations.items():
                integrations_list.append({
                    "service": service_name,
                    "config": service_config.get("config", {}),
                    "created_at": service_config.get("created_at"),
                    "updated_at": service_config.get("updated_at")
                })
            
            return {
                "success": True,
                "integrations": integrations_list
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list integrations: {str(e)}"
            }
    
    def list_mcp_tools(self, user_id: str) -> Dict[str, Any]:
        """List available MCP tools"""
        try:
            # TODO: Implement MCP tool discovery
            tools = [
                {
                    "name": "file_operations",
                    "description": "File system operations",
                    "parameters": {
                        "operation": "read|write|delete|list",
                        "path": "file path"
                    }
                },
                {
                    "name": "code_analysis",
                    "description": "Code analysis and review",
                    "parameters": {
                        "language": "programming language",
                        "code": "code to analyze"
                    }
                }
            ]
            
            return {
                "success": True,
                "tools": tools
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list MCP tools: {str(e)}"
            }
    
    def execute_mcp_tool(
        self,
        user_id: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an MCP tool"""
        try:
            # TODO: Implement MCP tool execution
            if tool_name == "file_operations":
                return self._execute_file_operations(parameters)
            elif tool_name == "code_analysis":
                return self._execute_code_analysis(parameters)
            else:
                return {
                    "success": False,
                    "message": f"Unknown MCP tool: {tool_name}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to execute MCP tool: {str(e)}"
            }
    
    def get_usage_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get usage analytics for a user"""
        try:
            user_usage = self.usage_tracker.get(user_id, {})
            
            return {
                "success": True,
                "analytics": {
                    "total_requests": sum(usage.get("requests", 0) for usage in user_usage.values()),
                    "total_tokens": sum(usage.get("tokens", 0) for usage in user_usage.values()),
                    "providers": user_usage,
                    "period": "all_time"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get usage analytics: {str(e)}"
            }
    
    def get_cost_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get cost analytics for a user"""
        try:
            user_usage = self.usage_tracker.get(user_id, {})
            
            # Calculate costs based on provider rates
            total_cost = 0
            provider_costs = {}
            
            for provider, usage in user_usage.items():
                # TODO: Implement actual cost calculation based on provider rates
                cost = usage.get("tokens", 0) * 0.0001  # Placeholder rate
                provider_costs[provider] = cost
                total_cost += cost
            
            return {
                "success": True,
                "costs": {
                    "total_cost": total_cost,
                    "provider_costs": provider_costs,
                    "currency": "USD",
                    "period": "all_time"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get cost analytics: {str(e)}"
            }
    
    # Private methods for provider-specific operations are now handled by UnifiedAIClient.
    # The methods _test_openai, _test_anthropic, _test_google, _test_ollama,
    # _create_openai_completion, _create_anthropic_completion, _create_google_completion,
    # and _create_ollama_completion have been removed and replaced by calls to the unified client.
    
    def _track_usage(self, user_id: str, provider: str, usage: Dict[str, Any]):
        """Track usage for analytics"""
        if user_id not in self.usage_tracker:
            self.usage_tracker[user_id] = {}
        
        if provider not in self.usage_tracker[user_id]:
            self.usage_tracker[user_id][provider] = {
                "requests": 0,
                "tokens": 0,
                "last_used": None
            }
        
        self.usage_tracker[user_id][provider]["requests"] += 1
        self.usage_tracker[user_id][provider]["tokens"] += usage.get("total_tokens", 0)
        self.usage_tracker[user_id][provider]["last_used"] = datetime.utcnow().isoformat()
    
    def _execute_file_operations(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operations MCP tool"""
        try:
            # TODO: Implement file operations
            return {
                "success": True,
                "result": f"File operation: {parameters.get('operation', 'unknown')}"
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _execute_code_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code analysis MCP tool"""
        try:
            # TODO: Implement code analysis
            return {
                "success": True,
                "result": f"Code analysis for {parameters.get('language', 'unknown')}"
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
