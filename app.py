from dotenv import load_dotenv
load_dotenv()
from langchain_community.document_loaders import PyPDFLoader,PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
import streamlit as st

# History persisting 
if "document_uploaded" not in st.session_state:
    st.session_state.document_uploaded = False

if "agent" not in st.session_state:
    st.session_state.agent = None

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if 'history' not in st.session_state:
    st.session_state.history=[]
def process_document(path):
    # Document Loader
    loader=PyPDFDirectoryLoader(path)
    docs=loader.load()

    # Text splitter

    splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)

    chunks=splitter.split_documents(docs)


    # Convert into embeddings

    embeddings= GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview")

    # Putting it in vector store

    vector_store=InMemoryVectorStore.from_documents(documents=chunks,embedding=embeddings)

    # agent-- llm-->tools-->system_prompt

    # creating tool -- for searching info in vectorDB

    @tool
    def retrieve_tool(query:str):
        """ Tools helps to retrieve the relevant data of the PDF document  """
        print("Tools called :",query)
        search=vector_store.similarity_search(query=query,k=4)
        context=""
        for docs in search:
            context+=docs.page_content+"\n\n"
        return context

    # llm model
    llm=ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")

    # System prompt
    system_prompt="""You are a helpful assistant that answers questions using retrieved context. 
        My knowledge base consists of the details from the uploaded document. 
        ALWAYS use the `retrieve_context` tool for questions requiring external knowledge."""

    memory= InMemorySaver()

    agent=create_agent(
    tools=[retrieve_tool],
    model=llm,
    system_prompt=system_prompt,
    checkpointer=memory
    )
    st.session_state.agent=agent
    st.session_state.document_uploaded=True

### upload ui 
if not  st.session_state.document_uploaded:
    uploaded=st.file_uploader(label="Select PDF Files",type=["pdf"],accept_multiple_files=True)
    if uploaded:
        with st.spinner("Processing..."):
            path="doc_files/"
            for file in uploaded:
                with open(path + file.name,"wb") as f:
                    f.write(file.getvalue())
            process_document(path)
            st.rerun()
### chat ui

if st.session_state.document_uploaded and st.session_state.agent:
    for message in st.session_state.history:
        role=message.get("role")
        content=message.get("content")
        st.chat_message(role).markdown(content)
    query=st.chat_input("Ask me Anything related to uploaded document..")
    if query:
        st.session_state.history.append({"role":"user", "content":query})
        st.chat_message("user").markdown(query)
        response=st.session_state.agent.invoke({"messages":[{'role':'user','content':query}]},{"configurable":{"thread_id":1}})
        res=response["messages"][-1].content[0]["text"]
        st.chat_message("ai").markdown(res)
        st.session_state.history.append({"role":"ai", "content":res})



# while True:
#     query=input("User:")
#     if query.lower()=="quit":
#         print("Bye!!")
#         break
#     response=agent.invoke({"messages":[{'role':'user','content':query}]},{"configurable":{"thread_id":1}})
#     res=response["messages"][-1].content[0]["text"]
#     print("AI:",res)






