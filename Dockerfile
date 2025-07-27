# Use a slim Python base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install git, which is required by some ADK/MCP components for session management.
# We run this before creating the non-root user or installing Python packages.
RUN apt-get update && apt-get install -y git --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for security, as in your example
RUN adduser --disabled-password --gecos "" myuser

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install all dependencies from your requirements.txt file
# This is the key step to include your project's libraries.
RUN pip install --no-cache-dir -r requirements.txt

# --- Templated Agent Section ---
# Copy the specific agent's code from the staged 'agents' directory
# into the final container structure.
COPY --chown=myuser:myuser agents/HisabAgent/ ./HisabAgent
# --- End Templated Agent Section ---

# Switch to the non-root user
USER myuser

# Set the PATH environment variable for the non-root user's packages
ENV PATH="/home/myuser/.local/bin:${PATH}"

# Set environment variables for Google Cloud runtime.
# Setting USE_VERTEXAI to 1 forces the agent to use the secure, key-less
# authentication method native to Google Cloud (IAM).
ENV GOOGLE_GENAI_USE_VERTEXAI=0

# Expose the port the app will run on. 8080 is the standard for Cloud Run.
EXPOSE 8080

# The command to run the ADK web server.
# This scans the '/app/agents' directory for discoverable agents,
# matching the pattern in your example.
CMD ["adk", "web", "--port=8080", "--host=0.0.0.0", "/app/agents"] 