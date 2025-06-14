# @Author: Dhaval Patel Copyrights Codebasics Inc. and LearnerX Pvt Ltd.

from uuid import uuid4
from dotenv import load_dotenv
from pathlib import Path
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

load_dotenv()

# Constants
CHUNK_SIZE = 300  # or even 300
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTORSTORE_DIR = Path(__file__).parent / "resources/vectorstore"
COLLECTION_NAME = "real_estate"

llm = None
vector_store = None


def initialize_components():
    global llm, vector_store

    if llm is None:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7, max_tokens=300, top_p=0.9)

    # if vector_store is None:
    #     ef = HuggingFaceEmbeddings(
    #         model_name=EMBEDDING_MODEL,
    #         model_kwargs={"trust_remote_code": True}
    #     )

    #     # vector_store = Chroma(
    #     #     collection_name=COLLECTION_NAME,
    #     #     embedding_function=ef,
    #     #     #persist_directory=str(VECTORSTORE_DIR)
    #     # )
    #     from langchain.docstore.in_memory import InMemoryDocstore
    #     vector_store = FAISS.from_documents([], ef)



def process_urls(urls):
    """
    This function scraps data from a url and stores it in a vector db
    :param urls: input urls
    :return:
    """
    yield "Initializing Components"
    initialize_components()

    yield "Loading data...✅"
    loader = UnstructuredURLLoader(urls=urls)
    data = loader.load()

    yield "Splitting text into chunks...✅"
    text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ".", " "],
    chunk_size=CHUNK_SIZE,
    chunk_overlap=50  # You can also try 100 if needed
    )

    docs = text_splitter.split_documents(data)

    yield "Creating vector store from documents...✅"
    global vector_store
    ef = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"trust_remote_code": True}
    )
    vector_store = FAISS.from_documents(docs, ef)

    yield "Add chunks to vector database...✅"
    uuids = [str(uuid4()) for _ in range(len(docs))]
    vector_store.add_documents(docs, ids=uuids)

    yield "Done adding docs to vector database...✅"


def generate_answer(query):
    if not vector_store:
        raise RuntimeError("Vector database is not initialized ")

    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    docs = retriever.get_relevant_documents(query)
    print("\n--- Retrieved Documents ---")
    for i, doc in enumerate(docs, 1):
        print(f"\nDoc {i}:\n{doc.page_content[:1000]}")  # truncate for readability

    chain = RetrievalQAWithSourcesChain.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff"  # You can later test "map_reduce" or "refine" too
    )
    result = chain.invoke({"question": query}, return_only_outputs=True)
    sources = result.get("sources", "")

    return result['answer'], sources


if __name__ == "__main__":
    urls = [
        "https://www.cnbc.com/2024/12/21/how-the-federal-reserves-rate-policy-affects-mortgages.html",
        "https://www.cnbc.com/2024/12/20/why-mortgage-rates-jumped-despite-fed-interest-rate-cut.html"
    ]

    # Run the generator to completion and print status messages
    for status in process_urls(urls):
        print(status)

    answer, sources = generate_answer("Tell me what was the 30 year fixed mortagate rate along with the date?")
    print(f"Answer: {answer}")
    print(f"Sources: {sources}")