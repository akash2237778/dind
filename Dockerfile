FROM elixircloud/foca:latest

## Set working directory
WORKDIR /app

## Copy app files
COPY ./ /app

RUN cd /app \
    && pip install kubernetes \
    && pip install gitpython

CMD ["bash", "-c", "cd /app; python app.py"]
