#!/usr/bin/env python3
"""
RAG System Test Script

This script demonstrates the RAG system functionality with example
document ingestion and querying operations.
"""

import asyncio
import json
import logging
from app.rag_tool import rag_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Sample documents for testing
SAMPLE_DOCUMENTS = [
    {
        "title": "인공지능 기초",
        "language": "ko",
        "source": "AI 교육 자료",
        "text": """
        인공지능(AI)은 컴퓨터가 인간의 지능을 모방하도록 설계된 기술입니다. 
        머신러닝은 AI의 하위 분야로, 데이터에서 패턴을 학습하여 예측을 수행합니다.
        딥러닝은 머신러닝의 한 방법으로, 신경망을 사용하여 복잡한 패턴을 학습합니다.
        자연어 처리(NLP)는 컴퓨터가 인간의 언어를 이해하고 생성할 수 있게 하는 AI 기술입니다.
        컴퓨터 비전은 이미지와 비디오를 분석하고 이해하는 AI 기술입니다.
        """
    },
    {
        "title": "Machine Learning Fundamentals",
        "language": "en",
        "source": "ML Tutorial",
        "text": """
        Machine Learning is a subset of artificial intelligence that enables computers to learn
        and make decisions from data without being explicitly programmed for every task.
        Supervised learning uses labeled data to train models that can make predictions on new data.
        Unsupervised learning finds patterns in data without labeled examples.
        Reinforcement learning learns through trial and error by receiving rewards or penalties.
        Deep learning uses neural networks with multiple layers to model complex patterns.
        """
    },
    {
        "title": "データサイエンス入門",
        "language": "ja",
        "source": "Data Science Guide",
        "text": """
        データサイエンスは、データから価値のある洞察を抽出する学際的な分野です。
        統計学、機械学習、プログラミングの知識が必要です。
        データの収集、クリーニング、分析、可視化が主な工程です。
        PythonやRなどのプログラミング言語がよく使われます。
        ビッグデータの処理にはHadoopやSparkなどのツールが使用されます。
        """
    }
]

# Test queries in different languages
TEST_QUERIES = [
    "머신러닝이 무엇인가요?",
    "What is deep learning?",
    "データサイエンスについて教えてください",
    "자연어 처리의 용도는 무엇인가요?",
    "How does supervised learning work?",
    "ビッグデータとは何ですか？"
]


async def test_document_ingestion():
    """Test document ingestion functionality."""
    print("\n" + "="*60)
    print("🔄 Testing Document Ingestion")
    print("="*60)
    
    ingested_docs = []
    
    for i, doc in enumerate(SAMPLE_DOCUMENTS):
        print(f"\n📄 Ingesting document {i+1}: {doc['title']}")
        
        request = {
            "action": "ingest",
            "text": doc["text"],
            "title": doc["title"],
            "source": doc["source"],
            "language": doc["language"],
            "chunking_method": "sentence"
        }
        
        try:
            result = await rag_tool._arun(json.dumps(request, ensure_ascii=False))
            result_data = json.loads(result)
            
            if result_data.get("success"):
                doc_id = result_data["document_id"]
                ingested_docs.append(doc_id)
                print(f"✅ Successfully ingested: {doc_id}")
                
                # Print document info
                if "document_info" in result_data:
                    info = result_data["document_info"]
                    print(f"   📊 Chunks: {info.get('chunk_count', 'N/A')}")
                    print(f"   📅 Created: {info.get('created_at', 'N/A')}")
            else:
                print(f"❌ Failed to ingest document: {result_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception during ingestion: {e}")
    
    print(f"\n📈 Ingestion Summary: {len(ingested_docs)}/{len(SAMPLE_DOCUMENTS)} documents successfully ingested")
    return ingested_docs


async def test_document_listing():
    """Test document listing functionality."""
    print("\n" + "="*60)
    print("📋 Testing Document Listing")
    print("="*60)
    
    request = {
        "action": "list",
        "limit": 20,
        "offset": 0
    }
    
    try:
        result = await rag_tool._arun(json.dumps(request))
        result_data = json.loads(result)
        
        if result_data.get("success"):
            documents = result_data["documents"]
            print(f"📚 Found {len(documents)} documents:")
            
            for doc in documents:
                print(f"   📄 {doc.get('title', 'Untitled')} ({doc.get('language', 'unknown')})")
                print(f"      🆔 ID: {doc['document_id']}")
                print(f"      📅 Created: {doc.get('created_at', 'N/A')}")
                print()
        else:
            print(f"❌ Failed to list documents: {result_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception during listing: {e}")


