"""
🎯 RAG System - Retrieval-Augmented Generation.

A comprehensive RAG system for the Synapse Backend Monolith.

Features:
- Vector Database Integration (ChromaDB, Pinecone, Weaviate)
- Multiple Embedding Models (OpenAI, Ollama, Local)
- Document Processing & Chunking
- Semantic Search & Retrieval
- Context-Aware Generation
- Caching & Performance Optimization
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import sqlite3
import redis
import requests
from concurrent.futures import ThreadPoolExecutor
import threading

# Vector Database Imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

# AI/ML Imports
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the unified client
from ..utils.unified_ai_client import get_client

@dataclass
class Document:
    """A document for the RAG System."""
    id: str
    content: str
    metadata: Dict[str, Any]
    source: str
    chunk_index: int = 0
    embedding: Optional[List[float]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Initializes the created_at timestamp if it's not set."""
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class SearchResult:
    """A search result from the RAG System."""
    document: Document
    score: float
    relevance: str  # 'high', 'medium', 'low'

@dataclass
class RAGResponse:
    """A response from the RAG System."""
    answer: str
    sources: List[Document]
    confidence: float
    context_used: str
    processing_time: float

class EmbeddingProvider:
    """A provider for Embedding Models that uses the UnifiedAIClient."""

    def __init__(self, provider_type: str = "ollama", model_name: str = "nomic-embed-text"):
        """
        Initializes the EmbeddingProvider.

        Args:
            provider_type (str, optional): The type of embedding provider. Defaults to "ollama".
            model_name (str, optional): The name of the embedding model. Defaults to "nomic-embed-text".
        """
        self.provider_type = provider_type
        self.model_name = model_name
        self.ai_client = get_client()
        if not self.ai_client.get_provider(self.provider_type):
             logger.warning(f"⚠️ Provider '{self.provider_type}' not available in UnifiedAIClient.")
             self.is_ready = False
        else:
            self.is_ready = True
            logger.info(f"✅ EmbeddingProvider initialized for provider '{self.provider_type}' with model '{self.model_name}'.")

    async def test_connection(self) -> bool:
        """
        Tests the connection to the embedding service via the UnifiedAIClient.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        if not self.is_ready:
            return False
        try:
            # A simple embedding call to test the connection.
            result = await self.ai_client.embed(self.provider_type, "test", model=self.model_name)
            return result.get('success', False)
        except Exception as e:
            logger.error(f"❌ Connection test failed for {self.provider_type}: {e}")
            return False

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Creates an embedding for a text using the UnifiedAIClient.

        Args:
            text (str): The text to create an embedding for.

        Returns:
            Optional[List[float]]: The created embedding, or None if an error occurred.
        """
        if not self.is_ready:
            logger.error(f"❌ Embedding provider '{self.provider_type}' is not ready.")
            return None

        try:
            result = await self.ai_client.embed(self.provider_type, text, model=self.model_name)
            if result and result.get('success'):
                return result.get('embedding')
            else:
                logger.error(f"❌ Error creating embedding with {self.provider_type}: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception during embedding: {e}")
            return None

