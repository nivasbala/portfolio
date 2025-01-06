import os

import streamlit as st
import time
import json
import random
import pprint

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


# Env Variables from Secrets File
from load_urls import datadog_docs_urls, load_website_urls
from classify_question import classify_question

# Datadog Python Libraries
from ddtrace import tracer
from logger import logger

# Datadog LLM Observability Libraries
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import llm, workflow, task, agent, tool, retrieval, embedding

# Global Variables
dd_llm_app = ""
generic_llm = {}

# Setup Tracing
#tracer.configure(
#    uds_path="/var/run/datadog/apm.socket",
#    dogstatsd_url="unix:///var/run/datadog/dsd.socket"
#)

tracer.configure(hostname="agent", port=8126)

# Create Embeddings
@task(name="create_embedding_from_urls")
def create_embeddings(data):
    # split the text into Chunks for Embedding
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
    docs = text_splitter.split_documents(data)
    # print(docs)
    # print(len(docs))
    return docs

# Create Vector Database - TODO: Change this to Pinecone (right now uses Chroma)
@task(name="create_vector_db")
def create_vector_db(docs, openai_api_key):

    # Create OpenAIEmbeddings
    embedding = OpenAIEmbeddings(openai_api_key=openai_api_key)

    # Create Vector DB from chucks created above and store in Chroma Vector DB
    vectorstore = Chroma.from_documents(documents=docs, embedding=embedding)

    # Create Retriever to do similarity search - k value being number of similar docs returned
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})
    # retrieved_docs = retriever.invoke("What are the type of APM licenses available?")
    # print(len(retrieved_docs))

    # for i in range(len(retrieved_docs)):
    #    print(f"Doc {i}\n")
    #    print(retrieved_docs[i].page_content)
    #    print("-------\n\n")
    return retriever

def create_llm_model(model_type, openai_api_key):

    llm = {}

    if model_type == "openai":
        llm = OpenAI(openai_api_key=openai_api_key, temperature=0.4, max_tokens=200)
    elif model_type == "classify":
        #llm = OpenAI(openai_api_key=openai_api_key, temperature=0.4)
        llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key, temperature=0.4)
    else:
        logger.error(f"Model Not found {model_type}")
    return llm

# Function that translates given text to a french or spanish
def translate_to_language(text):

    prompt = PromptTemplate(
        input_variables=["text"],
        template="Translate the following text to French or spanish randomly: {text}"
    )

    llm = OpenAI(temperature=0.5)

    # Create a chain with the prompt template and the LLM
    chain = LLMChain(llm=llm, prompt=prompt)

    # Define the text and target language
    text_str = text

    # Run the chain
    translated_text = chain.run({"text": text_str})
    return translated_text


#
# Function to Answer Datadog Question
# Calls the Rag Chain passed with the query
#
@workflow(name="answer_dd_question")
def answer_datadog_question(rag_chain, query):

    response = ""

    with tracer.trace("answer-question"):

        # Introduce Error randomly
        if random.random() < 0.2:
            time.sleep(5)
            try:
                raise Exception("Failed categorizing the user request")
            except ValueError as e:
                logger.error(f"Caught exception: {e}")
                return response
        else:
            chain_output = rag_chain.invoke({"input": query})
            response = str(chain_output["answer"])

        # Randomly return response is a different language
        if random.random() < 0.3:
            response = translate_to_language(response)

    return response

#
# StreamLit Chat App - Main App
# This App Does the following
# 1. Calls the Tool - Classify the Question
# 2. Calls the LLM to answer the question
#
@agent(name="datadog_assistant")
def datadog_chatapp(llm, classify_model, retriever):

    # Create Stream Lit App
    st.title("Datadog Docs - LLM App")
    st.write("Welcome to your Your Datadog Assistant!")

    # Get Input
    query = st.chat_input("Ask a Datadog related Question: ")

    # Create System Prompt to be used
    system_prompt = (
        "You are an assistant for question-answering tasks."
        "Use the following pieces of retrieved context to answer the question."
        "If you don't know the answer, say that you don't know."
        "Use five sentences maximum and keep the answer concise."
        "Return the response in markdown format."
        "\n\n"
        "Use the context provided to answer the question."
        "{context}"
    )
    # Create the Prompt in OpenAI Format
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # Evaluate the Span
    if query:

        # Classify the Question
        question_classification = classify_question(classify_model, query)
        #LLMObs.annotate(input_data=question_classification)
        st.text("The Question Classified as :")
        st.markdown(question_classification, unsafe_allow_html=True)
        logger.info(f"Question Classified as {question_classification}")

        # Create the LLM Chain
        ## 1. Create LLM with Prompt create above
        question_answer_chain = create_stuff_documents_chain(llm, prompt)

        ## 2. Create RAG Chain including the question chain with retriever
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        # Call LLM Chain
        # Invoke the chain with a question
        response = answer_datadog_question(rag_chain, query)

        # Print the Response
        #print(json.dumps(response, indent=4))
        #pprint.pprint(response)

        # Datadog - Annotate Response from LLM
        #LLMObs.annotate(output_data=str(response["answer"]))

        LLMObs.annotate(input_data=query, output_data=response)

        #st.write(response["answer"])
        logger.info(f"Query: {query}")
        logger.info(f"Answer: {response}")

        # Print the Question
        st.text("The Question is:")
        st.text(query)
        st.text("The Answer is:")
        st.markdown(response, unsafe_allow_html=True)

# Main Function
@tracer.wrap("main", service="dd-llm-app")
def main():

    # Load Environment Variables
    load_dotenv()
    dd_llm_app = os.getenv("DD_LLMOBS_ML_APP")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_site = os.getenv("DD_SITE")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Enable Datadog APM

    logger.info(f"LLM App {dd_llm_app} Started")
    # Enable Datadog LLM Observability
    LLMObs.enable(
        ml_app=dd_llm_app,
        api_key=dd_api_key,
        site=dd_site
    )

    # Load Website URLs
    data = load_website_urls(datadog_docs_urls)

    # Create Embeddings
    docs = create_embeddings(data)

    # Create Vector Database
    retriever = create_vector_db(docs, openai_api_key)

    # Create Classify Model
    generic_llm = create_llm_model("classify", openai_api_key)

    # Create the LLM to answer questions
    llm = create_llm_model("openai", openai_api_key)

    # Call the Datadog Chat App
    datadog_chatapp(llm, generic_llm, retriever)

if __name__ == "__main__":
    main()

