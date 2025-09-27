"""
RAG Processor Module
==================

This module implements Retrieval-Augmented Generation (RAG) using LangChain
for contextual question answering from scraped web content.

Author: AI Assistant
Date: 2025
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from urllib.parse import urlparse

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document, HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate

from config.settings import AppConfig
from utils.helpers import clean_text, format_response

logger = logging.getLogger(__name__)

_model_cache = {}

def get_sentence_transformer(model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """Get cached sentence transformer model"""
    if model_name not in _model_cache:
        cache_dir = os.path.expanduser("~/.cache/sentence_transformers")
        _model_cache[model_name] = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
            cache_folder=cache_dir  # You may need to update HuggingFaceEmbeddings to accept this or remove if unsupported
        )
    return _model_cache[model_name]


class RAGProcessor:
    """Retrieval-Augmented Generation processor for contextual Q&A (synchronous)"""
    
    def __init__(self):
        self.config = AppConfig()
        self.llm = self._setup_llm()
        self.embeddings = self._setup_embeddings()  # Uses cached embeddings now
        self.text_splitter = self._setup_text_splitter()
        self.vector_store = None
        self.conversation_chain = None
        self.document_metadata = {}
        self._initialize_once()
    def _initialize_once(self):
        """Initialize embeddings and vector store a single time to avoid overhead"""
        if self.embeddings is None:
            self.embeddings = get_sentence_transformer(self.config.EMBEDDING_MODEL)
        
        if self.vector_store is None:
            os.makedirs(self.config.VECTOR_DB_PERSIST_DIR, exist_ok=True)
            self.vector_store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=self.config.VECTOR_DB_PERSIST_DIR,
                collection_name="web_content"
            )
            logger.info("Vector store initialized successfully")
      
    def _setup_llm(self) -> ChatGroq:
        try:
            return ChatGroq(
                model=self.config.LLM_MODEL,
                groq_api_key=self.config.GROQ_API_KEY,
                temperature=0.1,
                max_tokens=2000
            )
        except Exception as e:
            logger.error(f"Failed to setup LLM: {str(e)}")
            raise
    
    def _setup_embeddings(self) -> HuggingFaceEmbeddings:
        try:
            return get_sentence_transformer(self.config.EMBEDDING_MODEL)

        except Exception as e:
            logger.error(f"Failed to setup embeddings: {str(e)}")
            raise
    
    def _setup_text_splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ",]
        )
    
    def _initialize_vector_store(self):
        try:
            os.makedirs(self.config.VECTOR_DB_PERSIST_DIR, exist_ok=True)
            self.vector_store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=self.config.VECTOR_DB_PERSIST_DIR,
                collection_name="web_content"
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def _create_document_id(self, content: str, url: str) -> str:
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{url}_{content_hash[:8]}"
    
    def _setup_conversation_chain(self):
        try:
            if not self.vector_store:
                raise ValueError("Vector store not initialized")
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": self.config.TOP_K_DOCUMENTS}
            )
            custom_prompt = PromptTemplate(
                template="""You are an intelligent assistant helping users understand web content for bot testing purposes.

Context from web pages:
{context}

Chat History:
{chat_history}

User Question: {question}

Instructions:
- Provide accurate, helpful answers based on the context
- If information is not in the context, say "This information is not available in the loaded web content"
- Be conversational and natural
- Reference specific pages when relevant
- For bot testing questions, provide detailed, actionable responses

