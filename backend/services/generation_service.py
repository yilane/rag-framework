import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from openai import OpenAI
import requests
from utils.config import config

logger = logging.getLogger(__name__)

class GenerationService:
    """
    生成服务类：负责调用不同的模型提供商（HuggingFace、OpenAI、DeepSeek）生成回答
    支持本地模型和API调用，并将生成结果保存到文件
    """
    def __init__(self):
        """
        初始化生成服务，配置支持的模型列表和创建输出目录
        """
        self.models = {
            "huggingface": {
                "Llama-2-7b-chat": "meta-llama/Llama-2-7b-chat-hf",
                "DeepSeek-7b": "deepseek-ai/deepseek-llm-7b-chat",
                "DeepSeek-R1-Distill-Qwen": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
            },
            "openai": {
                "gpt-3.5-turbo": "gpt-3.5-turbo",
                "gpt-4": "gpt-4",
            },
            "deepseek": {
                "deepseek-v3": "deepseek-chat",
                "deepseek-r1": "deepseek-reasoner",
            }
        }
        
        # 确保输出目录存在
        os.makedirs("05-generation-results", exist_ok=True)
        
    def _load_huggingface_model(self, model_name: str):
        """
        加载HuggingFace模型
        
        参数:
            model_name: 模型名称，对应self.models["huggingface"]中的键
            
        返回:
            model: 加载的模型
            tokenizer: 对应的分词器
        """
        try:
            model = AutoModelForCausalLM.from_pretrained(
                self.models["huggingface"][model_name],
                torch_dtype=torch.float16,
                device_map="auto"
            )
            tokenizer = AutoTokenizer.from_pretrained(
                self.models["huggingface"][model_name]
            )
            return model, tokenizer
        except Exception as e:
            logger.error(f"Error loading HuggingFace model: {str(e)}")
            raise

    def _generate_with_huggingface(
        self,
        model_name: str,
        query: str,
        context: str,
        max_length: int = 512
    ) -> str:
        """
        使用HuggingFace模型生成回答
        
        参数:
            model_name: 模型名称
            query: 用户查询
            context: 上下文信息
            max_length: 生成文本的最大长度
            
        返回:
            生成的回答文本
        """
        try:
            model, tokenizer = self._load_huggingface_model(model_name)
            
            # 构建提示
            prompt = f"""请基于以下上下文回答问题。如果上下文中没有相关信息，请说明无法回答。

                        问题：{query}

                        上下文：
                        {context}

                        回答："""
        
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            outputs = model.generate(
                **inputs,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response.split("回答：")[-1].strip()
            
        except Exception as e:
            logger.error(f"Error generating with HuggingFace: {str(e)}")
            raise

    def _sanitize_content(self, text: str, max_length: int = 8000) -> str:
        """
        清理和过滤内容，移除可能触发内容安全检查的文本
        
        参数:
            text: 需要清理的文本
            max_length: 最大长度限制
            
        返回:
            清理后的文本
        """
        if not text:
            return ""
            
        # 截断过长的文本
        if len(text) > max_length:
            text = text[:max_length] + "..."
            
        # 移除可能的敏感内容标识词（示例）
        sensitive_patterns = [
            # 可以根据实际情况添加更多过滤规则
        ]
        
        cleaned_text = text
        for pattern in sensitive_patterns:
            cleaned_text = cleaned_text.replace(pattern, "[FILTERED]")
            
        return cleaned_text

    def _generate_with_openai(
        self,
        model_name: str,
        query: str,
        context: str,
        api_key: Optional[str] = None
    ) -> str:
        """
        使用OpenAI API生成回答
        
        参数:
            model_name: 模型名称
            query: 用户查询
            context: 上下文信息
            api_key: OpenAI API密钥，如不提供则从环境变量获取
            
        返回:
            生成的回答文本
        """
        try:
            if not api_key:
                api_key = api_key or config.OPENAI_API_KEY
                if not api_key:
                    raise ValueError("OpenAI API key not provided")
                    
            client = OpenAI(api_key=api_key)
            
            # 清理内容以避免触发安全检查
            sanitized_query = self._sanitize_content(query, 1000)
            sanitized_context = self._sanitize_content(context, 6000)
            
            logger.info(f"Original query length: {len(query)}, sanitized: {len(sanitized_query)}")
            logger.info(f"Original context length: {len(context)}, sanitized: {len(sanitized_context)}")
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer the question accurately and concisely."},
                {"role": "user", "content": f"Context: {sanitized_context}\n\nQuestion: {sanitized_query}"}
            ]
            
            response = client.chat.completions.create(
                model=self.models["openai"][model_name],
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error generating with OpenAI: {error_str}")
            
            # 处理特定的内容风险错误
            if "Content Exists Risk" in error_str:
                logger.warning("Content safety check triggered. Attempting with reduced context.")
                try:
                    # 尝试使用更简短的上下文重新生成
                    short_context = self._sanitize_content(context, 2000)
                    short_query = self._sanitize_content(query, 500)
                    
                    messages = [
                        {"role": "system", "content": "You are a helpful assistant. Answer based on the provided information."},
                        {"role": "user", "content": f"Information: {short_context}\n\nQuestion: {short_query}"}
                    ]
                    
                    response = client.chat.completions.create(
                        model=self.models["openai"][model_name],
                        messages=messages,
                        temperature=0.5,
                        max_tokens=256
                    )
                    
                    return response.choices[0].message.content.strip()
                    
                except Exception as retry_e:
                    logger.error(f"Retry also failed: {str(retry_e)}")
                    return "抱歉，由于内容安全检查，无法生成回答。请尝试重新表述您的问题或使用其他模型。"
            
            raise

    def _generate_with_deepseek(
        self,
        model_name: str,
        query: str,
        context: str,
        api_key: Optional[str] = None,
        show_reasoning: bool = True
    ) -> str:
        """
        使用DeepSeek API生成回答
        
        参数:
            model_name: 模型名称
            query: 用户查询
            context: 上下文信息
            api_key: DeepSeek API密钥，如不提供则从环境变量获取
            show_reasoning: 是否显示推理过程（仅对推理模型有效）
            
        返回:
            生成的回答文本，对于推理模型可能包含思维过程
        """
        try:
            if not api_key:
                api_key = api_key or config.DEEPSEEK_API_KEY
                if not api_key:
                    raise ValueError("DeepSeek API key not provided")
                    
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
            # 清理内容以避免触发安全检查
            sanitized_query = self._sanitize_content(query, 1000)
            sanitized_context = self._sanitize_content(context, 6000)
            
            logger.info(f"DeepSeek - Original query length: {len(query)}, sanitized: {len(sanitized_query)}")
            logger.info(f"DeepSeek - Original context length: {len(context)}, sanitized: {len(sanitized_context)}")
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer the question accurately and concisely."},
                {"role": "user", "content": f"Context: {sanitized_context}\n\nQuestion: {sanitized_query}"}
            ]
            
            response = client.chat.completions.create(
                model=self.models["deepseek"][model_name],
                messages=messages,
                max_tokens=512,
                stream=False
            )
            
            # 如果是推理模型，处理思维链输出
            if model_name == "deepseek-r1":
                message = response.choices[0].message
                reasoning = getattr(message, 'reasoning_content', None)
                answer = message.content
                
                if show_reasoning and reasoning:
                    return f"【思维过程】\n{reasoning}\n\n【最终答案】\n{answer}"
                return answer
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error generating with DeepSeek: {error_str}")
            
            # 处理特定的内容风险错误
            if "Content Exists Risk" in error_str or "content_policy_violation" in error_str:
                logger.warning("DeepSeek content safety check triggered. Attempting with reduced context.")
                try:
                    # 尝试使用更简短的上下文重新生成
                    short_context = self._sanitize_content(context, 2000)
                    short_query = self._sanitize_content(query, 500)
                    
                    messages = [
                        {"role": "system", "content": "You are a helpful assistant. Answer based on the provided information."},
                        {"role": "user", "content": f"Information: {short_context}\n\nQuestion: {short_query}"}
                    ]
                    
                    response = client.chat.completions.create(
                        model=self.models["deepseek"][model_name],
                        messages=messages,
                        max_tokens=256,
                        stream=False
                    )
                    
                    return response.choices[0].message.content.strip()
                    
                except Exception as retry_e:
                    logger.error(f"DeepSeek retry also failed: {str(retry_e)}")
                    return "抱歉，由于内容安全检查，无法生成回答。请尝试重新表述您的问题或使用其他模型。"
            
            raise

    def generate(
        self,
        provider: str,
        model_name: str,
        query: str,
        search_results: List[Dict],
        api_key: Optional[str] = None,
        show_reasoning: bool = True
    ) -> Dict:
        """
        生成回答并保存结果
        
        参数:
            provider: 模型提供商，可选值为"huggingface"、"openai"、"deepseek"
            model_name: 模型名称
            query: 用户查询
            search_results: 搜索结果列表，用于构建上下文
            api_key: API密钥（对于API调用）
            show_reasoning: 是否显示推理过程（仅对DeepSeek推理模型有效）
            
        返回:
            包含生成回答和保存路径的字典
        """
        try:
            # 准备上下文
            context = "\n\n".join([
                f"[Source {i+1}]: {result['text']}"
                for i, result in enumerate(search_results)
            ])
            
            # 根据不同提供商生成回答
            if provider == "huggingface":
                response = self._generate_with_huggingface(model_name, query, context)
            elif provider == "openai":
                api_key = api_key or config.OPENAI_API_KEY
                if not api_key:
                    raise ValueError("OpenAI API key is required")
                response = self._generate_with_openai(model_name, query, context, api_key)
            elif provider == "deepseek":
                api_key = api_key or config.DEEPSEEK_API_KEY
                if not api_key:
                    raise ValueError("Deepseek API key is required")
                response = self._generate_with_deepseek(model_name, query, context, api_key, show_reasoning)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
            # 准备保存的结果
            result = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "provider": provider,
                "model": model_name,
                "response": response,
                "context": search_results
            }
            
            # 生成文件名并保存
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"generation_{provider}_{model_name}_{timestamp}.json"
            filepath = os.path.join("05-generation-results", filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            return {
                "response": response,
                "saved_filepath": filepath
            }
            
        except Exception as e:
            logger.error(f"Error in generation: {str(e)}")
            raise

    def get_available_models(self) -> Dict:
        """
        获取可用的模型列表
        
        返回:
            包含所有支持模型的字典
        """
        return self.models 