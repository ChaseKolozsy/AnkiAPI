ARG PYTHON_VERSION="3.9"
ARG DEBIAN_FRONTEND="noninteractive"
ARG ANKI_COMMIT

FROM anki-core:${ANKI_COMMIT} as runtime

# Runtime system deps for aqt/anki at runtime
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
    vim \
    libasound2 \
    libdbus-1-3 \
    libfontconfig1 \
    libfreetype6 \
    libgl1 \
    libglib2.0-0 \
    libnss3 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy API server files into the venv location
WORKDIR /opt/anki
COPY anki_api_server.py /opt/anki/venv/
COPY blueprint_decks.py /opt/anki/venv/
COPY blueprint_exports.py /opt/anki/venv/
COPY blueprint_imports.py /opt/anki/venv/
COPY blueprint_notetypes.py /opt/anki/venv/
COPY blueprint_users.py /opt/anki/venv/
COPY blueprint_cards.py /opt/anki/venv/
COPY blueprint_db.py /opt/anki/venv/
COPY blueprint_study_sessions.py /opt/anki/venv/

ENV PATH=/opt/anki/venv/bin:$PATH

RUN useradd --create-home anki
USER anki
WORKDIR /work

EXPOSE 5001
EXPOSE 5678

ENTRYPOINT ["/opt/anki/venv/bin/python", "/opt/anki/venv/anki_api_server.py"]

