FROM langchain/langgraph-api:3.11

RUN apt-get update && apt-get install -y --no-install-recommends wget gdebi-core texlive-latex-base texlive-latex-extra texlive-fonts-recommended latexmk && QUARTO_VERSION=1.6.42 && wget -q https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.deb && gdebi -n quarto-${QUARTO_VERSION}-linux-amd64.deb && rm quarto-${QUARTO_VERSION}-linux-amd64.deb && apt-get clean && rm -rf /var/lib/apt/lists/*

# -- Adding local package . --
ADD . /deps/Agent-PDAI-A2
# -- End of local package . --

# -- Installing all local dependencies --
RUN for dep in /deps/*; do \
        echo "Installing $dep"; \
        if [ -d "$dep" ]; then \
            echo "Installing $dep"; \
            (cd "$dep" && PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir -c /api/constraints.txt -e .); \
        fi; \
    done
# -- End of local dependencies install --
ENV LANGSERVE_GRAPHS='{"agent": "/deps/Agent-PDAI-A2/agent/graph.py:graph"}'

# -- Ensure user deps didn't inadvertently overwrite langgraph-api
RUN mkdir -p /api/langgraph_api /api/langgraph_runtime /api/langgraph_license && touch /api/langgraph_api/__init__.py /api/langgraph_runtime/__init__.py /api/langgraph_license/__init__.py
RUN PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir --no-deps -e /api
# -- End of ensuring user deps didn't inadvertently overwrite langgraph-api --

WORKDIR /deps/Agent-PDAI-A2