class VectorDatabase:
    """Vector Database Manager."""
    
    def __init__(self, db_type: str = "chromadb", config: Dict[str, Any] = None):
        """
        Initializes the VectorDatabase.

        Args:
            db_type (str, optional): The type of vector database. Defaults to "chromadb".
            config (Dict[str, Any], optional): The configuration for the vector database. Defaults to None.
        """
        self.db_type = db_type
        self.config = config or {}
        self.client = None
        self.collection = None
        self.setup_database()
    
    def setup_database(self):
        """Sets up the vector database."""
        try:
            if self.db_type == "chromadb":
                self._setup_chromadb()
            elif self.db_type == "pinecone":
                self._setup_pinecone()
            elif self.db_type == "sqlite":
                self._setup_sqlite_vector()
            else:
                logger.warning(f"⚠️ Vector database not supported: {self.db_type}")
                
        except Exception as e:
            logger.error(f"❌ Error setting up vector database: {e}")
    
    def _setup_chromadb(self):
        """Sets up ChromaDB."""
        if not CHROMADB_AVAILABLE:
            logger.warning("⚠️ ChromaDB not available")
            return
            
        try:
            self.client = chromadb.PersistentClient(
                path=self.config.get("path", "./chroma_db"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            collection_name = self.config.get("collection_name", "synapse_documents")
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Synapse RAG Documents"}
            )
            
            logger.info("✅ ChromaDB is ready")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB setup error: {e}")
    
    def _setup_pinecone(self):
        """Sets up Pinecone."""
        if not PINECONE_AVAILABLE:
            logger.warning("⚠️ Pinecone not available")
            return
            
        try:
            api_key = self.config.get("api_key")
            environment = self.config.get("environment")
            
            if not api_key or not environment:
                logger.warning("⚠️ Pinecone API key and environment are required")
                return
            
            pinecone.init(api_key=api_key, environment=environment)
            index_name = self.config.get("index_name", "synapse-rag")
            
            # Create index if it doesn't exist
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=self.config.get("dimension", 1536),
                    metric="cosine"
                )
            
            self.collection = pinecone.Index(index_name)
            logger.info("✅ Pinecone is ready")
            
        except Exception as e:
            logger.error(f"❌ Pinecone setup error: {e}")
    
    def _setup_sqlite_vector(self):
        """Sets up SQLite for vector storage."""
        try:
            db_path = self.config.get("db_path", "./synapse_vectors.db")
            self.client = sqlite3.connect(db_path)
            
            # Create table for storing vectors
            self.client.execute("""
                CREATE TABLE IF NOT EXISTS document_vectors (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for searching
            self.client.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_source 
                ON document_vectors(source)
            """)
            
            self.client.commit()
            logger.info("✅ SQLite Vector Database is ready")
            
        except Exception as e:
            logger.error(f"❌ SQLite vector setup error: {e}")
    
    async def test_connection(self) -> bool:
        """
        Tests the connection to the vector database.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            if self.db_type == "chromadb":
                return self.client is not None and self.collection is not None
            elif self.db_type == "pinecone":
                return self.collection is not None
            elif self.db_type == "sqlite":
                return self.client is not None
            else:
                return False
        except Exception as e:
            logger.error(f"❌ Vector database connection test failed: {e}")
            return False
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """
        Adds documents to the vector database.

        Args:
            documents (List[Document]): A list of documents to add.

        Returns:
            bool: True if the documents were added successfully, False otherwise.
        """
        if not self.collection and not self.client:
            logger.error("❌ Vector database not available")
            return False
        
        try:
            if self.db_type == "chromadb":
                return await self._add_to_chromadb(documents)
            elif self.db_type == "pinecone":
                return await self._add_to_pinecone(documents)
            elif self.db_type == "sqlite":
                return await self._add_to_sqlite(documents)
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            return False
    
    async def _add_to_chromadb(self, documents: List[Document]) -> bool:
        """
        Adds documents to ChromaDB.

        Args:
            documents (List[Document]): A list of documents to add.

        Returns:
            bool: True if the documents were added successfully, False otherwise.
        """
        try:
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            embeddings = [doc.embedding for doc in documents if doc.embedding]
            metadatas = [asdict(doc.metadata) for doc in documents]
            
            if embeddings:
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
            else:
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas
                )
            
            logger.info(f"✅ Added {len(documents)} documents to ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"❌ ChromaDB add error: {e}")
            return False
    
    async def _add_to_pinecone(self, documents: List[Document]) -> bool:
        """
        Adds documents to Pinecone.

        Args:
            documents (List[Document]): A list of documents to add.

        Returns:
            bool: True if the documents were added successfully, False otherwise.
        """
        try:
            vectors = []
            for doc in documents:
                if doc.embedding:
                    vectors.append({
                        "id": doc.id,
                        "values": doc.embedding,
                        "metadata": {
                            "content": doc.content,
                            "source": doc.source,
                            **doc.metadata
                        }
                    })
            
            if vectors:
                self.collection.upsert(vectors=vectors)
                logger.info(f"✅ Added {len(vectors)} documents to Pinecone")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Pinecone add error: {e}")
            return False
    
    async def _add_to_sqlite(self, documents: List[Document]) -> bool:
        """
        Adds documents to SQLite.

        Args:
            documents (List[Document]): A list of documents to add.

        Returns:
            bool: True if the documents were added successfully, False otherwise.
        """
        try:
            cursor = self.client.cursor()
            
            for doc in documents:
                embedding_json = json.dumps(doc.embedding) if doc.embedding else "[]"
                metadata_json = json.dumps(doc.metadata)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO document_vectors 
                    (id, content, embedding, metadata, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (doc.id, doc.content, embedding_json, metadata_json, doc.source))
            
            self.client.commit()
            logger.info(f"✅ Added {len(documents)} documents to SQLite")
            return True
            
        except Exception as e:
            logger.error(f"❌ SQLite add error: {e}")
            return False
    
    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[SearchResult]:
        """
        Searches for similar documents.

        Args:
            query_embedding (List[float]): The embedding of the query.
            top_k (int, optional): The number of results to return. Defaults to 5.

        Returns:
            List[SearchResult]: A list of search results.
        """
        if not self.collection and not self.client:
            logger.error("❌ Vector database not available")
            return []
        
        try:
            if self.db_type == "chromadb":
                return await self._search_chromadb(query_embedding, top_k)
            elif self.db_type == "pinecone":
                return await self._search_pinecone(query_embedding, top_k)
            elif self.db_type == "sqlite":
                return await self._search_sqlite(query_embedding, top_k)
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            return []
    
    async def _search_chromadb(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """
        Searches in ChromaDB.

        Args:
            query_embedding (List[float]): The embedding of the query.
            top_k (int): The number of results to return.

        Returns:
            List[SearchResult]: A list of search results.
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            search_results = []
            for i in range(len(results['ids'][0])):
                doc_id = results['ids'][0][i]
                content = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                
                # Convert distance to score (0-1)
                score = 1 - distance
                
                document = Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata,
                    source=metadata.get('source', 'unknown')
                )
                
                search_results.append(SearchResult(
                    document=document,
                    score=score,
                    relevance=self._get_relevance(score)
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"❌ ChromaDB search error: {e}")
            return []
    
    async def _search_pinecone(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """
        Searches in Pinecone.

        Args:
            query_embedding (List[float]): The embedding of the query.
            top_k (int): The number of results to return.

        Returns:
            List[SearchResult]: A list of search results.
        """
        try:
            results = self.collection.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            search_results = []
            for match in results['matches']:
                metadata = match['metadata']
                
                document = Document(
                    id=match['id'],
                    content=metadata.get('content', ''),
                    metadata=metadata,
                    source=metadata.get('source', 'unknown')
                )
                
                search_results.append(SearchResult(
                    document=document,
                    score=match['score'],
                    relevance=self._get_relevance(match['score'])
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"❌ Pinecone search error: {e}")
            return []
    
    async def _search_sqlite(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """
        Searches in SQLite (cosine similarity).

        Args:
            query_embedding (List[float]): The embedding of the query.
            top_k (int): The number of results to return.

        Returns:
            List[SearchResult]: A list of search results.
        """
        try:
            cursor = self.client.cursor()
            cursor.execute("SELECT id, content, embedding, metadata, source FROM document_vectors")
            
            results = []
            query_embedding_np = np.array(query_embedding)
            
            for row in cursor.fetchall():
                doc_id, content, embedding_json, metadata_json, source = row
                
                try:
                    embedding = json.loads(embedding_json)
                    if embedding:
                        embedding_np = np.array(embedding)
                        
                        # Calculate cosine similarity
                        similarity = np.dot(query_embedding_np, embedding_np) / (
                            np.linalg.norm(query_embedding_np) * np.linalg.norm(embedding_np)
                        )
                        
                        metadata = json.loads(metadata_json) if metadata_json else {}
                        
                        document = Document(
                            id=doc_id,
                            content=content,
                            metadata=metadata,
                            source=source
                        )
                        
                        results.append(SearchResult(
                            document=document,
                            score=float(similarity),
                            relevance=self._get_relevance(float(similarity))
                        ))
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not process document {doc_id}: {e}")
                    continue
            
            # Sort results by score and select top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ SQLite search error: {e}")
            return []
    
    def _get_relevance(self, score: float) -> str:
        """
        Determines the relevance level based on the score.

        Args:
            score (float): The similarity score.

        Returns:
            str: The relevance level ('high', 'medium', or 'low').
        """
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        else:
            return "low"

class DocumentProcessor:
    """Document Processing & Chunking"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initializes the DocumentProcessor.

        Args:
            chunk_size (int, optional): The size of each chunk. Defaults to 1000.
            chunk_overlap (int, optional): The overlap between chunks. Defaults to 200.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, content: str, metadata: Dict[str, Any], source: str) -> List[Document]:
        """
        Processes a document and splits it into chunks.

        Args:
            content (str): The content of the document.
            metadata (Dict[str, Any]): The metadata of the document.
            source (str): The source of the document.

        Returns:
            List[Document]: A list of document chunks.
        """
        try:
            # Clean content
            cleaned_content = self._clean_content(content)
            
            # Split into chunks
            chunks = self._create_chunks(cleaned_content)
            
            # Create Document objects
            documents = []
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_doc_id(source, i, chunk)
                
                document = Document(
                    id=doc_id,
                    content=chunk,
                    metadata={
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_size": len(chunk)
                    },
                    source=source,
                    chunk_index=i
                )
                
                documents.append(document)
            
            logger.info(f"✅ Processed document {source} into {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error processing document: {e}")
            return []
    
    def _clean_content(self, content: str) -> str:
        """
        Cleans the content.

        Args:
            content (str): The content to clean.

        Returns:
            str: The cleaned content.
        """
        # Remove unnecessary whitespace
        content = " ".join(content.split())
        
        # Remove unwanted special characters
        import re
        content = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}]', '', content)
        
        return content.strip()
    
    def _create_chunks(self, content: str) -> List[str]:
        """
        Splits content into chunks.

        Args:
            content (str): The content to split.

        Returns:
            List[str]: A list of content chunks.
        """
        if len(content) <= self.chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            # Find a suitable split point (sentence or paragraph)
            if end < len(content):
                # Find the nearest sentence end
                sentence_end = content.rfind('.', start, end)
                paragraph_end = content.rfind('\n\n', start, end)
                
                if paragraph_end > sentence_end and paragraph_end > start:
                    end = paragraph_end
                elif sentence_end > start:
                    end = sentence_end + 1
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move to the next chunk (with overlap)
            start = end - self.chunk_overlap
            if start >= len(content):
                break
        
        return chunks
    
    def _generate_doc_id(self, source: str, chunk_index: int, content: str) -> str:
        """
        Generates an ID for a document.

        Args:
            source (str): The source of the document.
            chunk_index (int): The index of the chunk.
            content (str): The content of the chunk.

        Returns:
            str: The generated document ID.
        """
        # Use a hash of the source, chunk index, and content
        content_hash = hashlib.md5(f"{source}_{chunk_index}_{content}".encode()).hexdigest()
        return f"doc_{content_hash[:12]}"

class RAGSystem:
    """
    The main Retrieval-Augmented Generation (RAG) System.

    This class orchestrates the entire RAG pipeline, from document processing
    and embedding to searching and response generation. It integrates with
    various components like an `EmbeddingProvider`, a `VectorDatabase`, and
    a `DocumentProcessor`.

    While not directly coupled, this system is designed to work in tandem with a
    memory system like `ChatMemoryManager`. A typical workflow involves:
    1.  Retrieving conversation history from `ChatMemoryManager`.
    2.  Using the context from the history to formulate a query for this RAGSystem.
    3.  Searching for relevant documents with `search()`.
    4.  Generating a context-aware response with `generate_response()`.

    Attributes:
        config (Dict[str, Any]): The configuration dictionary.
        embedding_provider (EmbeddingProvider): The provider for text embeddings.
        vector_db (VectorDatabase): The vector database for document storage
                                    and retrieval.
        document_processor (DocumentProcessor): The tool for cleaning and
                                                chunking documents.
        cache (redis.Redis): A Redis client for caching search results.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initializes the RAGSystem.

        Args:
            config (Dict[str, Any], optional): The configuration for the RAG system. Defaults to None.
        """
        self.config = config or {}
        
        # Initialize components
        self.embedding_provider = EmbeddingProvider(
            provider_type=self.config.get("embedding_provider", "ollama"),
            model_name=self.config.get("embedding_model", "nomic-embed-text")
        )
        
        self.vector_db = VectorDatabase(
            db_type=self.config.get("vector_db", "chromadb"),
            config=self.config.get("vector_db_config", {})
        )
        
        self.document_processor = DocumentProcessor(
            chunk_size=self.config.get("chunk_size", 1000),
            chunk_overlap=self.config.get("chunk_overlap", 200)
        )
        
        # Cache system
        self.cache = redis.Redis(
            host=self.config.get("redis_host", "localhost"),
            port=self.config.get("redis_port", 6379),
            db=self.config.get("redis_db", 0),
            decode_responses=True
        )
        self.ai_client = get_client() # Add the unified client
        
        logger.info("🚀 RAG System is ready")
    
    async def initialize_system(self) -> Dict[str, Any]:
        """
        Initializes the system and tests connections.

        Returns:
            Dict[str, Any]: The status of the system.
        """
        status = {
            "embedding_provider": False,
            "vector_database": False,
            "cache_system": False,
            "system_ready": False
        }
        
        try:
            # Test embedding provider
            logger.info("🔍 Testing Embedding Provider connection...")
            status["embedding_provider"] = await self.embedding_provider.test_connection()
            
            # Test vector database
            logger.info("🔍 Testing Vector Database connection...")
            status["vector_database"] = await self.vector_db.test_connection()
            
            # Test cache system
            logger.info("🔍 Testing Cache System connection...")
            try:
                self.cache.ping()
                status["cache_system"] = True
                logger.info("✅ Cache System is ready")
            except Exception as e:
                logger.warning(f"⚠️ Cache System not available: {e}")
            
            # Check if the system is ready
            status["system_ready"] = status["embedding_provider"] and status["vector_database"]
            
            if status["system_ready"]:
                logger.info("🎉 RAG System is fully operational!")
            else:
                logger.warning("⚠️ RAG System is partially operational")
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error initializing system: {e}")
            return status
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Gets the system status.

        Returns:
            Dict[str, Any]: The status of the system.
        """
        try:
            status = {
                "embedding_provider": {
                    "type": self.embedding_provider.provider_type,
                    "model": self.embedding_provider.model_name,
                    "connected": await self.embedding_provider.test_connection()
                },
                "vector_database": {
                    "type": self.vector_db.db_type,
                    "connected": await self.vector_db.test_connection()
                },
                "cache_system": {
                    "connected": False
                },
                "document_processor": {
                    "chunk_size": self.document_processor.chunk_size,
                    "chunk_overlap": self.document_processor.chunk_overlap
                }
            }
            
            # Test cache
            try:
                self.cache.ping()
                status["cache_system"]["connected"] = True
            except:
                pass
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Could not get system status: {e}")
            return {}
    
    async def add_document(self, content: str, metadata: Dict[str, Any], source: str) -> bool:
        """
        Adds a document to the RAG system.

        Args:
            content (str): The content of the document.
            metadata (Dict[str, Any]): The metadata of the document.
            source (str): The source of the document.

        Returns:
            bool: True if the document was added successfully, False otherwise.
        """
        try:
            # Process the document
            documents = self.document_processor.process_document(content, metadata, source)
            
            if not documents:
                return False
            
            # Create embeddings
            for doc in documents:
                doc.embedding = await self.embedding_provider.get_embedding(doc.content)
            
            # Add to vector database
            success = await self.vector_db.add_documents(documents)
            
            if success:
                # Cache metadata
                cache_key = f"doc_meta:{source}"
                self.cache.setex(cache_key, 3600, json.dumps(metadata))
                
                logger.info(f"✅ Added document {source} successfully ({len(documents)} chunks)")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error adding document: {e}")
            return False
    
    async def search(self, query: str, top_k: int = 5, use_cache: bool = True) -> List[SearchResult]:
        """
        Searches for relevant documents.

        Args:
            query (str): The search query.
            top_k (int, optional): The number of results to return. Defaults to 5.
            use_cache (bool, optional): Whether to use the cache. Defaults to True.

        Returns:
            List[SearchResult]: A list of search results.

        Example:
            >>> rag = RAGSystem()
            >>> results = await rag.search("What is the Synapse architecture?")
            >>> for result in results:
            ...     print(f"Source: {result.document.source}, Score: {result.score}")
        """
        try:
            # Check cache
            if use_cache:
                cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.info("✅ Using result from cache")
                    cached_data = json.loads(cached_result)
                    results = []
                    for item in cached_data:
                        doc_data = item['document']
                        if doc_data.get('created_at'):
                            doc_data['created_at'] = datetime.fromisoformat(doc_data['created_at'])
                        doc = Document(**doc_data)
                        results.append(SearchResult(document=doc, score=item['score'], relevance=item['relevance']))
                    return results
            
            # Create query embedding
            query_embedding = await self.embedding_provider.get_embedding(query)
            if not query_embedding:
                logger.error("❌ Could not create query embedding")
                return []
            
            # Search in vector database
            results = await self.vector_db.search(query_embedding, top_k)
            
            # Cache results
            if use_cache and results:
                cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"

                # Custom JSON serializer for datetime
                def datetime_serializer(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")

                cache_data = json.dumps([asdict(result) for result in results], default=datetime_serializer)
                self.cache.setex(cache_key, 1800, cache_data)  # Cache for 30 minutes
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            return []
    
    async def generate_response(self, query: str, context_documents: List[Document], 
                              llm_provider: str = "ollama") -> RAGResponse:
        """
        Generates a response using RAG.

        Args:
            query (str): The user's query.
            context_documents (List[Document]): A list of context documents.
            llm_provider (str, optional): The LLM provider to use. Defaults to "ollama".

        Returns:
            RAGResponse: The generated response.

        Example:
            >>> search_results = await rag.search("What is Synapse?")
            >>> documents = [res.document for res in search_results]
            >>> response = await rag.generate_response("What is the Synapse architecture?", documents)
            >>> print(response.answer)
        """
        try:
            start_time = datetime.now()
            
            # Build context from relevant documents
            context = self._build_context(context_documents)
            
            # Create prompt for LLM
            prompt = self._create_rag_prompt(query, context)
            
            # Call LLM
            answer = await self._call_llm(prompt, llm_provider)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(context_documents)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return RAGResponse(
                answer=answer,
                sources=context_documents,
                confidence=confidence,
                context_used=context[:500] + "..." if len(context) > 500 else context,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return RAGResponse(
                answer="Sorry, an error occurred while processing your request.",
                sources=[],
                confidence=0.0,
                context_used="",
                processing_time=0.0
            )
    
    def _build_context(self, documents: List[Document]) -> str:
        """
        Builds the context from documents.

        Args:
            documents (List[Document]): A list of context documents.

        Returns:
            str: The built context.
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"Document {i} (from {doc.source}):\n{doc.content}\n")
        
        return "\n".join(context_parts)
    
    def _create_rag_prompt(self, query: str, context: str) -> str:
        """
        Creates a prompt for RAG.

        Args:
            query (str): The user's query.
            context (str): The context from relevant documents.

        Returns:
            str: The created prompt.
        """
        return f"""
You are an AI Assistant that helps answer questions using the provided documents.

Relevant Information:
{context}

Question: {query}

Please answer the question using only the information from the provided documents. If the information is not available, say that you cannot answer.

Answer:
"""
    
    async def _call_llm(self, prompt: str, provider: str) -> str:
        """
        Calls the LLM using the UnifiedAIClient.

        Args:
            prompt (str): The prompt for the LLM.
            provider (str): The LLM provider to use.

        Returns:
            str: The response from the LLM.
        """
        try:
            if not self.ai_client.get_provider(provider):
                return f"LLM provider '{provider}' is not supported or configured."

            messages = [{"role": "user", "content": prompt}]
            # Use a default model from config if available, otherwise let the strategy decide
            model = self.config.get(f"{provider}_model")
            
            result = await self.ai_client.generate_response(provider, messages, model=model)

            if result and result.get('success'):
                return result.get('content', 'No content received.')
            else:
                error_msg = result.get('error', 'An unknown error occurred')
                logger.error(f"❌ LLM call error with {provider}: {error_msg}")
                return f"An error occurred while calling the {provider} LLM."

        except Exception as e:
            logger.error(f"❌ Exception during LLM call: {e}")
            return "An unexpected error occurred while calling the LLM."
    
    def _calculate_confidence(self, documents: List[Document]) -> float:
        """
        Calculates the confidence score.

        Args:
            documents (List[Document]): A list of context documents.

        Returns:
            float: The confidence score.
        """
        if not documents:
            return 0.0
        
        # Calculate based on the number of relevant documents and the diversity of sources
        unique_sources = len(set(doc.source for doc in documents))
        total_docs = len(documents)
        
        # Confidence = (number of documents * diversity of sources) / 10
        confidence = (total_docs * unique_sources) / 10.0
        
        return min(confidence, 1.0)  # Limit to 1.0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Gets statistics of the RAG system.

        Returns:
            Dict[str, Any]: A dictionary of statistics.
        """
        try:
            stats = {
                "total_documents": 0,
                "total_chunks": 0,
                "embedding_provider": self.embedding_provider.provider_type,
                "vector_db_type": self.vector_db.db_type,
                "cache_status": "connected" if self.cache.ping() else "disconnected"
            }
            
            # Get statistics from the vector database
            if self.vector_db.db_type == "chromadb" and self.vector_db.collection:
                stats["total_chunks"] = self.vector_db.collection.count()
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return {"error": str(e)}

# Factory function for creating a RAG System
def create_rag_system(config: Dict[str, Any] = None) -> RAGSystem:
    """
    Creates a RAG System instance.

    Args:
        config (Dict[str, Any], optional): The configuration for the RAG system. Defaults to None.

    Returns:
        RAGSystem: A RAG System instance.
    """
    return RAGSystem(config)

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = {
        "embedding_provider": "ollama",
        "embedding_model": "nomic-embed-text",
        "vector_db": "chromadb",
        "vector_db_config": {
            "path": "./chroma_db",
            "collection_name": "synapse_documents"
        },
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "redis_host": "localhost",
        "redis_port": 6379,
        "ollama_model": "llama3.1:8b"
    }
    
    async def test_rag():
        """Tests the RAG system."""
        rag = create_rag_system(config)
        
        # Add a sample document
        sample_content = """
        The Synapse Backend Monolith is an architecture designed to be the central hub of the entire system.
        This system allows for rapid initial development and allows for important components to be gradually
        separated into Microservices later on.
        
        The system uses Python with FastAPI as its core, as it is a high-performance framework
        that is well-suited for API and AI work.
        """
        
        metadata = {
            "title": "Synapse Architecture",
            "author": "Orion Senior Dev",
            "category": "architecture"
        }
        
        success = await rag.add_document(sample_content, metadata, "architecture_doc")
        print(f"Document added successfully: {success}")
        
        # Test search
        results = await rag.search("Synapse architecture", top_k=3)
        print(f"Found {len(results)} relevant documents:")
        
        for result in results:
            print(f"- {result.document.source}: {result.score:.3f}")
        
        # Test response generation
        if results:
            response = await rag.generate_response(
                "What is the Synapse Backend Monolith?",
                [result.document for result in results]
            )
            print(f"\nAnswer: {response.answer}")
            print(f"Confidence: {response.confidence:.3f}")
            print(f"Processing time: {response.processing_time:.2f} seconds")
    
    # Run test
    asyncio.run(test_rag())
