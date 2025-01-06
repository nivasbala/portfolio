# This file has the URLs for searching
from nltk import toolbox
from ddtrace import tracer

from logger import logger
from langchain_community.document_loaders import UnstructuredURLLoader
from ddtrace.llmobs.decorators import llm, workflow, task, agent, tool, retrieval



# TODO - Update this to use the library and update the URLs from the url loading tool

# Datadog URL data from the website
datadog_docs_urls = ['https://www.datadoghq.com/pricing/',
                     'https://www.datadoghq.com/pricing/list/',
                     'https://docs.datadoghq.com/account_management/billing/',
                     'https://docs.datadoghq.com/account_management/billing/pricing/'
                     'https://docs.datadoghq.com/account_management/billing/containers/',
                     'https://docs.datadoghq.com/account_management/billing/serverless/']


#@tracer.wrap("load_urls", service="dd-llm-app")
@tool(name="load_urls")
def load_website_urls(site_urls):

    # Load the URLs from the list - TODO: Convert this to read from a JSON file
    logger.info(f"Loading Site Information from URL List")
    loader = UnstructuredURLLoader(urls=site_urls)
    data = loader.load()
    # print(data)
    return data