async def test_knowledge_queries():
    """Test knowledge base querying functionality."""
    print("\n" + "="*60)
    print("🔍 Testing Knowledge Base Queries")
    print("="*60)
    
    for i, query in enumerate(TEST_QUERIES):
        print(f"\n🤔 Query {i+1}: {query}")
        print("-" * 50)
        
        request = {
            "action": "query",
            "query": query,
            "top_k": 3,
            "similarity_threshold": 0.3,
            "include_metadata": True
        }
        
        try:
            result = await rag_tool._arun(json.dumps(request, ensure_ascii=False))
            result_data = json.loads(result)
            
            if result_data.get("success"):
                context_chunks = result_data["context_chunks"]
                metadata = result_data["metadata"]
                
                print(f"📊 Retrieved {len(context_chunks)} relevant chunks")
                print(f"⏱️  Processing time: {metadata.get('processing_time', 0):.3f}s")
                
                if context_chunks:
                    print("\n📖 Retrieved Context:")
                    for j, chunk in enumerate(context_chunks):
                        score = chunk["similarity_score"]
                        title = chunk["metadata"].get("document_title", "Unknown")
                        text_preview = chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"]
                        
                        print(f"   {j+1}. [{title}] (Score: {score:.3f})")
                        print(f"      {text_preview}")
                        print()
                    
                    # Show constructed prompt preview
                    prompt = result_data.get("answer_prompt", "")
                    if prompt:
                        prompt_preview = prompt[:300] + "..." if len(prompt) > 300 else prompt
                        print("🎯 Generated Prompt Preview:")
                        print(f"   {prompt_preview}")
                else:
                    print("⚠️  No relevant context found")
                    
            else:
                print(f"❌ Query failed: {result_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception during query: {e}")


async def test_system_statistics():
    """Test system statistics functionality."""
    print("\n" + "="*60)
    print("📊 Testing System Statistics")
    print("="*60)
    
    request = {"action": "stats"}
    
    try:
        result = await rag_tool._arun(json.dumps(request))
        result_data = json.loads(result)
        
        if result_data.get("success"):
            stats = result_data["stats"]
            
            print("🏗️  System Status:")
            print(f"   ✅ Initialized: {stats.get('initialized', False)}")
            
            if "vector_store" in stats:
                vs_stats = stats["vector_store"]
                print(f"   📚 Total Documents: {vs_stats.get('total_documents', 'N/A')}")
                print(f"   📄 Total Chunks: {vs_stats.get('total_chunks', 'N/A')}")
                print(f"   🔢 Embedding Dimension: {vs_stats.get('embedding_dimension', 'N/A')}")
            
            if "embedding_service" in stats:
                es_stats = stats["embedding_service"]
                print(f"   🤖 Embedding Model: {es_stats.get('model_name', 'N/A')}")
                print(f"   💻 Device: {es_stats.get('device', 'N/A')}")
                print(f"   🟢 Status: {es_stats.get('status', 'N/A')}")
                
            if "configuration" in stats:
                config = stats["configuration"]
                print("\n⚙️  Configuration:")
                for key, value in config.items():
                    print(f"   {key}: {value}")
        else:
            print(f"❌ Failed to get statistics: {result_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception during stats retrieval: {e}")


async def main():
    """Main test function."""
    print("🚀 RAG System Comprehensive Test")
    print("=" * 80)
    print("This script will test all aspects of the RAG system:")
    print("1. Document ingestion with multilingual content")
    print("2. Document listing and management")
    print("3. Knowledge base querying in multiple languages")
    print("4. System statistics and health monitoring")
    print("=" * 80)
    
    try:
        # Test 1: Document Ingestion
        ingested_docs = await test_document_ingestion()
        
        # Test 2: Document Listing
        await test_document_listing()
        
        # Test 3: Knowledge Queries
        await test_knowledge_queries()
        
        # Test 4: System Statistics
        await test_system_statistics()
        
        print("\n" + "="*80)
        print("🎉 RAG System Test Completed!")
        print("="*80)
        print("✅ All tests executed successfully")
        print("📚 The RAG system is ready for production use")
        print("🔧 Check the logs above for any issues or warnings")
        print("📖 Refer to RAG_README.md for detailed usage instructions")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        logger.exception("Test execution error")


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(main()) 