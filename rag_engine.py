import os
import re
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
# Load environment variables
load_dotenv()


def initialize_vector_store(data_path="data/", persist_directory="./chroma_db"):
    """Loads documents, creates embeddings, and builds a local Chroma vector store."""
    print("Path:", os.path.abspath(data_path))
    if not os.path.exists(data_path) or not os.listdir(data_path):
        return None

    # 1. Load Documents (PDFs and TXTs)
    pdf_loader = PyPDFDirectoryLoader(data_path)
    pdf_docs = pdf_loader.load()
    
    txt_loader = DirectoryLoader(data_path, glob="**/*.txt", loader_cls=TextLoader)
    txt_docs = txt_loader.load()
    
    # Combine all loaded documents
    docs = pdf_docs + txt_docs
    
    if not docs:
        raise ValueError("No readable documents found in the data folder.")
    # 2. Split Text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    # 3. Create Embeddings and Vector Store
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_store = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=persist_directory)
    
    return vector_store

def get_calculation_explanation(vector_store, input_data):
    """Creates the RAG chain and asks it to explain calculations using retrieved formulas."""
    llm = ChatOpenAI(
        base_url="http://localhost:1234/v1", 
        api_key="lm-studio", # Required by the class, but LM Studio ignores it
        model="meta-llama-3-8b-instruct:2", # LM Studio will automatically use whichever model you have loaded
        temperature=0.1 
    )

    # Define the Prompt Template tailored for formula extraction
    system_prompt = (
        "You are a financial expert in CMS (Child Maintenance Service) or CMG (Child Maintenance Group). Your task is to explain mathematical "
        "calculations using ONLY the formulas and rules provided in the context document for the target component. "
        "Do not invent your own formulas. \n\n"
        "CRITICAL INSTRUCTION:\n"
        "You MUST NOT perform calculations. The final calculated result is provided to you in the input prompt. "
        "Your task is to:\n"
        "1. Summarize the formula used.\n"
        "2. Explain all the components of the formula used in detail.\n"
        "3. Explicitly state where the component values can be seen in the existing UI (e.g., 'calculation applet').\n"
        "4. Cite proper references to the document when generating the response.\n\n"
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Here is the calculation context and final result:\n{input}\n\nPlease summarize the formula, explain its components, cite the source document, and note where these values appear in the UI.")
    ])

    # Create Retrieval Chain
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    # Execute Chain
    response = rag_chain.invoke({"input": input_data})
    return response["answer"]