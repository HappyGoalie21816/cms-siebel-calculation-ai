import os
import re
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
# Load environment variables
load_dotenv()

#comment
def evaluate_expressions(text):
    """Parses and safely evaluates mathematical expressions wrapped in [[...]]."""
    variables = {}
    last_ndigits = [None]
    
    def my_round(number, ndigits=None):
        last_ndigits[0] = ndigits
        return round(number, ndigits)
        
    allowed_names = {
        'round': my_round,
        'abs': abs,
        'min': min,
        'max': max,
    }
    
    pattern = re.compile(r'\[\[(.*?)\]\]')
    
    def replacer(match):
        expr_content = match.group(1).strip()
        
        # Replace common math symbols
        expr_content = expr_content.replace('×', '*').replace('÷', '/')
        
        if '=' in expr_content:
            parts = expr_content.split('=', 1)
            var_name = parts[0].strip()
            expr = parts[1].strip()
        else:
            var_name = None
            expr = expr_content
            
        try:
            last_ndigits[0] = None
            eval_env = {**allowed_names, **variables}
            val = eval(expr, {"__builtins__": None}, eval_env)
            
            if var_name:
                variables[var_name] = val
                
            if last_ndigits[0] is not None and isinstance(val, (int, float)):
                return f"{val:,.{last_ndigits[0]}f}"
            if isinstance(val, float):
                if val.is_integer():
                    return f"{int(val):,}"
                s = f"{val:,.4f}"
                if '.' in s:
                    s = s.rstrip('0').rstrip('.')
                return s
            if isinstance(val, int):
                return f"{val:,}"
            return str(val)
        except Exception as e:
            return f"[Error: {e} in '{expr_content}']"
            
    return pattern.sub(replacer, text)



def initialize_vector_store(data_path="data/"):
    """Loads documents, creates embeddings, and builds a local FAISS vector store."""
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
    vector_store = FAISS.from_documents(splits, embeddings)
    
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
        "You are an expert financial calculation engine. Your task is to explain mathematical "
        "calculations using ONLY the formulas and rules provided in the context document. "
        "Do not invent your own formulas. \n\n"
        "CRITICAL INSTRUCTION FOR CALCULATIONS:\n"
        "LLMs are prone to basic arithmetic errors. Therefore, you MUST NOT write down pre-calculated numbers or intermediate results. "
        "Instead, write every calculation/arithmetic expression you want to evaluate inside double square brackets, like this: [[expression]]. "
        "A post-processing calculator will automatically evaluate the expression and replace it with the correct value.\n\n"
        "Rules for expression writing:\n"
        "1. Write formulas by substituting the variables directly: e.g. [[18.71 * 365]] or [[A / 12]].\n"
        "2. To store intermediate results so you can use them in subsequent steps, assign them to a variable: e.g. [[A = 18.71 * 365]], then in the next step write [[A / 12]].\n"
        "3. Use round(expression, decimal_places) to round values: e.g. [[round(18.71 * 365, 2)]].\n"
        "4. Put currency symbols or units OUTSIDE the double brackets: e.g. £[[round(A, 2)]], NOT [[£round(A, 2)]].\n"
        "5. Do not write commas as thousands separators inside the brackets (write [[6829.15]], NOT [[6,829.15]]).\n"
        "6. Do not include spaces inside variable names. Keep expressions simple and standard.\n\n"
        "Example output structure:\n"
        "1. Multiply daily liability by number of days: £18.71 * 365 = £[[A = round(18.71 * 365, 2)]]\n"
        "2. Divide by number of periods: £[[A]] / 12 = £[[B = round(A / 12, 4)]]\n"
        "Therefore, the calculated OGM value is approximately £[[round(B, 2)]].\n\n"
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Here are the input variables:\n{input}\n\nPlease find the relevant formula in the context and explain the step-by-step calculation.")
    ])

    # Create Retrieval Chain
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    # Execute Chain
    response = rag_chain.invoke({"input": input_data})
    raw_answer = response["answer"]
    
    # Process mathematical expressions to ensure accurate calculation results
    processed_answer = evaluate_expressions(raw_answer)
    return processed_answer