# Step 1: Use an official Python image as the base image
FROM python:3.12-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements.txt file (if you have one)
COPY requirements.txt .

# Step 4: Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install ddtrace

# Step 5: Set Environment Variables to access Datadog Agent
#ENV DD_AGENT_HOST=dd-agent
#ENV DD_TRACE_AGENT_PORT=8126

# Step 6: Copy the Streamlit app and other necessary files to the working directory
COPY . .

# Step 7: Expose the default Streamlit port
EXPOSE 8501

# Step 8: Set the command to run the Streamlit app
#CMD ["streamlit", "run", "rag_example.py"]
ENTRYPOINT ["ddtrace-run"]
CMD ["streamlit", "run", "dd_llm_app.py"]