Answer:""",
                input_variables=["context", "chat_history", "question"]
            )
            self.conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                return_source_documents=True,
                verbose=False,
                combine_docs_chain_kwargs={"prompt": custom_prompt}
            )
            logger.info("Conversation chain setup completed")
        except Exception as e:
            logger.error(f"Failed to setup conversation chain: {str(e)}")
            raise
    
    def add_documents(self, content: str, url: str) -> bool:
        try:
            logger.debug(f"Raw content from {url}: {content[:1000]}...")
            cleaned_content = clean_text(content)
            logger.debug(f"Cleaned content from {url}: {cleaned_content[:1000]}...")
            
            if len(cleaned_content) < 100:
                logger.warning(f"Content too short to add from {url}: {len(cleaned_content)} chars")
                return False
            
            doc_id = self._create_document_id(cleaned_content, url)
            if doc_id in self.document_metadata:
                logger.info(f"Document already exists: {doc_id}")
                return True
            
            chunks = self.text_splitter.split_text(cleaned_content)
            if not chunks:
                logger.warning(f"No chunks created from content at {url}")
                return False
            
            # Filter out invalid or short chunks
            valid_chunks = [chunk for chunk in chunks if len(chunk.strip()) >= 50 and '"questions"' not in chunk]
            logger.info(f"Created {len(chunks)} chunks, {len(valid_chunks)} valid chunks from {url}")
            
            if not valid_chunks:
                logger.warning(f"No valid chunks after filtering from {url}")
                return False
            
            documents = [
                Document(
                    page_content=chunk,
                    metadata={
                        "source": url,
                        "chunk_id": f"{doc_id}_chunk_{i}",
                        "total_chunks": len(valid_chunks),
                        "added_at": datetime.now().isoformat(),
                        "content_type": "web_content"
                    }
                )
                for i, chunk in enumerate(valid_chunks)
            ]
            
            self.vector_store.add_documents(documents)
            self.document_metadata[doc_id] = {
                "url": url,
                "chunks_count": len(valid_chunks),
                "content_length": len(cleaned_content),
                "added_at": datetime.now().isoformat()
            }
            
            if not self.conversation_chain:
                self._setup_conversation_chain()
            
            logger.info(f"Successfully added {len(documents)} document chunks from {url}")
            return True
        except Exception as e:
            logger.error(f"Error adding documents from {url}: {str(e)}")
            return False
    
    def query_with_context(self, question: str, chat_history: List[Dict[str, str]] = None) -> str:
        try:
            if not self.conversation_chain:
                return "No documents loaded yet. Please load some web content first."
            
            formatted_history = []
            if chat_history:
                for message in chat_history[-10:]:
                    role = message.get("role")
                    content = message.get("content", "")
                    formatted_history.append(("human" if role == "user" else "ai", content))
            
            result = self.conversation_chain({
                "question": question,
                "chat_history": formatted_history
            })
            
            answer = result.get("answer", "")
            source_docs = result.get("source_documents", [])
            
            if source_docs:
                sources = {doc.metadata.get("source", "Unknown") for doc in source_docs}
                if sources:
                    source_list = list(sources)[:3]
                    sources_text = ", ".join([self._extract_domain(url) for url in source_list])
                    answer += f"\n\n*Sources: {sources_text}*"
            
            return format_response(answer)
        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}")
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"
    
    def get_general_response(self, question: str, chat_history: List[Dict[str, str]] = None) -> str:
        try:
            context = ""
            if chat_history:
                context = "Previous conversation context:\n"
                for message in chat_history[-5:]:
                    context += f"{message.get('role', '')}: {message.get('content','')[:200]}\n"
                context += "\n"
            
            prompt = f"""{context}Please answer the following question as helpfully as possible:

Question: {question}

Answer:"""
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return format_response(response.content)
        except Exception as e:
            logger.error(f"Error in general response: {str(e)}")
            return "I apologize, but I couldn't generate a response at this time."
    
    def _extract_domain(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return url
    
    def search_similar_content(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            if not self.vector_store:
                return []
            
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            return [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "Unknown"),
                    "similarity_score": float(score),
                    "chunk_id": doc.metadata.get("chunk_id", ""),
                    "added_at": doc.metadata.get("added_at", "")
                }
                for doc, score in results
            ]
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []
    
    def get_vector_store_stats(self) -> Dict[str, Any]:
        try:
            if not self.vector_store:
                return {"status": "not_initialized"}
            collection = self.vector_store._collection
            count = collection.count()
            return {
                "status": "active",
                "document_count": count,
                "unique_documents": len(self.document_metadata),
                "sources": list({meta["url"] for meta in self.document_metadata.values()}),
                "total_chunks": sum(meta["chunks_count"] for meta in self.document_metadata.values())
            }
        except Exception as e:
            logger.error(f"Error getting vector store stats: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def clear_vector_store(self) -> bool:
        try:
            if self.vector_store:
                self.vector_store.delete_collection()
                self._initialize_vector_store()
                self.document_metadata.clear()
                self.conversation_chain = None
                logger.info("Vector store cleared successfully")
                return True
        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
            return False
    
    def close(self):
        try:
            if self.vector_store:
                self.vector_store.persist()
            logger.info("RAG processor closed successfully")
        except Exception as e:
            logger.error(f"Error during RAG processor cleanup: {str(e)}")
