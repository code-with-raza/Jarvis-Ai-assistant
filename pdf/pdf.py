import os
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import Chroma

# Embeddings choice:
# - If you have OpenAI embeddings key: use OpenAIEmbeddings
# - If not, I recommend local embeddings (sentence-transformers)
#
# For simplest setup (and since you're using OpenRouter for chat),
# we'll use HuggingFace local embeddings to avoid needing a second API.
from langchain_community.embeddings import HuggingFaceEmbeddings


def _embeddings():
    # If you have OpenAI API key and want to use OpenAI embeddings, uncomment below:
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _vectorstore(persist_dir: str, collection_name: str) -> Chroma:
    os.makedirs(persist_dir, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        persist_directory=persist_dir,
        embedding_function=_embeddings(),
    )


def index_pdf(
    pdf_path: str,
    persist_dir: str = "rag_db",
    collection_name: str = "jarvis_pdfs",
    source_id: Optional[str] = None,
) -> int:
    """
    Load PDF, split into chunks, store in Chroma.
    Returns number of chunks stored.
    """
    loader = PyPDFLoader(pdf_path, mode="page")
    docs = loader.load()

    # add source_id metadata
    sid = source_id or os.path.basename(pdf_path)
    for d in docs:
        d.metadata["source_id"] = sid

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(docs)

    vs = _vectorstore(persist_dir, collection_name)
    vs.add_documents(chunks)
    vs.persist()
    return len(chunks)


def retrieve_context(
    question: str,
    persist_dir: str = "rag_db",
    collection_name: str = "jarvis_pdfs",
    k: int = 4,
    source_id: Optional[str] = None,
) -> List[str]:
    """
    Returns top-k chunk texts (optionally filtered by source_id).
    """
    vs = _vectorstore(persist_dir, collection_name)

    # build search kwargs
    search_kwargs = {"k": k}
    if source_id:
        search_kwargs["filter"] = {"source_id": source_id}

    docs = vs.similarity_search(question, **search_kwargs)
    return [d.page_content for d in docs]
